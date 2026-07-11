#!/usr/bin/env python3
"""Chef d'orchestre — un CYCLE (pas un processus permanent). Réveil périodique via GitHub Actions.

À chaque cycle : verrou de concurrence -> reset des fournisseurs échus -> agents déterministes (travail
utile sans LLM) -> mise à jour du backlog/file -> sélection + routage explicable -> exécution bornée des
tâches LLM (si un moteur gratuit est disponible) -> contrôles déterministes (déjà dans les agents) ->
métriques -> READY_FOR_REVIEW -> manifeste de cycle -> arrêt propre. Ne fait AUCUNE opération Git
(le workflow gère commit/scope/PR). Zéro coût, jamais de fusion, aucun fichier produit modifié.
"""
import os, sys, json, glob, time, argparse, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import safety_checks as S
import orch

ORCH_DIR = os.path.join(S.AGENT_WORK, "orchestrator")
DEFAULT_DETERMINISTIC = ["coverage-gaps", "quality"]
MAX_LLM_TASKS_PER_CYCLE = 2
CYCLE_TIME_BUDGET_S = 600


def _preflight_keys(keys, L):
    """Affiche la détection des clés (true/false uniquement) — jamais de valeur, longueur ou préfixe."""
    def b(x):
        return "true" if x else "false"
    L("Gemini key detected: %s" % b(keys.get("gemini")))
    L("Groq key detected: %s" % b(keys.get("groq")))
    L("OpenRouter key detected: %s" % b(keys.get("openrouter")))
    L("Cloudflare credentials detected: %s" % b(keys.get("cloudflare")))


def _run_agent(agent, dry_run):
    args = [sys.executable, os.path.join(S.AGENT_WORK, "scripts", "orchestrator.py"), "--agent", agent]
    if dry_run:
        args.append("--dry-run")
    try:
        r = subprocess.run(args, cwd=S.REPO_ROOT, capture_output=True, timeout=300)
        out = (r.stdout or b"").decode("utf-8", "replace")
        status = "ok" if r.returncode == 0 else "error"
        # récupère le statut réel depuis le dernier manifeste de l'agent
        return status, out[-400:]
    except Exception as e:
        return "error", str(e)


def _build_llm_tasks(queue):
    """Alimente la file avec des tâches d'extraction issues des trous de couverture (déterministe)."""
    caps = S.load_json(os.path.join(S.AGENT_WORK, "config", "agent_capabilities.json"), default={})
    ext = caps.get("agents", {}).get("extraction-llm", {})
    created = 0
    for f in glob.glob(os.path.join(S.AGENT_WORK, "quality", "incidents", "coverage__categorie_absente*.json")):
        try:
            inc = S.load_json(f)
        except Exception:
            continue
        pl = inc.get("proposed_change", {}).get("payload", {})
        contrat = pl.get("subject") or pl.get("contrat")
        for cat in (pl.get("categories_absentes") or [pl.get("categorie")] or []):
            if not contrat or not cat:
                continue
            _, is_new = queue.add(
                "extraction-llm", priority=4, contract=contrat, category=cat,
                required_capabilities=ext.get("required_capabilities", []),
                compatible_providers=ext.get("compatible_providers", []),
                estimated_input_tokens=2500, estimated_output_tokens=700,
                source_gap_id=inc.get("proposal_id"), human_validation_required=True)
            created += int(is_new)
    return created


