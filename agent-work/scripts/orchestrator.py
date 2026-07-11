#!/usr/bin/env python3
"""Orchestrateur d'un run d'agent (petit, borné, fail-closed).

1 agent, 1 micro-tâche, <= N propositions. Étapes : préflight sécurité -> sélection de tâche ->
exécution de l'agent -> validation (schéma + règles) -> déduplication -> écriture des propositions
autorisées dans agent-work/<agent>/pending -> manifeste de run. Aucune opération Git ici : le commit,
le contrôle de périmètre et la PR sont gérés par le workflow (et sautés en dry-run).

Usage :
  python agent-work/scripts/orchestrator.py --agent quality [--dry-run] [--mock]
"""
import os, sys, argparse, importlib, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import safety_checks as S
import quota_manager as Q
import select_task as ST
import deduplicate as DD
import validate_proposal as VP
import json

AGENT_MODULES = {
    "quality": "agents.quality",
    "coverage-gaps": "agents.coverage_gaps",
    "extraction-llm": "agents.extraction_llm",
    "extraction-cg": "agents.extraction_cg",
    "official-sources": "agents.official_sources",
    "concepts": "agents.concepts",
    "adversarial-tests": "agents.adversarial_tests",
    "ux-ai": "agents.ux_ai",
    "corpus-explorer": "agents.corpus_explorer",
    "knowledge-curator": "agents.knowledge_curator",
}


class Ctx:
    def __init__(self):
        self._seq = 0
        self.provider_used = None
        self.model_used = None
        self.self_wrote = False
        self.summary = {}
        self.last_llm_cause = None

    def seq_next(self):
        self._seq += 1
        return "%03d" % self._seq


def build_router(policies, providers_cfg, need_llm, dry_run, logf):
    # Diag non sensible (sous-processus) : le forçage de l'orchestrateur est-il présent avant build_router ?
    logf("[orch] before build_router: AXA_FORCE_PROVIDER present: %s | AXA_FORCE_MODEL present: %s | need_llm=%s" % (
        "true" if os.environ.get("AXA_FORCE_PROVIDER") else "false",
        "true" if os.environ.get("AXA_FORCE_MODEL") else "false", need_llm))
    if not need_llm:
        return None
    import provider_router as PR
    return PR.ProviderRouter(providers_cfg, policies, logger=logf)


