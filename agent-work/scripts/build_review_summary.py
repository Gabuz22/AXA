#!/usr/bin/env python3
"""Coordinateur — DÉTERMINISTE. Ne fait pas le travail des agents. Il lit les propositions en attente,
valide leur schéma, élimine les doublons stricts, repère les conflits, calcule un score de priorité,
et produit une synthèse COURTE pour Claude (READY_FOR_REVIEW.md/.json) + conflicts.json + statistics.json.

Objectif : Claude reprend le travail en lisant UN seul fichier, puis n'examine que les propositions
prioritaires — au lieu de relire tous les logs.
"""
import os, glob, json, argparse
import safety_checks as S
import deduplicate as DD
import validate_proposal as VP

PENDING_DIRS = [
    "agent-work/extraction/pending", "agent-work/official-sources/pending",
    "agent-work/official-sources/changes", "agent-work/concepts/pending",
    "agent-work/tests/pending", "agent-work/ux-ai/pending", "agent-work/quality/incidents",
]
COORD = "agent-work/coordinator"


def _load_all():
    props = []
    for d in PENDING_DIRS:
        for f in sorted(glob.glob(os.path.join(S.REPO_ROOT, d, "*.json"))):
            try:
                p = S.load_json(f)
            except Exception:
                continue
            ok, _ = VP.validate(p)
            if ok:
                p["_file"] = os.path.relpath(f, S.REPO_ROOT).replace("\\", "/")
                props.append(p)
    return props


def _dedupe(props):
    seen, out, removed = {}, [], 0
    for p in props:
        fp = DD.fingerprint(p)
        if fp in seen:
            removed += 1
            continue
        seen[fp] = 1
        out.append(p)
    return out, removed


def _agent_priority(pid, agents_cfg):
    for a in agents_cfg["agents"]:
        if a["id"] == pid:
            return a.get("priority_default", 3)
    return 3


def _score(p, agents_cfg):
    conf = float(p.get("confidence", 0))
    ap = _agent_priority(p.get("agent_id"), agents_cfg) / 5.0
    reg = 0.2 if p.get("regulatory_status", "none") not in ("none",) else 0.0
    risk = 0.1 if p.get("risks") else 0.0
    return round(conf * 0.5 + ap * 0.3 + reg + risk, 4)


def _conflicts(props):
    conflicts = []
    groups = {}
    for p in props:
        chg = p.get("proposed_change", {})
        pl = chg.get("payload", {})
        if chg.get("operation") == "relation":
            key = (pl.get("node_source"), pl.get("node_cible"))
            groups.setdefault(key, []).append(p)
    for key, items in groups.items():
        rels = {i["proposed_change"]["payload"].get("type_relation") for i in items}
        if len(items) > 1 and len(rels) > 1:
            conflicts.append({"kind": "relation_contradictoire", "nodes": list(key),
                              "proposals": [i["proposal_id"] for i in items], "relations": sorted(str(r) for r in rels)})
    return conflicts


def _stats(props, deduped):
    agg = {"runs": 0, "llm_calls": 0, "tokens_in_est": 0, "tokens_out_est": 0,
           "proposals_generated": 0, "proposals_pending": len(props),
           "proposals_deduplicated": deduped, "proposals_rejected_auto": 0, "summary_bytes": 0}
    per_agent = {}
    for f in glob.glob(os.path.join(S.REPO_ROOT, "agent-work/runs/manifests", "*.json")):
        try:
            m = S.load_json(f)
        except Exception:
            continue
        agg["runs"] += 1
        c = m.get("counters", {})
        for k in ("llm_calls", "tokens_in_est", "tokens_out_est", "proposals_generated", "proposals_rejected_auto"):
            agg[k] += int(c.get(k, 0))
        a = m.get("agent_id", "?")
        pa = per_agent.setdefault(a, {"runs": 0, "proposals_generated": 0, "proposals_rejected_auto": 0, "llm_calls": 0})
        pa["runs"] += 1
        pa["proposals_generated"] += int(c.get("proposals_generated", 0))
        pa["proposals_rejected_auto"] += int(c.get("proposals_rejected_auto", 0))
        pa["llm_calls"] += int(c.get("llm_calls", 0))
    return agg, per_agent


