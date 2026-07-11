#!/usr/bin/env python3
"""Tests du chef d'orchestre (Partie 15) — 20 scénarios, adaptateurs/état factices, aucun réseau."""
import os, sys, json, time, tempfile, shutil, datetime, subprocess, unittest

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


class TestSecretsAndIdempotency(Base):
    def _pcfg(self):
        return {"gemini": {"api_key_env": "GEMINI_API_KEY", "style": "gemini"},
                "groq": {"api_key_env": "GROQ_API_KEY", "style": "openai"},
                "openrouter": {"api_key_env": "OPENROUTER_API_KEY", "style": "openai"},
                "cloudflare": {"api_key_env": "CLOUDFLARE_API_TOKEN", "account_id_env": "CLOUDFLARE_ACCOUNT_ID", "style": "cloudflare"}}

    def tearDown(self):
        for k in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY", "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"):
            os.environ.pop(k, None)
        super().tearDown()

    def test_1_gemini_key_detected(self):
        os.environ["GEMINI_API_KEY"] = "x"
        self.assertTrue(orch.detect_keys(self._pcfg())["gemini"])

    def test_7_no_key_all_false(self):
        for k in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY", "CLOUDFLARE_API_TOKEN"):
            os.environ.pop(k, None)
        d = orch.detect_keys(self._pcfg())
        self.assertFalse(any(d.values()))

    def test_cloudflare_needs_both(self):
        os.environ["CLOUDFLARE_API_TOKEN"] = "x"
        self.assertFalse(orch.detect_keys(self._pcfg())["cloudflare"])  # account_id manquant
        os.environ["CLOUDFLARE_ACCOUNT_ID"] = "a"
        self.assertTrue(orch.detect_keys(self._pcfg())["cloudflare"])

    def test_2_3_reevaluated_each_cycle(self):
        reg = orch.ProviderRegistry(self.tmp)
        reg.set_key_detected("gemini", False)              # cycle N : absente
        reg.save()
        reg2 = orch.ProviderRegistry(self.tmp)             # persistant: cle_absente
        self.assertFalse(reg2._p("gemini")["key_detected"])
        os.environ["GEMINI_API_KEY"] = "x"                 # cycle N+1 : présente
        for pid, present in orch.detect_keys(self._pcfg()).items():
            reg2.set_key_detected(pid, present)
        self.assertTrue(reg2._p("gemini")["key_detected"])  # recalculé -> réactivable

    def test_5_idempotency_unique_per_task_cycle(self):
        k1 = orch.idempotency_key("c1", "t1", "extraction-llm")
        k2 = orch.idempotency_key("c1", "t1", "extraction-llm")
        k3 = orch.idempotency_key("c1", "t2", "extraction-llm")
        k4 = orch.idempotency_key("c2", "t1", "extraction-llm")
        self.assertEqual(k1, k2)
        self.assertEqual(len({k1, k3, k4}), 3)

    def test_4_workflow_passes_secrets(self):
        wf = os.path.join(S.REPO_ROOT, ".github/workflows/agents-orchestrator.yml")
        txt = open(wf, encoding="utf-8").read()
        self.assertIn("secrets: inherit", txt)
        self.assertIn("mode: cycle", txt)

    def test_5b_single_execution_per_cycle(self):
        # Clé présente + 2 tâches extraction-llm -> l'agent n'est exécuté qu'UNE fois (pas de double run).
        import orchestrator_cycle as OC
        os.environ["GEMINI_API_KEY"] = "x"
        calls = {"extraction-llm": 0}
        orig_run, orig_coord, orig_sync = OC._run_agent, OC._run_coordinator, OC._sync_provider_state_from_run
        OC._run_agent = lambda agent, dry, force_provider=None, force_model=None: (calls.__setitem__(agent, calls.get(agent, 0) + 1), ("ok", ""))[1]
        OC._run_coordinator = lambda dry: None
        OC._sync_provider_state_from_run = lambda reg, agent: None
        try:
            q = orch.TaskQueue(self.tmp)
            q.add("extraction-llm", contract="Avizen", category="definitions")
            q.add("extraction-llm", contract="Avizen", category="conditions")
            q.save()
            m = OC.run_cycle(dry_run=False, deterministic=[], base_dir=self.tmp)
            self.assertEqual(calls["extraction-llm"], 1, "extraction-llm doit être exécuté une seule fois par cycle")
            self.assertEqual(len(m["tasks_executed"]), 1)
        finally:
            OC._run_agent, OC._run_coordinator, OC._sync_provider_state_from_run = orig_run, orig_coord, orig_sync

    def test_6_preflight_no_secret_value(self):
        import orchestrator_cycle as OC
        os.environ["GEMINI_API_KEY"] = "SUPERSECRETVALUE"
        lines = []
        keys = orch.detect_keys(self._pcfg())
        OC._preflight_keys(keys, lines.append)
        blob = "\n".join(lines)
        self.assertIn("Gemini key detected: true", blob)
        self.assertNotIn("SUPERSECRETVALUE", blob)         # jamais la valeur


