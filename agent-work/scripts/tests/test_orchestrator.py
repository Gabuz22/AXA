#!/usr/bin/env python3
"""Tests du chef d'orchestre (Partie 15) — 20 scénarios, adaptateurs/état factices, aucun réseau."""
import os, sys, json, time, tempfile, shutil, datetime, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, SCRIPTS)
import safety_checks as S
import orch

RANKS = {"faible": 1, "moyen": 2, "bon": 3, "eleve": 4}
CAPS_EXTRACT = {"required_capabilities": ["json_strict"], "json_strict": True, "reasoning_min": "moyen",
                "compatible_providers": ["gemini", "groq", "cloudflare", "openrouter"], "min_quality_history": 55,
                "allow_smaller_model": True}
CAPS_COMPLEX = dict(CAPS_EXTRACT, reasoning_min="eleve")


def providers():
    return {
        "gemini": {"active": True, "free_tier": True, "requires_paid": False, "requires_card": False,
                   "style": "gemini", "json_capable": True, "reasoning": "bon", "priority": 1, "models": ["gflash"]},
        "groq": {"active": True, "free_tier": True, "requires_paid": False, "requires_card": False,
                 "style": "openai", "json_capable": True, "reasoning": "bon", "priority": 2, "models": ["llama"]},
        "cloudflare": {"active": True, "free_tier": True, "requires_paid": False, "requires_card": False,
                       "style": "cloudflare", "json_capable": True, "reasoning": "faible", "priority": 3, "models": ["cf"]},
        "openrouter": {"active": True, "free_tier": True, "requires_paid": False, "requires_card": False,
                       "style": "openai", "json_capable": True, "reasoning": "moyen", "priority": 4,
                       "models": ["big:free", "paid-model"]},
    }


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp, "locks"), exist_ok=True)
        self.reg = orch.ProviderRegistry(self.tmp)
        for pid in providers():
            self.reg.set_key_detected(pid, True)
        self.scores = {}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def choose(self, caps=CAPS_EXTRACT, exclude=None):
        task = {"task_id": "t1", "agent_type": "extraction-llm"}
        d, why = orch.choose_engine(task, caps, providers(), self.reg, self.scores, RANKS, exclude_providers=exclude)
        return d, why


class TestRouting(Base):
    def test_01_gemini_chosen(self):
        d, _ = self.choose()
        self.assertEqual(d["provider"], "gemini")

    def test_02_gemini_429_groq_takes(self):
        self.reg.record_error("gemini", "gflash", 429, "rate limit per minute", 0.5)
        d, _ = self.choose()
        self.assertEqual(d["provider"], "groq")

    def test_03_gemini_groq_out_openrouter_free(self):
        self.reg.record_error("gemini", "gflash", 429, "daily quota", 0.5)
        self.reg.record_error("groq", "llama", 429, "daily", 0.5)
        # cloudflare : raisonnement faible, incompatible avec moyen requis -> reste openrouter
        d, _ = self.choose()
        self.assertEqual(d["provider"], "openrouter")
        self.assertIn(":free", d["model"])   # jamais un modèle payant

    def test_04_openrouter_only_paid_refused(self):
        p = providers(); p["openrouter"]["models"] = ["paid-model"]  # aucun :free
        task = {"task_id": "t", "agent_type": "extraction-llm"}
        # seuls gemini/groq indispo + cloudflare incompatible -> openrouter sans :free -> None
        self.reg.record_error("gemini", "gflash", 429, "daily", 0.5)
        self.reg.record_error("groq", "llama", 429, "daily", 0.5)
        d, why = orch.choose_engine(task, CAPS_EXTRACT, p, self.reg, self.scores, RANKS)
        self.assertIsNone(d)
        self.assertTrue(any("openrouter" == r[0] for r in why["rejected"]))

    def test_05_all_out_none(self):
        for pid in ("gemini", "groq", "openrouter"):
            self.reg.record_error(pid, "m", 429, "daily", 0.5)
        d, _ = self.choose()  # cloudflare incompatible (raisonnement)
        self.assertIsNone(d)

    def test_09_complex_refused_small_model(self):
        # cloudflare (raisonnement faible) doit être écarté pour une tâche 'eleve'
        for pid in ("gemini", "groq", "openrouter"):
            self.reg.record_error(pid, "m", 429, "daily", 0.5)
        d, why = self.choose(caps=CAPS_COMPLEX)
        self.assertIsNone(d)
        self.assertTrue(any(r[0] == "cloudflare" and "raisonnement" in r[1] for r in why["rejected"]))

    def test_10_second_review_different_provider(self):
        d, _ = self.choose(exclude=["gemini"])
        self.assertNotEqual(d["provider"], "gemini")

    def test_15_insufficient_learning_keeps_priority(self):
        # groq a une meilleure qualité mais < 3 échantillons -> priorité (gemini=1) l'emporte
        self.scores = {"groq": {"quality": 95, "samples": 1}}
        d, _ = self.choose()
        self.assertEqual(d["provider"], "gemini")

    def test_16_enough_history_uses_learned(self):
        self.scores = {"groq": {"quality": 95, "samples": 5}, "gemini": {"quality": 50, "samples": 5}}
        d, _ = self.choose()
        self.assertEqual(d["provider"], "groq")

    def test_17_no_key_clean_stop(self):
        for pid in providers():
            self.reg.set_key_detected(pid, False)
        d, why = self.choose()
        self.assertIsNone(d)
        self.assertTrue(all("clé absente" in r[1] for r in why["rejected"]))

    def test_20_never_paid(self):
        p = providers(); p["paidx"] = dict(p["gemini"], requires_paid=True, models=["x"])
        self.reg.set_key_detected("paidx", True)
        task = {"task_id": "t", "agent_type": "extraction-llm"}
        caps = dict(CAPS_EXTRACT, compatible_providers=["paidx"])
        d, why = orch.choose_engine(task, caps, p, self.reg, self.scores, RANKS)
        self.assertIsNone(d)