def build():
    agents_cfg = S.load_agents_config()
    props = _load_all()
    props, deduped = _dedupe(props)
    for p in props:
        p["_score"] = _score(p, agents_cfg)
    props.sort(key=lambda p: -p["_score"])

    conflicts = _conflicts(props)
    top = props[:5]
    failing_tests = [p for p in props if p.get("agent_id") == "adversarial-tests"]
    source_changes = [p for p in props if p.get("agent_id") == "official-sources"]

    ready_json = {
        "generated_at": S.now_iso(),
        "high_priority": [{
            "proposal_id": p["proposal_id"], "agent": p["agent_id"], "score": p["_score"],
            "type": p["task"].get("type"), "confidence": p.get("confidence"),
            "target_file": p.get("target", {}).get("file"),
            "regulatory_status": p.get("regulatory_status", "none"),
            "validation_required": p.get("validation_required", True),
            "file": p.get("_file"), "summary": p.get("reasoning_summary", "")[:180],
        } for p in top],
        "new_failing_tests": [{"proposal_id": p["proposal_id"], "famille": p["target"].get("section"),
                               "file": p.get("_file")} for p in failing_tests[:10]],
        "official_source_changes": [{"proposal_id": p["proposal_id"], "status": p.get("regulatory_status"),
                                     "url": p.get("source", {}).get("url"), "file": p.get("_file")} for p in source_changes[:10]],
        "conflicts": conflicts,
        "recommended_order": [p["proposal_id"] for p in top],
        "counts": {"pending_total": len(props), "by_agent": _count_by_agent(props)},
    }

    stats, per_agent = _stats(props, deduped)
    saved = _estimate_saved(props)
    ready_json["estimated_work_saved"] = saved

    md = _render_md(ready_json, top, failing_tests, source_changes, conflicts, saved)
    stats["summary_bytes"] = len(md.encode("utf-8"))
    ready_json["counts"]["summary_bytes"] = stats["summary_bytes"]

    S.write_json(os.path.join(S.REPO_ROOT, COORD, "READY_FOR_REVIEW.json"), ready_json)
    with open(os.path.join(S.REPO_ROOT, COORD, "READY_FOR_REVIEW.md"), "w", encoding="utf-8") as f:
        f.write(md)
    S.write_json(os.path.join(S.REPO_ROOT, COORD, "conflicts.json"), {"generated_at": S.now_iso(), "conflicts": conflicts})
    stats["generated_at"] = S.now_iso()
    S.write_json(os.path.join(S.REPO_ROOT, COORD, "statistics.json"), {"generated_at": S.now_iso(), "totals": stats, "per_agent": per_agent})
    print("[coordinator] pending=%d dédupliquées=%d conflits=%d résumé=%d octets" %
          (len(props), deduped, len(conflicts), stats["summary_bytes"]))
    return ready_json


def _count_by_agent(props):
    d = {}
    for p in props:
        d[p["agent_id"]] = d.get(p["agent_id"], 0) + 1
    return d


def _estimate_saved(props):
    n = len(props)
    if n == 0:
        return "aucune proposition en attente"
    return ("%d micro-zones déjà transformées en propositions sourcées et structurées : "
            "Claude examine ces %d éléments prioritaires au lieu de refaire l'analyse préparatoire." % (n, min(5, n)))


def _render_md(rj, top, failing, sources, conflicts, saved):
    L = ["# Prêt pour examen", "",
         "_Généré le %s par le coordinateur. Lire CE fichier d'abord ; n'examiner que les éléments ci-dessous._" % rj["generated_at"], "",
         "**En attente : %d proposition(s).** %s" % (rj["counts"]["pending_total"], saved), "",
         "## Haute priorité"]
    if not top:
        L.append("_(aucune)_")
    for i, p in enumerate(top, 1):
        L += ["%d. **%s** — %s (score %.2f, confiance %s)" % (
                i, p["task"].get("type"), p["proposal_id"], p["_score"], p.get("confidence")),
              "   - fichier proposition : `%s`" % p.get("_file"),
              "   - cible : `%s`%s" % (p.get("target", {}).get("file", "?"),
                  " · **réglementaire → validation humaine**" if p.get("regulatory_status", "none") not in ("none",) else ""),
              "   - %s" % (p.get("reasoning_summary", "")[:160])]
    L += ["", "## Tests nouveaux (à exécuter contre le moteur)"]
    L.append("- %d proposition(s) de test ; familles : %s" % (
        len(failing), ", ".join(sorted({p["target"].get("section", "?") for p in failing})) or "—") if failing else "- _(aucun)_")
    L += ["", "## Changements de sources officielles"]
    if sources:
        for p in sources[:10]:
            L.append("- %s — statut `%s` — %s (interprétation NON effectuée)" % (
                p["proposal_id"], p.get("regulatory_status"), p.get("source", {}).get("url")))
    else:
        L.append("- _(aucun)_")
    L += ["", "## Conflits"]
    if conflicts:
        for c in conflicts:
            L.append("- %s entre %s : %s" % (c["kind"], c.get("proposals"), c.get("relations")))
    else:
        L.append("- _(aucun)_")
    L += ["", "## Ordre recommandé", ", ".join(rj["recommended_order"]) or "—", "",
          "---", "Protocole de reprise : voir `agent-work/README.md` § « Reprise du projet avec Claude ». "
          "Ne jamais demander à Claude de relire tous les logs."]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="(sans effet Git ; écrit la synthèse locale)")
    ap.parse_args()
    build()