def run_cycle(dry_run=False, deterministic=None, base_dir=ORCH_DIR):
    cid = "cycle_" + S.stamp()
    policies = S.load_policies()
    providers_cfg = S.load_providers_config().get("providers", {})
    caps = S.load_json(os.path.join(S.AGENT_WORK, "config", "agent_capabilities.json"), default={})
    ranks = caps.get("reasoning_rank", {"faible": 1, "moyen": 2, "bon": 3, "eleve": 4})
    t0 = time.time()
    log = []
    def L(m):
        print(m); log.append(m)

    ok_lock, holder = orch.acquire_cycle_lock(base_dir, cid, dry_run=dry_run)
    if not ok_lock:
        L("[cycle] verrou déjà pris par %s — arrêt (anti-concurrence)." % holder)
        return {"cycle_id": cid, "status": "locked", "holder": holder}

    manifest = {"cycle_id": cid, "started_at": orch._iso(), "dry_run": dry_run, "status": "ok",
                "deterministic_ran": [], "llm_decisions": [], "tasks_executed": [], "tasks_deferred": [],
                "provider_changes": [], "notes": []}
    try:
        # 1) état persistant + RE-DÉTECTION des clés à CHAQUE cycle (une absence ancienne ne bloque plus)
        registry = orch.ProviderRegistry(base_dir).reactivate_expired()
        keys = orch.detect_keys(providers_cfg)
        for pid, present in keys.items():
            registry.set_key_detected(pid, present)
        _preflight_keys(keys, L)
        queue = orch.TaskQueue(base_dir).recover_stale()
        cost = orch.CostPolicy(policies, per_provider_cycle_cap=policies.get("limits", {}).get("max_llm_calls_per_run", 6))

        # 2) agents déterministes (toujours du travail utile, même sans LLM)
        for agent in (deterministic or DEFAULT_DETERMINISTIC):
            st, tail = _run_agent(agent, dry_run)
            manifest["deterministic_ran"].append({"agent": agent, "status": st})
            L("[cycle] déterministe %s -> %s" % (agent, st))

        # 3) file de tâches depuis les trous de couverture
        created = _build_llm_tasks(queue)
        L("[cycle] file: %d nouvelle(s) tâche(s) d'extraction depuis les trous de couverture" % created)

        # 4) routage + exécution bornée des tâches LLM.
        # IDEMPOTENCE : un agent LLM (qui auto-batch ses zones) n'est exécuté qu'UNE fois par cycle ;
        # une même (cycle_id, task_id, agent_type) n'est jamais rejouée (anti double-exécution/crash).
        scores = S.load_json(os.path.join(S.AGENT_WORK, "runs", "provider_scores.json"), default={}).get("providers", {})
        idem = S.load_json(os.path.join(base_dir, "idempotency.json"), default={"done": []})
        idem_done = set(idem.get("done", []))
        ran_agents, executed = set(), 0
        for task in queue.ready_tasks():
            if executed >= MAX_LLM_TASKS_PER_CYCLE or (time.time() - t0) > CYCLE_TIME_BUDGET_S:
                break
            agent = task["agent_type"]
            if caps.get("agents", {}).get(agent, {}).get("kind") != "llm":
                continue
            ikey = orch.idempotency_key(cid, task["task_id"], agent)
            agent_caps = caps.get("agents", {}).get(agent, {})
            decision, why = orch.choose_engine(task, agent_caps, providers_cfg, registry, scores, ranks)
            if not decision:
                task["status"] = "waiting_provider"
                manifest["tasks_deferred"].append({"task_id": task["task_id"], "raison": why.get("reason")})
                L("[cycle] tâche %s reportée: %s" % (task["task_id"], why.get("reason")))
                continue
            # Un seul run de cet agent par cycle : les autres tâches du même agent restent 'ready'
            # (l'agent traite son lot de zones en un seul run — évite la double exécution).
            if agent in ran_agents or ikey in idem_done:
                task["status"] = "ready"
                manifest["tasks_deferred"].append({"task_id": task["task_id"], "raison": "regroupé avec le run unique de %s ce cycle" % agent})
                continue
            if not cost.can_call(decision["provider"]):
                task["status"] = "waiting_reset"
                manifest["tasks_deferred"].append({"task_id": task["task_id"], "raison": "budget cycle atteint"})
                continue
            manifest["llm_decisions"].append(decision)
            L("[cycle] ROUTAGE %s -> %s/%s (%s)" % (task["task_id"], decision["provider"], decision["model"], decision["reason"]))
            if not queue.claim(task, cid):
                continue
            st, tail = _run_agent(agent, dry_run)     # exécution réelle (réutilise routeur/quota)
            cost.record(decision["provider"]); ran_agents.add(agent); idem_done.add(ikey)
            _sync_provider_state_from_run(registry, agent)
            queue.finish(task, "completed" if st == "ok" else "failed_retryable",
                         provider=decision["provider"], model=decision["model"],
                         error=None if st == "ok" else tail, retry_delay_s=120)
            manifest["tasks_executed"].append({"task_id": task["task_id"], "provider": decision["provider"],
                                               "model": decision["model"], "status": task["status"]})
            executed += 1
        if not dry_run:
            S.write_json(os.path.join(base_dir, "idempotency.json"), {"done": list(idem_done)[-300:], "updated_at": orch._iso()})

        manifest["provider_changes"] = registry.snapshot()

        # 5) coordinateur (synthèse pour l'humain)
        _run_coordinator(dry_run)

        # 6) persistance de l'état d'orchestration + résumé de cycle
        registry.save(dry_run); queue.save(dry_run)
        summary = _cycle_summary(cid, manifest, queue, registry)
        if not dry_run:
            S.write_json(os.path.join(base_dir, "cycle_summary.json"), summary)
            S.write_json(os.path.join(base_dir, "cycles", cid + ".json"), manifest)
        manifest["finished_at"] = orch._iso()
        manifest["duration_s"] = round(time.time() - t0, 1)
        L("[cycle] terminé en %.1fs — déterministes=%d, tâches exécutées=%d, reportées=%d" % (
            manifest["duration_s"], len(manifest["deterministic_ran"]), len(manifest["tasks_executed"]), len(manifest["tasks_deferred"])))
        return manifest
    finally:
        orch.release_cycle_lock(base_dir, dry_run)


