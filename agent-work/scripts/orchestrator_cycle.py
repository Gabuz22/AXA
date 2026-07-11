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
DEFAULT_DETERMINISTIC = ["knowledge-curator", "coverage-gaps", "quality"]
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


def _run_agent(agent, dry_run, force_provider=None, force_model=None):
    args = [sys.executable, os.path.join(S.AGENT_WORK, "scripts", "orchestrator.py"), "--agent", agent]
    if dry_run:
        args.append("--dry-run")
    env = dict(os.environ)
    env.pop("AXA_FORCE_PROVIDER", None); env.pop("AXA_FORCE_MODEL", None)
    if force_provider:                       # impose le moteur choisi par l'orchestrateur (pas de second routage)
        env["AXA_FORCE_PROVIDER"] = force_provider
        if force_model:
            env["AXA_FORCE_MODEL"] = force_model
    # Diag non sensible (parent) : ce que l'on transmet au sous-processus.
    print("[cycle] _run_agent(%s): env AXA_FORCE_PROVIDER present: %s | AXA_FORCE_MODEL present: %s" % (
        agent, "true" if env.get("AXA_FORCE_PROVIDER") else "false",
        "true" if env.get("AXA_FORCE_MODEL") else "false"))
    try:
        r = subprocess.run(args, cwd=S.REPO_ROOT, capture_output=True, timeout=300, env=env)
        out = (r.stdout or b"").decode("utf-8", "replace")
        result = _parse_agent_result(out)        # résultat MÉTIER (parsé sur le stdout complet, pas seulement la queue)
        status = "ok" if r.returncode == 0 else "error"
        return status, out[-400:], result
    except Exception as e:
        return "error", str(e), {}


def _parse_agent_result(stdout):
    """Extrait la DERNIÈRE ligne 'AGENT_RESULT_JSON=...' (résultat métier machine-readable). Robuste :
    tolère l'absence, une ligne tronquée ou un JSON invalide (retourne alors {})."""
    result = {}
    for line in (stdout or "").splitlines():
        s = line.strip()
        if s.startswith("AGENT_RESULT_JSON="):
            try:
                result = json.loads(s[len("AGENT_RESULT_JSON="):])
            except Exception:
                pass
    return result


def _latest_manifest_status(agent):
    """Statut du dernier manifeste de l'agent (repli quand AGENT_RESULT_JSON n'est pas émis :
    orchestrator.py ne l'imprime que sur le chemin succès ; sur quota/exception on lit le manifeste)."""
    mans = sorted(glob.glob(os.path.join(S.AGENT_WORK, "runs", "manifests", "run_%s_*.json" % agent)))
    if not mans:
        return None
    return (S.load_json(mans[-1]) or {}).get("status")


