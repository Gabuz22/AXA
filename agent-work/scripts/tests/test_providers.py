#!/usr/bin/env python3
"""Tests de la plateforme LLM multi-fournisseurs (déclarative, sans GitHub Models)."""
import os, sys, json, tempfile, shutil, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, SCRIPTS)

import safety_checks as S
import quota_manager as Q
import provider_router as PR
from providers import adapters


def fake_style(cfg, api_key, account_id, messages, max_tokens, timeout):
    beh = cfg.get("_behavior", "ok")
    if beh == "ratelimit":
        raise adapters.RateLimited("429")
    if beh == "error":
        raise adapters.ProviderError("boom")
    return '{"items":[]}', 11, 7


def cfg_with(providers):
    return {"version": "test", "providers": providers}


class ProviderBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp, "runs"), exist_ok=True)
        adapters.STYLES["faketest"] = fake_style
        self._old_cooldown = Q.provider_in_cooldown
        Q.provider_in_cooldown = lambda pid: False
        for k in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY"):
            os.environ[k] = "TESTKEY"
        self.pol = S.load_policies()

    def tearDown(self):
        Q.provider_in_cooldown = self._old_cooldown
        adapters.STYLES.pop("faketest", None)
        for k in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY"):
            os.environ.pop(k, None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def prov(self, **over):
        p = {"active": True, "free_tier": True, "requires_paid": False, "requires_card": False,
             "style": "faketest", "api_key_env": "GEMINI_API_KEY", "models": ["m1"], "priority": 1}
        p.update(over)
        return p


class TestEligibility(ProviderBase):
    def test_key_absent_not_eligible(self):
        r = PR.ProviderRouter(cfg_with({"x": self.prov(api_key_env="MISSING_KEY")}), self.pol, state_dir=self.tmp)
        self.assertEqual(r.available(), [])

    def test_requires_card_excluded(self):
        r = PR.ProviderRouter(cfg_with({"x": self.prov(requires_card=True)}), self.pol, state_dir=self.tmp)
        self.assertEqual(r.available(), [])

    def test_requires_paid_excluded(self):
        r = PR.ProviderRouter(cfg_with({"x": self.prov(requires_paid=True)}), self.pol, state_dir=self.tmp)
        self.assertEqual(r.available(), [])

    def test_inactive_excluded(self):
        r = PR.ProviderRouter(cfg_with({"x": self.prov(active=False)}), self.pol, state_dir=self.tmp)
        self.assertEqual(r.available(), [])

    def test_eligible_when_key_present(self):
        r = PR.ProviderRouter(cfg_with({"gemini": self.prov()}), self.pol, state_dir=self.tmp)
        self.assertEqual(r.available(), ["gemini"])


class TestOrderingAndFallback(ProviderBase):
    def test_learned_score_beats_priority(self):
        cfg = cfg_with({
            "a": self.prov(api_key_env="GEMINI_API_KEY", priority=1),
            "b": self.prov(api_key_env="GROQ_API_KEY", priority=2),
        })
        # b a une meilleure qualité apprise malgré une priorité plus basse
        S.write_json(os.path.join(self.tmp, PR.SCORES_FILE),
                     {"providers": {"a": {"quality": 40, "success": 1, "error": 0},
                                    "b": {"quality": 92, "success": 5, "error": 0}}})
        r = PR.ProviderRouter(cfg, self.pol, state_dir=self.tmp)
        self.assertEqual(r.available()[0], "b")

    def test_priority_tiebreak_when_no_scores(self):
        cfg = cfg_with({"a": self.prov(api_key_env="GEMINI_API_KEY", priority=2),
                        "b": self.prov(api_key_env="GROQ_API_KEY", priority=1)})
        r = PR.ProviderRouter(cfg, self.pol, state_dir=self.tmp)
        self.assertEqual(r.available()[0], "b")  # priorité 1 en premier

    def test_fallback_on_ratelimit(self):
        cfg = cfg_with({
            "a": self.prov(api_key_env="GEMINI_API_KEY", priority=1, _behavior="ratelimit"),
            "b": self.prov(api_key_env="GROQ_API_KEY", priority=2, _behavior="ok"),
        })
        r = PR.ProviderRouter(cfg, self.pol, state_dir=self.tmp, logger=lambda m: None)
        res = r.chat([{"role": "user", "content": "hi"}], 100, Q.Budget(5, 10000), dry_run=False)
        self.assertEqual(res["provider"], "b")

    def test_all_fail_raises(self):
        cfg = cfg_with({"a": self.prov(_behavior="error")})
        r = PR.ProviderRouter(cfg, self.pol, state_dir=self.tmp, logger=lambda m: None)
        with self.assertRaises(PR.NoProviderAvailable):
            r.chat([{"role": "user", "content": "hi"}], 100, Q.Budget(5, 10000), dry_run=False)

    def test_metrics_recorded(self):
        cfg = cfg_with({"a": self.prov(_behavior="ok")})
        r = PR.ProviderRouter(cfg, self.pol, state_dir=self.tmp, logger=lambda m: None)
        r.chat([{"role": "user", "content": "hi"}], 100, Q.Budget(5, 10000), dry_run=False)
        m = json.load(open(os.path.join(self.tmp, PR.METRICS_FILE), encoding="utf-8"))
        self.assertEqual(m["providers"]["a"]["success"], 1)
        self.assertGreaterEqual(m["providers"]["a"]["tokens_in"], 1)


class TestRealConfig(unittest.TestCase):
    def test_no_github_models_anywhere(self):
        cfg = S.load_providers_config()
        self.assertNotIn("github-models", cfg.get("providers", {}))
        for pid, p in cfg["providers"].items():
            self.assertNotIn("github", pid.lower())
            self.assertNotIn("github", (p.get("base_url", "") + p.get("api_key_env", "")).lower())
            self.assertNotIn("api.openai.com", p.get("base_url", "").lower())   # aucun endpoint OpenAI
            self.assertNotIn("openai_api_key", p.get("api_key_env", "").lower())  # aucune clé OpenAI
        # ('openai' comme STYLE d'API OpenAI-compatible reste autorisé : Groq/OpenRouter)

    def test_gemini_is_priority_one(self):
        cfg = S.load_providers_config()
        self.assertEqual(cfg["providers"]["gemini"]["priority"], 1)
        self.assertTrue(cfg["providers"]["gemini"]["active"])

    def test_all_active_free_no_card(self):
        cfg = S.load_providers_config()
        for pid, p in cfg["providers"].items():
            if p.get("active"):
                self.assertTrue(p.get("free_tier"))
                self.assertFalse(p.get("requires_paid"))
                self.assertFalse(p.get("requires_card"))

    def test_preflight_passes_on_real_config(self):
        S.preflight(S.load_policies(), S.load_providers_config(), need_llm=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