def _sync_provider_state_from_run(registry, agent):
    """Lit le dernier manifeste de l'agent pour refléter le fournisseur réellement utilisé (sans secret)."""
    mans = sorted(glob.glob(os.path.join(S.AGENT_WORK, "runs", "manifests", "run_%s_*.json" % agent)))
    if not mans:
        return
    m = S.load_json(mans[-1])
    pid = m.get("provider_used")
    if pid:
        c = m.get("counters", {})
        registry.record_success(pid, m.get("model_used"), c.get("tokens_in_est", 0), c.get("tokens_out_est", 0), 1.0)


def _run_coordinator(dry_run):
    try:
        subprocess.run([sys.executable, os.path.join(S.AGENT_WORK, "scripts", "build_review_summary.py")],
                       cwd=S.REPO_ROOT, capture_output=True, timeout=120)
    except Exception:
        pass


def _cycle_summary(cid, manifest, queue, registry):
    counts = queue.counts()
    # « disponible » = clé détectée ET état available (sinon c'est un moteur non utilisable).
    avail = [pid for pid in registry.data["providers"]
             if registry._p(pid).get("key_detected") and registry.is_available(pid)]
    resting = []
    for s in registry.snapshot():
        no_key = not registry._p(s["provider"]).get("key_detected")
        if s["state"] != "available" or no_key:
            state = "cle_absente" if (no_key and s["state"] == "available") else s["state"]
            resting.append({"provider": s["provider"], "state": state, "reprise": s["next_available_at"]})
    return {
        "cycle_id": cid, "generated_at": orch._iso(),
        "deterministic_ran": [d["agent"] for d in manifest["deterministic_ran"]],
        "tasks_done_this_cycle": len(manifest["tasks_executed"]),
        "tasks_waiting": counts.get("ready", 0) + counts.get("waiting_provider", 0) + counts.get("waiting_reset", 0),
        "providers_available": avail, "providers_resting": resting,
        "incidents_human": [s["provider"] for s in registry.snapshot() if s.get("needs_human")],
        "next_priority": (manifest["tasks_deferred"][0]["task_id"] if manifest["tasks_deferred"] else None),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--deterministic", default=",".join(DEFAULT_DETERMINISTIC))
    args = ap.parse_args()
    S.preflight(S.load_policies(), S.load_providers_config(), need_llm=False)  # zéro coût garanti
    m = run_cycle(dry_run=args.dry_run, deterministic=[a for a in args.deterministic.split(",") if a])
    print(json.dumps({k: m.get(k) for k in ("cycle_id", "status", "duration_s")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