def _derive_outcome(result):
    """Traduit le AGENT_RESULT_JSON de l'agent (contrat orchestrator.py : task_outcome ∈ ok/no_work/
    quota_exhausted/exception/…) en RÉSULTAT CANONIQUE pour TaskQueue.apply_outcome. Jamais le seul
    exit code. Retourne : produced | analyzed_no_data | quota | auth_error | failed | waiting_provider."""
    r = result or {}
    pw = int(r.get("proposals_written") or 0)
    lc = int(r.get("llm_calls") or 0)
    cause = (r.get("last_llm_cause") or "").lower()
    outc = (r.get("task_outcome") or "").lower()
    status = (r.get("agent_status") or "").lower()
    if any(k in cause for k in ("auth", "401", "403")):
        return "auth_error"
    if "quota" in outc or "quota" in cause or "429" in cause or "rate" in cause or status == "stopped_quota":
        return "quota"
    if outc in ("exception", "execution_incomplete", "error") or status in ("error", "failed_terminal"):
        return "failed"
    if pw > 0 or outc == "ok" or status == "ok":
        return "produced"                        # travail réel écrit -> revue humaine
    if lc > 0:
        return "analyzed_no_data"                # le LLM a tourné, rien retenu -> zone analysée
    return "waiting_provider"                     # no_work sans appel LLM (provider/modèle indispo) -> réessai


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
        # MIGRATION idempotente : réactive les tâches 'completed' brûlées par l'ancien bug (no_work
        # marqué 'completed' sans proposition valide). Ne touche jamais une tâche réellement terminée.
        reopened = orch.unstick_burned_tasks(queue, policies)
        if reopened:
            L("[cycle] migration: %d tâche(s) 'completed' brûlée(s) réactivée(s): %s" % (len(reopened), ", ".join(reopened)))
            manifest["notes"].append("migration_reopened=%d" % len(reopened))
            manifest["reopened_tasks"] = reopened
        cost = orch.CostPolicy(policies, per_provider_cycle_cap=policies.get("limits", {}).get("max_llm_calls_per_run", 6))

        # 2) agents déterministes (toujours du travail utile, même sans LLM)
        for agent in (deterministic or DEFAULT_DETERMINISTIC):
            st, tail, _res = _run_agent(agent, dry_run)
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
            # exécution réelle : le moteur choisi est IMPOSÉ à l'agent (pas de second routage).
            st, tail, result = _run_agent(agent, dry_run, force_provider=decision["provider"], force_model=decision["model"])
            cost.record(decision["provider"]); ran_agents.add(agent); idem_done.add(ikey)
            _sync_provider_state_from_run(registry, agent)
            # STATUT MÉTIER (jamais le seul returncode). orchestrator.py n'émet AGENT_RESULT_JSON que sur
            # le chemin succès ; sur quota/exception on retombe sur le statut du manifeste.
            result = result or {}
            if not result:
                ms = _latest_manifest_status(agent)
                result = {"agent_status": ms, "task_outcome": ms}
            outcome = _derive_outcome(result)
            if outcome == "failed":
                # échec réel (exception/erreur) -> réessai borné, jamais 'completed'
                queue.finish(task, "failed_retryable", provider=decision["provider"], model=decision["model"],
                             error=result.get("last_llm_cause") or tail, retry_delay_s=120)
            else:
                queue.apply_outcome(task, outcome,
                                    provider=result.get("provider_used") or decision["provider"],
                                    model=result.get("model_used") or decision["model"],
                                    cause=result.get("last_llm_cause"))
            manifest["tasks_executed"].append({"task_id": task["task_id"], "provider": decision["provider"],
                                               "model": decision["model"], "status": task["status"],
                                               "agent_status": result.get("agent_status"),
                                               "task_outcome": outcome, "llm_calls": result.get("llm_calls"),
                                               "proposals_written": result.get("proposals_written"),
                                               "tokens_in": result.get("tokens_in"), "tokens_out": result.get("tokens_out")})
            executed += 1
        if not dry_run:
            S.write_json(os.path.join(base_dir, "idempotency.json"), {"done": list(idem_done)[-300:], "updated_at": orch._iso()})

        manifest["provider_changes"] = registry.snapshot()

        # 5) coordinateur (synthèse pour l'humain)
        _run_coordinator(dry_run)

        # 6) persistance de l'état d'orchestration + résumé de cycle
        registry.save(dry_run); queue.save(dry_run)
        summary = _cycle_summary(cid, manifest, queue, registry)
        _emit_cycle_step_summary(summary)        # page du run (aussi en dry-run) — aucune donnée secrète
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
    # Reflète les modèles retirés (404) découverts par le routeur dans provider_state.json.
    disc = S.load_json(os.path.join(S.AGENT_WORK, "orchestrator", "model_discovery.json"), default={"providers": {}})
    for dpid, pd in disc.get("providers", {}).items():
        for model in pd.get("disabled", []):
            registry.disable_model(dpid, model)


def _run_coordinator(dry_run):
    try:
        subprocess.run([sys.executable, os.path.join(S.AGENT_WORK, "scripts", "build_review_summary.py")],
                       cwd=S.REPO_ROOT, capture_output=True, timeout=120)
    except Exception:
        pass


def _next_cycle_iso():
    """Estimation du prochain cycle planifié (jamais garantie ; GitHub peut différer/annuler les schedules).
    Se cale sur l'intervalle et la minute du cron via env (colocalisés avec le workflow), défaut 6 h / :17."""
    try:
        every = max(1, int(os.environ.get("AXA_CYCLE_EVERY_HOURS", "6")))
        minute = min(59, max(0, int(os.environ.get("AXA_CYCLE_MINUTE", "17"))))
    except ValueError:
        every, minute = 6, 17
    now = orch._now()
    cand = now.replace(minute=minute, second=0, microsecond=0)
    while cand <= now or (cand.hour % every) != 0:
        cand += __import__("datetime").timedelta(hours=1)
        cand = cand.replace(minute=minute, second=0, microsecond=0)
    return orch._iso(cand)