class TestProviderState(Base):
    def test_06_cooldown_then_reactivate(self):
        self.reg.record_error("gemini", "gflash", 429, "minute", 0.5)
        self.assertFalse(self.reg.is_available("gemini"))
        self.reg._p("gemini")["next_available_at"] = orch._iso(orch._now() - datetime.timedelta(seconds=5))
        self.reg.reactivate_expired()
        self.assertTrue(self.reg.is_available("gemini"))

    def test_07_auth_error_disables_until_human(self):
        self.reg.record_error("gemini", "gflash", 401, "invalid key", 0.2)
        self.assertFalse(self.reg.is_available("gemini"))
        self.assertTrue(self.reg._p("gemini")["needs_human"])
        # ne se réactive PAS automatiquement
        self.reg._p("gemini")["next_available_at"] = orch._iso(orch._now() - datetime.timedelta(seconds=5))
        self.reg.reactivate_expired()
        self.assertFalse(self.reg.is_available("gemini"))

    def test_08_model_404_disables_model_not_provider(self):
        cat = self.reg.record_error("gemini", "gflash", 404, "model not found", 0.2)
        self.assertEqual(cat, "model_unavailable")
        self.assertTrue(self.reg.is_available("gemini"))               # fournisseur toujours OK
        self.assertFalse(self.reg.model_available("gemini", "gflash"))  # ce modèle est désactivé

    def test_classify(self):
        self.assertEqual(orch.classify_error(401)[1], "auth_error")
        self.assertEqual(orch.classify_error(404)[1], "model_unavailable")
        self.assertEqual(orch.classify_error(500)[1], "provider_unavailable")
        self.assertEqual(orch.classify_error(429, "daily")[1], "quota_exhausted")


class TestQueueAndLock(Base):
    def test_11_lock_prevents_concurrent(self):
        ok1, _ = orch.acquire_cycle_lock(self.tmp, "c1")
        ok2, holder = orch.acquire_cycle_lock(self.tmp, "c2")
        self.assertTrue(ok1); self.assertFalse(ok2); self.assertEqual(holder, "c1")

    def test_12_crash_recovery_requeues(self):
        q = orch.TaskQueue(self.tmp)
        t, _ = q.add("extraction-llm", contract="avizen", category="definitions")
        q.claim(t, "old")
        t["running_since"] = orch._iso(orch._now() - datetime.timedelta(hours=2))
        q.recover_stale()
        self.assertEqual(t["status"], "ready")

    def test_dedup_no_duplicate_task(self):
        q = orch.TaskQueue(self.tmp)
        a, new1 = q.add("extraction-llm", contract="avizen", category="definitions")
        b, new2 = q.add("extraction-llm", contract="avizen", category="definitions")
        self.assertTrue(new1); self.assertFalse(new2); self.assertEqual(a["task_id"], b["task_id"])

    def test_14_retryable_becomes_terminal(self):
        q = orch.TaskQueue(self.tmp)
        t, _ = q.add("extraction-llm", contract="x", category="y", max_attempts=2)
        q.claim(t, "c"); q.finish(t, "failed_retryable", retry_delay_s=10)
        q.claim(t, "c"); q.finish(t, "failed_retryable", retry_delay_s=10)
        self.assertEqual(t["status"], "failed_terminal")

    def test_13_cost_policy_stops_with_margin(self):
        cp = orch.CostPolicy(S.load_policies(), per_provider_cycle_cap=3, safety_margin=1)
        cp.record("gemini"); cp.record("gemini")  # 2 appels, cap 3 marge 1 -> stop à 2
        self.assertFalse(cp.can_call("gemini"))

    def test_18_state_paths_under_agent_work(self):
        q = orch.TaskQueue(orch.ORCH_DIR if hasattr(orch, "ORCH_DIR") else os.path.join(S.AGENT_WORK, "orchestrator"))
        self.assertIn("agent-work", q.path.replace("\\", "/"))

    def test_20_cost_policy_refuses_paid(self):
        pol = dict(S.load_policies()); pol["allow_paid_usage"] = True
        with self.assertRaises(S.SafetyError):
            orch.CostPolicy(pol)


if __name__ == "__main__":
    unittest.main(verbosity=2)
