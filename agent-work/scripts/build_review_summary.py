#!/usr/bin/env python3
"""Coordinateur — DÉTERMINISTE. Agrège les sorties, valide, déduplique, détecte conflits, score, et
produit une synthèse COURTE pour Claude. Distingue clairement résultat RÉEL / fixture de démonstration,
et anomalie NOUVELLE / CONNUE / CORRIGÉE / RÉGRESSION. Ne présente jamais un mock comme une vraie proposition.
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
REAL_ORIGINS = {"deterministic", "llm"}
FIXTURE_ORIGINS = {"example_fixture", "mock"}


def _load_all():
    props = []
    for d in PENDING_DIRS:
        for f in sorted(glob.glob(os.path.join(S.REPO_ROOT, d, "*.json"))):
            try:
                p = S.load_json(f)
            except Exception:
                continue
            if VP.validate(p)[0]:
                p["_file"] = os.path.relpath(f, S.REPO_ROOT).replace("\\", "/")
                props.append(p)
    return props


def _dedupe(props):
    seen, out, removed = set(), [], 0
    for p in props:
        fp = DD.fingerprint(p)
        if fp in seen:
            removed += 1; continue
        seen.add(fp); out.append(p)
    return out, removed


def _agent_priority(pid, agents_cfg):
    return next((a.get("priority_default", 3) for a in agents_cfg["agents"] if a["id"] == pid), 3)


def _score(p, agents_cfg):
    conf = float(p.get("confidence", 0))
    ap = _agent_priority(p.get("agent_id"), agents_cfg) / 5.0
    reg = 0.2 if p.get("regulatory_status", "none") != "none" else 0.0
    risk = 0.1 if p.get("risks") else 0.0
    return round(conf * 0.5 + ap * 0.3 + reg + risk, 4)


def _conflicts(props):
    conflicts, groups = [], {}
    for p in props:
        chg = p.get("proposed_change", {})
        if chg.get("operation") == "relation":
            pl = chg.get("payload", {})
            groups.setdefault((pl.get("node_source"), pl.get("node_cible")), []).append(p)
    for key, items in groups.items():
        rels = {i["proposed_change"]["payload"].get("type_relation") for i in items}
        if len(items) > 1 and len(rels) > 1:
            conflicts.append({"kind": "relation_contradictoire", "nodes": list(key),
                              "proposals": [i["proposal_id"] for i in items]})
    return conflicts


def _latest_quality_anomalies():
    files = sorted(glob.glob(os.path.join(S.REPO_ROOT, "agent-work/quality/reports/quality_*.json")))
    if not files:
        return {"new": [], "known": [], "corrected": []}
    return S.load_json(files[-1]).get("anomalies", {"new": [], "known": [], "corrected": []})


def _human_action(p):
    if p.get("regulatory_status", "none") not in ("none",):
        return "validation réglementaire humaine (aucune interprétation automatique)"
    t = p["task"].get("type")
    return {"quality": "vérification documentaire / correction manuelle",
            "coverage": "vérification documentaire humaine (donnée structurée manquante)",
            "routing-metrics": "investiguer la régression du moteur",
            "official-source": "vérifier la source officielle",
            "adversarial-test": "exécuter le test contre le moteur"}.get(t, "revue humaine")


def _stats(props, deduped, fixtures):
    agg = {"runs": 0, "llm_calls": 0, "tokens_in_est": 0, "tokens_out_est": 0,
           "proposals_generated": 0, "proposals_pending_real": len(props), "proposals_fixtures": len(fixtures),
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
        pa = per_agent.setdefault(m.get("agent_id", "?"), {"runs": 0, "proposals_generated": 0})
        pa["runs"] += 1
        pa["proposals_generated"] += int(c.get("proposals_generated", 0))
    return agg, per_agent


def build():
    agents_cfg = S.load_agents_config()
    allp = _load_all()
    real = [p for p in allp if p.get("origin") in REAL_ORIGINS]
    fixtures = [p for p in allp if p.get("origin") in FIXTURE_ORIGINS]
    real, deduped = _dedupe(real)
    for p in real:
        p["_score"] = _score(p, agents_cfg)
    real.sort(key=lambda p: -p["_score"])

    conflicts = _conflicts(real)
    anomalies = _latest_quality_anomalies()
    regressions = [p for p in real if p["task"].get("type") == "routing-metrics"]
    source_changes = [p for p in real if p.get("agent_id") == "official-sources"]
    top = real[:5]

    ready = {
        "generated_at": S.now_iso(),
        "high_priority": [{
            "proposal_id": p["proposal_id"], "agent": p["agent_id"], "score": p["_score"],
            "type": p["task"].get("type"), "confidence": p.get("confidence"),
            "origin": p.get("origin"), "target_file": p.get("target", {}).get("file"),
            "regulatory_status": p.get("regulatory_status", "none"),
            "risk": ("réglementaire" if p.get("regulatory_status", "none") != "none" else (p.get("risks") or ["faible"])[0])[:80],
            "human_action": _human_action(p), "file": p.get("_file"),
            "summary": p.get("reasoning_summary", "")[:160],
        } for p in top],
        "anomalies": anomalies,
        "regressions": [{"proposal_id": p["proposal_id"], "detail": p["proposed_change"]["payload"].get("regressions"), "file": p["_file"]} for p in regressions],
        "official_source_changes": [{"proposal_id": p["proposal_id"], "change_kind": p["proposed_change"]["payload"].get("change_kind"),
                                     "regulatory_status": p.get("regulatory_status"), "url": p.get("source", {}).get("url"), "file": p["_file"]} for p in source_changes[:10]],
        "conflicts": conflicts,
        "recommended_order": [p["proposal_id"] for p in top],
        "counts": {"real_pending": len(real), "fixtures": len(fixtures), "by_agent": _by_agent(real)},
        "fixtures_note": "%d fixture(s) de démonstration exclue(s) de la priorisation (origin example_fixture/mock)." % len(fixtures),
    }

    stats, per_agent = _stats(real, deduped, fixtures)
    saved = _estimate_saved(real)
    ready["estimated_work_saved"] = saved

    md = _render_md(ready, top, anomalies, regressions, source_changes, conflicts, saved, len(fixtures))
    stats["summary_bytes"] = len(md.encode("utf-8"))
    ready["counts"]["summary_bytes"] = stats["summary_bytes"]

    S.write_json(os.path.join(S.REPO_ROOT, COORD, "READY_FOR_REVIEW.json"), ready)
    with open(os.path.join(S.REPO_ROOT, COORD, "READY_FOR_REVIEW.md"), "w", encoding="utf-8") as f:
        f.write(md)
    S.write_json(os.path.join(S.REPO_ROOT, COORD, "conflicts.json"), {"generated_at": S.now_iso(), "conflicts": conflicts})
    S.write_json(os.path.join(S.REPO_ROOT, COORD, "statistics.json"), {"generated_at": S.now_iso(), "totals": stats, "per_agent": per_agent})
    print("[coordinator] réel=%d fixtures=%d dédupliquées=%d régressions=%d anomalies_nouv=%d résumé=%d o" % (
        len(real), len(fixtures), deduped, len(regressions), len(anomalies.get("new", [])), stats["summary_bytes"]))
    return ready


def _by_agent(props):
    d = {}
    for p in props:
        d[p["agent_id"]] = d.get(p["agent_id"], 0) + 1
    return d


def _estimate_saved(real):
    n = len(real)
    if n == 0:
        return "aucune proposition réelle en attente"
    return ("%d contrôle(s)/trou(s) déjà transformé(s) en incidents structurés et sourcés : Claude examine "
            "les %d éléments prioritaires (~%d min économisées) au lieu de refaire l'analyse." % (n, min(5, n), n * 3))


def _render_md(rj, top, anomalies, regressions, sources, conflicts, saved, n_fixtures):
    L = ["# Prêt pour examen", "",
         "_Généré le %s. Lire CE fichier d'abord ; n'examiner que les éléments ci-dessous._" % rj["generated_at"], "",
         "**Réel en attente : %d.** %s" % (rj["counts"]["real_pending"], saved)]
    if n_fixtures:
        L.append("_(%d fixture(s) de démonstration exclue(s) de la priorisation.)_" % n_fixtures)
    L += ["", "## Haute priorité (résultats réels)"]
    if not top:
        L.append("_(aucun)_")
    for i, p in enumerate(top, 1):
        reg = " · **réglementaire → validation humaine**" if p.get("regulatory_status", "none") != "none" else ""
        L += ["%d. **%s** — %s (score %.2f)%s" % (i, p["task"].get("type"), p["proposal_id"], p["_score"], reg),
              "   - fichier : `%s` · cible : `%s`" % (p.get("_file"), p.get("target", {}).get("file", "?")),
              "   - risque : %s · action : %s" % (
                  ("réglementaire" if reg else (p.get("risks") or ["faible"])[0])[:70], _human_action(p)),
              "   - %s" % p.get("reasoning_summary", "")[:150]]
    L += ["", "## Anomalies qualité",
          "- **Nouvelles** : %s" % (", ".join(anomalies.get("new", [])) or "aucune"),
          "- **Connues** : %s" % (", ".join(anomalies.get("known", [])) or "aucune"),
          "- **Corrigées** : %s" % (", ".join(anomalies.get("corrected", [])) or "aucune")]
    L += ["", "## Régressions (tests de routage)"]
    L.append("- %d régression(s) : %s" % (len(regressions), "; ".join(str(r["proposed_change"]["payload"].get("regressions")) for r in regressions)) if regressions else "- aucune")
    L += ["", "## Changements de sources officielles"]
    if sources:
        for p in sources[:10]:
            L.append("- %s — %s (statut `%s`, interprétation NON effectuée)" % (
                p.get("source", {}).get("url"), p["proposed_change"]["payload"].get("change_kind"), p.get("regulatory_status")))
    else:
        L.append("- aucun")
    L += ["", "## Conflits", ("- " + "; ".join(str(c) for c in conflicts)) if conflicts else "- aucun",
          "", "## Ordre recommandé", ", ".join(rj["recommended_order"]) or "—", "",
          "---", "Reprise : voir `agent-work/README.md` § « Reprise avec Claude ». Ne jamais relire tous les logs."]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    argparse.ArgumentParser().parse_args()
    build()
