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


class TestGeminiDiscovery(unittest.TestCase):
    """Découverte des modèles Gemini + résilience au retrait d'un modèle (404)."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.calls = []
        self.discover_calls = {"n": 0}
        self._old_cd = Q.provider_in_cooldown
        Q.provider_in_cooldown = lambda pid: False
        os.environ["GEMINI_API_KEY"] = "x"
        self._old_style = adapters.STYLES.get("gemini")
        self._old_disc = adapters.discover_gemini_models

        def fake_gemini(cfg, key, acc, msgs, mx, to):
            m = cfg.get("model"); self.calls.append(m)
            if m == "gemini-2.5-flash-lite":
                raise adapters.ProviderError("HTTP 404 : no longer available", code=404)
            return "{}", 50, 20
        adapters.STYLES["gemini"] = fake_gemini
        self._discovered = {"gemini-2.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.1-flash"}

        def fake_discover(base_url, key, timeout):
            self.discover_calls["n"] += 1
            return set(self._discovered)
        adapters.discover_gemini_models = fake_discover

    def tearDown(self):
        Q.provider_in_cooldown = self._old_cd
        adapters.STYLES["gemini"] = self._old_style
        adapters.discover_gemini_models = self._old_disc
        for k in ("GEMINI_API_KEY", "AXA_FORCE_PROVIDER", "AXA_FORCE_MODEL"):
            os.environ.pop(k, None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _cfg(self, models):
        return {"version": "t", "providers": {"gemini": {
            "active": True, "free_tier": True, "requires_paid": False, "requires_card": False,
            "style": "gemini", "base_url": "https://x", "path": "/v1beta/models/{model}:generateContent",
            "api_key_env": "GEMINI_API_KEY", "models": models, "priority": 1}}}

    def _router(self, models):
        return PR.ProviderRouter(self._cfg(models), S.load_policies(), logger=lambda m: None, state_dir=self.tmp)

    def test_1_2_404_fallbacks_and_provider_stays_gemini(self):
        os.environ["AXA_FORCE_PROVIDER"] = "gemini"; os.environ["AXA_FORCE_MODEL"] = "gemini-2.5-flash-lite"
        r = self._router(["gemini-2.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.1-flash"])
        res = r.chat([{"role": "user", "content": "hi"}], 100, Q.Budget(6, 100000))
        self.assertEqual(res["provider"], "gemini")                 # 2. reste Gemini
        self.assertEqual(res["model"], "gemini-3.1-flash-lite")     # 1. bascule vers 3.1-flash-lite
        disc = json.load(open(os.path.join(self.tmp, "orchestrator/model_discovery.json"), encoding="utf-8"))
        self.assertIn("gemini-2.5-flash-lite", disc["providers"]["gemini"]["disabled"])  # retiré désactivé

    def test_3_model_absent_from_listing_ignored(self):
        self._discovered = {"gemini-3.1-flash"}                     # 2.5 et 3.1-flash-lite absents du listing réel
        r = self._router(["gemini-2.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.1-flash"])
        res = r.chat([{"role": "user", "content": "hi"}], 100, Q.Budget(6, 100000))
        self.assertEqual(res["model"], "gemini-3.1-flash")
        self.assertNotIn("gemini-2.5-flash-lite", self.calls)       # jamais appelé
        self.assertNotIn("gemini-3.1-flash-lite", self.calls)

    def test_4_generatecontent_filter(self):
        # discover_gemini_models réel : un modèle sans generateContent est exclu.
        adapters.discover_gemini_models = self._old_disc            # vraie fonction
        import io
        class Resp:
            def __enter__(s): return s
            def __exit__(s, *a): return False
            def read(s):
                return json.dumps({"models": [
                    {"name": "models/gemini-3.1-flash-lite", "supportedGenerationMethods": ["generateContent"]},
                    {"name": "models/embedding-x", "supportedGenerationMethods": ["embedContent"]}]}).encode()
        old = adapters.urllib.request.urlopen
        adapters.urllib.request.urlopen = lambda req, timeout=0: Resp()
        try:
            got = adapters.discover_gemini_models("https://x", "key", 5)
        finally:
            adapters.urllib.request.urlopen = old
        self.assertIn("gemini-3.1-flash-lite", got)
        self.assertNotIn("embedding-x", got)                        # pas de generateContent -> exclu

    def test_5_no_compatible_model_raises(self):
        self._discovered = set()                                    # aucun modèle listé
        r = self._router(["gemini-3.1-flash-lite"])
        with self.assertRaises(PR.NoProviderAvailable):             # -> l'orchestrateur mettra waiting_provider
            r.chat([{"role": "user", "content": "hi"}], 100, Q.Budget(6, 100000))

    def test_6_no_paid_model_openrouter(self):
        cfg = {"version": "t", "providers": {"openrouter": {
            "active": True, "free_tier": True, "requires_paid": False, "requires_card": False,
            "style": "openai", "base_url": "https://o", "api_key_env": "GEMINI_API_KEY",
            "models": ["paid-model"], "priority": 4}}}
        adapters.STYLES["openai"] = lambda *a, **k: (_ for _ in ()).throw(AssertionError("ne doit pas appeler un modèle payant"))
        os.environ["AXA_FORCE_PROVIDER"] = "openrouter"
        r = PR.ProviderRouter(cfg, S.load_policies(), logger=lambda m: None, state_dir=self.tmp)
        with self.assertRaises(PR.NoProviderAvailable):
            r.chat([{"role": "user", "content": "hi"}], 100, Q.Budget(6, 100000))

    def test_7_discovery_once_per_cycle(self):
        r = self._router(["gemini-3.1-flash-lite"])
        r.chat([{"role": "user", "content": "a"}], 100, Q.Budget(6, 100000))
        r.chat([{"role": "user", "content": "b"}], 100, Q.Budget(6, 100000))
        self.assertEqual(self.discover_calls["n"], 1)               # cache : une seule découverte

    def test_8_used_model_in_metrics(self):
        r = self._router(["gemini-3.1-flash-lite"])
        r.chat([{"role": "user", "content": "a"}], 100, Q.Budget(6, 100000))
        met = json.load(open(os.path.join(self.tmp, PR.METRICS_FILE), encoding="utf-8"))
        self.assertIn("gemini-3.1-flash-lite", met["providers"]["gemini"]["models"])


class TestRealConfigModels(unittest.TestCase):
    def test_no_obsolete_gemini_2_5_flash_lite(self):
        cfg = S.load_providers_config()
        self.assertNotIn("gemini-2.5-flash-lite", cfg["providers"]["gemini"]["models"])
        self.assertEqual(cfg["providers"]["gemini"]["models"][0], "gemini-3.1-flash-lite")


if __name__ == "__main__":
    unittest.main(verbosity=2)