def main():
    result = {
        "agent_status": "failed_retryable",
        "provider_used": None,
        "model_used": None,
        "llm_calls": 0,
        "tokens_in": 0,
        "tokens_out": 0,
        "proposals_written": 0,
        "last_llm_cause": None,
        "task_outcome": "execution_incomplete",
    }

    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True, choices=list(AGENT_MODULES.keys()))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--mock", action="store_true", help="produit un exemple sans appeler de LLM ni le réseau")
    args = ap.parse_args()

    policies = S.load_policies()
    agents_cfg = S.load_agents_config()
    providers_cfg = S.load_providers_config()
    acfg = next((a for a in agents_cfg["agents"] if a["id"] == args.agent), None)
    if not acfg:
        print("[orch] agent inconnu: %s" % args.agent); return 2

    run_id = S.gen_run_id(args.agent)
    log_lines = []
    def logf(m):
        print(m); log_lines.append(S.redact_secrets(m, providers_cfg))

    logf("[orch] run=%s agent=%s dry_run=%s mock=%s" % (run_id, args.agent, args.dry_run, args.mock))

    manifest = {"run_id": run_id, "agent_id": args.agent, "started_at": S.now_iso(),
                "finished_at": None, "dry_run": bool(args.dry_run), "status": "error",
                "task_id": None, "provider_used": None, "model_used": None,
                "counters": {"llm_calls": 0, "tokens_in_est": 0, "tokens_out_est": 0,
                             "proposals_generated": 0, "proposals_written": 0,
                             "proposals_deduplicated": 0, "proposals_rejected_auto": 0},
                "notes": []}

    need_llm = bool(acfg.get("uses_llm")) and not args.mock
    try:
        S.preflight(policies, providers_cfg, need_llm)  # fail-closed sur usage payant
    except S.SafetyError as e:
        manifest["status"] = "refused_preflight"; manifest["notes"].append(str(e))
        manifest["finished_at"] = S.now_iso()
        _finish(manifest, log_lines, args.dry_run)
        logf("[orch] REFUS préflight : %s" % e); return 3

    ctx = Ctx()
    ctx.agent_id = args.agent
    ctx.uses_llm = bool(acfg.get("uses_llm"))
    ctx.run_id = run_id
    ctx.policies = policies
    ctx.agents_cfg = agents_cfg
    ctx.providers_cfg = providers_cfg
    ctx.dry_run = bool(args.dry_run)
    ctx.mock = bool(args.mock)
    ctx.limits = policies.get("limits", {})
    ctx.task = ST.select(args.agent) or {}
    ctx.budget = Q.Budget(max_llm_calls=ctx.limits.get("max_llm_calls_per_run", 6),
                          max_tokens=ctx.limits.get("max_tokens_per_run", 40000))
    ctx.router = build_router(policies, providers_cfg, need_llm, args.dry_run, logf)
    manifest["task_id"] = ctx.task.get("id")

    # Exécution de l'agent (bornée). QuotaExhausted => arrêt propre.
    try:
        mod = importlib.import_module(AGENT_MODULES[args.agent])
        proposals, notes = mod.run(ctx)
        manifest["notes"].extend(notes)
    except Q.QuotaExhausted as e:
        manifest["status"] = "stopped_quota"; manifest["notes"].append("quota: %s" % e)
        manifest["provider_used"] = ctx.provider_used; manifest["model_used"] = ctx.model_used
        manifest["counters"].update(ctx.budget.as_counters())
        manifest["finished_at"] = S.now_iso(); _finish(manifest, log_lines, args.dry_run)
        logf("[orch] arrêt propre (quota) : %s" % e);
        result.update({
        "agent_status": "failed_retryable",
        "last_llm_cause": f"quota: {e}",
        "task_outcome": "quota_exhausted",
        })
        return 0
    except Exception as e:
        manifest["notes"].append("erreur agent: %s" % e)
        logf("[orch] ERREUR agent: %s\n%s" % (e, traceback.format_exc()))
    
        result.update({
            "agent_status": "failed_retryable",
            "last_llm_cause": f"exception: {type(e).__name__}: {e}",
            "task_outcome": "exception",
        })
    
        manifest["finished_at"] = S.now_iso()
        _finish(manifest, log_lines, args.dry_run)

        return 1

    manifest["provider_used"] = ctx.provider_used
    manifest["model_used"] = ctx.model_used
    manifest["counters"].update(ctx.budget.as_counters())
    manifest["counters"]["proposals_generated"] = len(proposals)

    out_dir = S.REPO_ROOT + "/" + acfg["output_dir"]
    dedup_dirs = [out_dir]
    for sub in ("reviewed", "rejected"):
        d = os.path.join(os.path.dirname(out_dir.rstrip("/")), sub)
        if os.path.isdir(d):
            dedup_dirs.append(d)
    # Les agents self_wrote gèrent leurs propres fichiers à identifiant stable (dédup intrinsèque).
    existing = {} if ctx.self_wrote else DD.existing_fingerprints(dedup_dirs)

    written = deduped = rejected = 0
    for p in proposals:
        ok, errs = VP.validate(p, policies)
        p.setdefault("automatic_checks", {})
        p["automatic_checks"]["schema_valid"] = ok
        p["automatic_checks"]["scope_allowed"] = True  # écriture confinée à agent-work/
        if not ok:
            rejected += 1
            logf("[orch] proposition rejetée (auto): %s" % "; ".join(errs[:3]))
            continue
        fp = DD.fingerprint(p)
        if fp in existing:
            deduped += 1
            p["automatic_checks"]["duplicate_detected"] = True
            logf("[orch] doublon strict ignoré: %s" % p["proposal_id"])
            continue
        existing[fp] = p["proposal_id"]
        p["automatic_checks"]["duplicate_detected"] = False
        if not ctx.dry_run and not ctx.self_wrote:
            S.write_json(os.path.join(out_dir, p["proposal_id"] + ".json"), p,
                         max_bytes=ctx.limits.get("max_output_bytes_per_proposal", 65536))
        written += 1

    manifest["counters"]["proposals_written"] = written
    manifest["counters"]["proposals_deduplicated"] = deduped
    manifest["counters"]["proposals_rejected_auto"] = rejected
    manifest["status"] = "ok" if written else "no_work"
    manifest["finished_at"] = S.now_iso()

    if not ctx.dry_run and ctx.task.get("id"):
        ST.mark_attempt(args.agent, ctx.task["id"], status="todo", dry_run=ctx.dry_run)

    _finish(manifest, log_lines, args.dry_run)
    logf("[orch] terminé: écrites=%d dédupliquées=%d rejetées=%d status=%s" %
         (written, deduped, rejected, manifest["status"]))
    _emit_summary(args.agent, ctx, manifest, written, deduped, rejected)

    result.update({
    "agent_status": manifest["status"],
    "provider_used": ctx.provider_used,
    "model_used": ctx.model_used,
    "llm_calls": manifest["counters"]["llm_calls"],
    "tokens_in": manifest["counters"]["tokens_in_est"],
    "tokens_out": manifest["counters"]["tokens_out_est"],
    "proposals_written": written,
    "last_llm_cause": ctx.last_llm_cause,
    "task_outcome": manifest["status"],
    })

    print("AGENT_RESULT_JSON=" + json.dumps(result, ensure_ascii=False))

    return 0

def _emit_summary(agent, ctx, manifest, written, deduped, rejected):
    """Résumé lisible sur la page du run GitHub Actions (aucun secret)."""
    mode = "dry-run" if manifest["dry_run"] else "live"
    lines = ["", "### Agent %s — résumé" % agent, "", "```text", "Mode : %s" % mode]
    for k, v in (ctx.summary or {}).items():
        lines.append("%s : %s" % (k, v))
    lines += [
        "Propositions générées : %d" % manifest["counters"]["proposals_generated"],
        "Propositions retenues : %d" % written,
        "Dédupliquées : %d   Rejetées (auto) : %d" % (deduped, rejected),
        "Statut du run : %s" % manifest["status"],
        "```", ""]
    S.github_summary("\n".join(lines))


def _finish(manifest, log_lines, dry_run):
    """Écrit le manifeste + le log localement (rapport local ; aucune opération Git ici)."""
    S.write_json(os.path.join(S.AGENT_WORK, "runs", "manifests", manifest["run_id"] + ".json"), manifest)
    log_path = os.path.join(S.AGENT_WORK, "runs", "logs", manifest["run_id"] + ".log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines) + "\n")


if __name__ == "__main__":
    sys.exit(main())