def _cycle_summary(cid, manifest, queue, registry):
    counts = queue.counts()
    # « disponible » = clé détectée ET état available (sinon c'est un moteur non utilisable).
    avail = [pid for pid in registry.data["providers"]
             if registry._p(pid).get("key_detected") and registry.is_available(pid)]
    detected = [pid for pid in registry.data["providers"] if registry._p(pid).get("key_detected")]
    resting = []
    for s in registry.snapshot():
        no_key = not registry._p(s["provider"]).get("key_detected")
        if s["state"] != "available" or no_key:
            state = "cle_absente" if (no_key and s["state"] == "available") else s["state"]
            resting.append({"provider": s["provider"], "state": state, "reprise": s["next_available_at"]})
    ex = manifest["tasks_executed"]
    providers_used = sorted({t["provider"] for t in ex if t.get("provider")})
    llm_calls = sum(int(t.get("llm_calls") or 0) for t in ex)
    tokens_in = sum(int(t.get("tokens_in") or 0) for t in ex)
    tokens_out = sum(int(t.get("tokens_out") or 0) for t in ex)
    # Erreurs (jamais de secret) : tâches en échec réel + fournisseurs nécessitant un humain + causes LLM.
    errors = []
    for t in ex:
        if t.get("status") in ("failed_retryable", "failed_terminal", "waiting_reset"):
            errors.append({"task_id": t["task_id"], "status": t["status"], "cause": t.get("task_outcome")})
    for s in registry.snapshot():
        if s.get("needs_human"):
            errors.append({"provider": s["provider"], "state": s.get("state"), "needs_human": True})
    blocked = counts.get("blocked_human_review", 0)
    ready = counts.get("ready", 0)
    waiting_provider = counts.get("waiting_provider", 0)
    waiting_reset = counts.get("waiting_reset", 0)
    # Quota estimé = compteur prudent d'appels par fournisseur détecté (jamais la clé/valeur).
    quota_est = {pid: registry._p(pid).get("calls_used_est", 0) for pid in detected}
    progression = "attente_revue_humaine" if (blocked > 0 and ready == 0 and waiting_provider == 0 and waiting_reset == 0) \
        else ("attente_fournisseur" if (ready == 0 and (waiting_provider or waiting_reset)) else "en_cours")
    return {
        "cycle_id": cid, "generated_at": orch._iso(), "next_cycle_estimate": _next_cycle_iso(),
        "deterministic_ran": [d["agent"] for d in manifest["deterministic_ran"]],
        "tasks_done_this_cycle": len(ex),
        "tasks_ready": ready, "tasks_waiting_provider": waiting_provider, "tasks_waiting_reset": waiting_reset,
        "tasks_blocked_human_review": blocked, "tasks_completed": counts.get("completed", 0),
        "tasks_failed_terminal": counts.get("failed_terminal", 0),
        "tasks_waiting": ready + waiting_provider + waiting_reset,
        "providers_detected": detected, "providers_available": avail, "providers_resting": resting,
        "providers_used": providers_used, "quota_estimate_calls": quota_est,
        "llm_calls": llm_calls, "tokens_in_est": tokens_in, "tokens_out_est": tokens_out,
        "errors": errors, "progression": progression,
        "reopened_tasks": manifest.get("reopened_tasks", []),
        "incidents_human": [s["provider"] for s in registry.snapshot() if s.get("needs_human")],
        "next_priority": (manifest["tasks_deferred"][0]["task_id"] if manifest["tasks_deferred"] else None),
    }


def _emit_cycle_step_summary(s):
    """Résumé lisible sur la page du run (aucune donnée secrète : ids de fournisseurs, compteurs, true/false)."""
    prog = {"attente_revue_humaine": "[PAUSE] En attente de revue humaine (aucun retraitement en boucle)",
            "attente_fournisseur": "[ATTENTE] En attente d'un fournisseur (réessai automatique au prochain cycle)",
            "en_cours": "[ACTIF] Progression active"}.get(s["progression"], s["progression"])
    lines = ["", "### Chef d'orchestre — résumé du cycle", "", "```text",
             "Prochain cycle estimé : %s (indicatif)" % s["next_cycle_estimate"],
             "État : %s" % prog,
             "Déterministes : %s" % (", ".join(s["deterministic_ran"]) or "aucun"),
             "Tâches — exécutées ce cycle : %d" % s["tasks_done_this_cycle"],
             "Tâches — ready: %d · waiting_provider: %d · waiting_reset: %d · blocked_human_review: %d · completed: %d · failed_terminal: %d" % (
                 s["tasks_ready"], s["tasks_waiting_provider"], s["tasks_waiting_reset"],
                 s["tasks_blocked_human_review"], s["tasks_completed"], s["tasks_failed_terminal"]),
             "Fournisseurs détectés : %s" % (", ".join(s["providers_detected"]) or "aucun"),
             "Fournisseurs disponibles : %s" % (", ".join(s["providers_available"]) or "aucun"),
             "Fournisseur(s) utilisé(s) ce cycle : %s" % (", ".join(s["providers_used"]) or "aucun"),
             "Quota estimé (appels cumulés/fournisseur) : %s" % (json.dumps(s["quota_estimate_calls"], ensure_ascii=False)),
             "Appels LLM ce cycle : %d · tokens ~ entrée %d / sortie %d" % (s["llm_calls"], s["tokens_in_est"], s["tokens_out_est"]),
             "Erreurs : %s" % (json.dumps(s["errors"], ensure_ascii=False) if s["errors"] else "aucune"),
             "Tâches réactivées (migration) : %s" % (", ".join(s["reopened_tasks"]) if s["reopened_tasks"] else "aucune"),
             "```", ""]
    if s["tasks_blocked_human_review"] > 0:
        lines.append("_%d proposition(s) attendent une revue humaine — voir `agent-work/coordinator/READY_FOR_REVIEW.md`._" % s["tasks_blocked_human_review"])
    S.github_summary("\n".join(lines))


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