class TestIntegrationChain(unittest.TestCase):
    """Chaîne complète : fournisseur imposé par l'orchestrateur -> extraction-llm l'utilise réellement,
    exactement un appel LLM, fournisseur=gemini, une proposition générée. Adaptateur gemini factice."""
    PDF = os.path.join(S.REPO_ROOT, "data/AXA/00_PACKAGE_ACTIF/Contrats-AXA/Avizen/2025-04 Notice d'information Avizen.pdf")

    def setUp(self):
        import quota_manager as Q
        from agents import extraction_llm as EX
        try:
            import pypdf  # noqa
        except Exception:
            self.skipTest("pypdf requis")
        if not os.path.isfile(self.PDF):
            self.skipTest("notice Avizen absente")
        from providers import adapters
        self.adapters = adapters
        self.EX = EX; self.Q = Q
        self.pages = EX._read_pdf_pages(self.PDF, 4, 4)
        self.cite = " ".join(self.pages[4].split())[60:130]     # citation RÉELLE
        self.calls = {"n": 0, "providers": []}

        def fake_gemini(cfg, key, acc, msgs, mx, to):
            self.calls["n"] += 1; self.calls["providers"].append("gemini")
            item = {"categorie": "garanties", "texte": "element garantie", "page": 4, "citation": self.cite,
                    "confidence": 0.9, "importance": "forte", "why_missing": "categorie vide"}
            return json.dumps({"items": [item]}), 120, 40
        self._orig = adapters.STYLES.get("gemini")
        adapters.STYLES["gemini"] = fake_gemini
        self._orig_disc = adapters.discover_gemini_models     # évite tout appel réseau réel de découverte
        adapters.discover_gemini_models = lambda b, k, t: {"gemini-3.1-flash-lite"}
        # gemini est en COOLDOWN local -> prouve que le forçage le contourne
        self._old_cd = Q.provider_in_cooldown
        Q.provider_in_cooldown = lambda pid: (pid == "gemini")
        os.environ["GEMINI_API_KEY"] = "x"
        os.environ["AXA_FORCE_PROVIDER"] = "gemini"
        os.environ["AXA_FORCE_MODEL"] = "gemini-3.1-flash-lite"
        # zone fixe pointant sur la vraie notice
        self._old_sel = EX._select_zones
        self._old_res = EX._resolve_pdf
        self._old_rem = EX._remaining_daily_calls
        def _sel(mem, n, learning):
            mem.setdefault("contracts", {}).setdefault("avizen", {"pages_done": [], "pages_refused": [],
                "next_page": 4, "total_pages": 50, "zones_done": 0, "proposed_fingerprints": [],
                "last_processed_at": None, "nom_contrat": "Avizen"})
            return [{"slug": "avizen", "contrat": "Avizen", "entry": {"nom_fichier": os.path.basename(self.PDF)},
                     "start": 4, "end": 4, "gap_categories": ["garanties"]}]
        EX._select_zones = _sel
        EX._resolve_pdf = lambda entry: self.PDF
        EX._remaining_daily_calls = lambda mem, pol: (50, 0, 50, "2026-07-11")

    def tearDown(self):
        if self._orig:
            self.adapters.STYLES["gemini"] = self._orig
        self.adapters.discover_gemini_models = self._orig_disc
        self.Q.provider_in_cooldown = self._old_cd
        self.EX._select_zones = self._old_sel
        self.EX._resolve_pdf = self._old_res
        self.EX._remaining_daily_calls = self._old_rem
        for k in ("GEMINI_API_KEY", "AXA_FORCE_PROVIDER", "AXA_FORCE_MODEL"):
            os.environ.pop(k, None)

    def _ctx(self):
        import provider_router as PR
        pol = S.load_policies(); pcfg = S.load_providers_config()
        class Ctx:
            def __init__(s):
                s.agent_id = "extraction-llm"; s.run_id = "run_it"; s.mock = False; s.uses_llm = True
                s.policies = pol; s.providers_cfg = pcfg; s.dry_run = True
                s.limits = pol.get("limits", {}); s.task = {"id": "t", "scope": "", "type": "extraction"}
                s.budget = orch_Q_budget(); s.router = PR.ProviderRouter(pcfg, pol, logger=lambda m: None)
                s.provider_used = None; s.model_used = None; s.self_wrote = False; s._n = 0
            def seq_next(s):
                s._n += 1; return "%03d" % s._n
        return Ctx()

    def test_forced_provider_single_call_one_proposal(self):
        ctx = self._ctx()
        proposals, notes = self.EX.run(ctx)
        self.assertEqual(self.calls["n"], 1, "exactement un appel LLM")
        self.assertEqual(self.calls["providers"], ["gemini"])
        self.assertEqual(ctx.provider_used, "gemini")     # fournisseur imposé réellement utilisé
        self.assertGreaterEqual(ctx.budget.llm_calls, 1)  # Appels LLM > 0
        self.assertGreaterEqual(len(proposals), 1)        # une proposition générée
        self.assertEqual(proposals[0]["proposed_change"]["payload"]["categorie"], "garanties")


class TestSubprocessForcing(unittest.TestCase):
    """VRAI test de sous-processus : lance orchestrator.py dans un process séparé avec AXA_FORCE_* dans
    l'environnement + adaptateur Gemini factice. Prouve que le sous-processus voit les variables, qu'un
    seul appel adaptateur a lieu, et que le résumé contient 'Fournisseur : gemini' et 'Appels LLM : 1'."""
    PDF = os.path.join(S.REPO_ROOT, "data/AXA/00_PACKAGE_ACTIF/Contrats-AXA/Avizen/2025-04 Notice d'information Avizen.pdf")

    def test_subprocess_sees_force_and_calls_once(self):
        try:
            import pypdf  # noqa
        except Exception:
            self.skipTest("pypdf requis")
        if not os.path.isfile(self.PDF):
            self.skipTest("notice Avizen absente")
        from agents import extraction_llm as EX
        pages = EX._read_pdf_pages(self.PDF, 4, 4)
        cite = " ".join(pages[4].split())[60:130]

        harness = (
            "import sys, os, json\n"
            "sys.path.insert(0, @SCRIPTS@)\n"
            "from providers import adapters\n"
            "CITE = @CITE@\nPDF = @PDF@\n"
            "def fake(cfg, key, acc, msgs, mx, to):\n"
            "    print('ADAPTER_CALLED', cfg.get('model'))\n"
            "    return json.dumps({'items':[{'categorie':'garanties','texte':'x','page':4,'citation':CITE,'confidence':0.9,'importance':'forte','why_missing':'categorie vide'}]}), 120, 40\n"
            "adapters.STYLES['gemini'] = fake\n"
            "adapters.discover_gemini_models = lambda b, k, t: {'gemini-3.1-flash-lite'}\n"
            "from agents import extraction_llm as EX\n"
            "def sel(mem, n, l):\n"
            "    mem.setdefault('contracts', {}).setdefault('avizen', {'pages_done':[], 'pages_refused':[], 'next_page':4, 'total_pages':50, 'zones_done':0, 'proposed_fingerprints':[], 'last_processed_at':None, 'nom_contrat':'Avizen'})\n"
            "    return [{'slug':'avizen','contrat':'Avizen','entry':{'nom_fichier':os.path.basename(PDF)},'start':4,'end':4,'gap_categories':['garanties']}]\n"
            "EX._select_zones = sel\n"
            "EX._resolve_pdf = lambda e: PDF\n"
            "EX._remaining_daily_calls = lambda m, p: (50, 0, 50, '2026-07-11')\n"
            "import orchestrator\n"
            "sys.argv = ['orchestrator.py', '--agent', 'extraction-llm', '--dry-run']\n"
            "orchestrator.main()\n"
        ).replace("@SCRIPTS@", repr(SCRIPTS)).replace("@CITE@", repr(cite)).replace("@PDF@", repr(self.PDF))

        hpath = os.path.join(tempfile.mkdtemp(), "harness.py")
        with open(hpath, "w", encoding="utf-8") as f:
            f.write(harness)
        env = dict(os.environ, GEMINI_API_KEY="x", AXA_FORCE_PROVIDER="gemini", AXA_FORCE_MODEL="gemini-3.1-flash-lite")
        r = subprocess.run([sys.executable, hpath], cwd=S.REPO_ROOT, capture_output=True, text=True, timeout=120, env=env)
        out = r.stdout + r.stderr
        # 1) le sous-processus voit bien la variable forcée
        self.assertIn("AXA_FORCE_PROVIDER present: true", out, out[-800:])
        # 2) exactement un appel adaptateur, sur le modèle imposé
        self.assertEqual(out.count("ADAPTER_CALLED"), 1, out[-800:])
        self.assertIn("ADAPTER_CALLED gemini-3.1-flash-lite", out)
        # 3) le résumé montre le fournisseur réellement utilisé + un appel
        self.assertIn("Fournisseur : gemini", out, out[-800:])
        self.assertIn("Appels LLM : 1", out, out[-800:])
        # 4) aucun secret affiché
        self.assertNotIn("GEMINI_API_KEY=x", out)


def orch_Q_budget():
    import quota_manager as Q
    return Q.Budget(max_llm_calls=6, max_tokens=40000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
