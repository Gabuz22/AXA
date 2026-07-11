#!/usr/bin/env python3
"""Manager STRATÉGIQUE — analyse la plateforme et produit des recommandations VÉRIFIABLES. 0 token.

Ne modifie JAMAIS la connaissance ni l'architecture : il lit les métriques (couverture, backlog, coût,
revue, scores fournisseurs) et propose des priorités (approfondir une zone, prioriser un type de tâche,
router les tâches simples vers le meilleur fournisseur, renforcer un garde-fou déterministe, signaler une
lacune persistante). L'humain décide. Déterministe, réutilisable pour tout domaine.
"""


def _load(load_json, path, default):
    try:
        return load_json(path, default=default)
    except Exception:
        return default


def analyze(load_json, repo_path, domain="axa-contrat"):
    cov = _load(load_json, repo_path("agent-work/knowledge/coverage.json"), {}) or {}
    backlog = _load(load_json, repo_path("agent-work/knowledge/tasks.json"), {"tasks": []}) or {"tasks": []}
    ledger = _load(load_json, repo_path("agent-work/knowledge/cost_ledger.json"), {"weeks": {}}) or {"weeks": {}}
    scores = (_load(load_json, repo_path("agent-work/runs/provider_scores.json"), {}) or {}).get("providers", {})

    subjects = cov.get("subjects", {})
    ranked = sorted(({"subject": s, "depth_score": r.get("depth_score", 0.0),
                      "weak_axes": r.get("weak_axes", []),
                      "semantic_coverage": r.get("semantic_coverage")}
                     for s, r in subjects.items()), key=lambda x: x["depth_score"])

    pend = [t for t in backlog.get("tasks", []) if t.get("status") == "pending"]
    by_type = {}
    for t in pend:
        by_type[t["type"]] = by_type.get(t["type"], 0) + 1
    persistent = sorted((t for t in pend), key=lambda t: t.get("first_seen") or "")[:10]

    best_provider = None
    if scores:
        best_provider = max(scores.items(), key=lambda kv: (kv[1].get("quality", 0), kv[1].get("success_rate", 0)))[0]

    recos = []
    for s in ranked[:3]:
        if s["depth_score"] < 0.8:
            recos.append({"type": "approfondir", "target": s["subject"], "priority": 4,
                          "rationale": "profondeur %.2f, axes faibles: %s" % (s["depth_score"], ", ".join(s["weak_axes"])),
                          "action": "orienter knowledge-builder / extraction sur ce sujet"})
    if by_type:
        dom = max(by_type.items(), key=lambda kv: kv[1])
        recos.append({"type": "prioriser_tache", "target": dom[0], "priority": 3,
                      "rationale": "%d tâches '%s' en attente (type dominant)" % (dom[1], dom[0]),
                      "action": "s'assurer qu'un exécuteur traite ce type"})
    if best_provider:
        recos.append({"type": "router", "target": best_provider, "priority": 2,
                      "rationale": "meilleur score qualité/fiabilité mesuré",
                      "action": "réserver les tâches complexes à ce fournisseur ; tâches simples aux modèles rapides"})
    # lacune persistante : tâche pending la plus ancienne
    if persistent:
        oldest = persistent[0]
        recos.append({"type": "lacune_persistante", "target": oldest.get("subject") or oldest.get("type"),
                      "priority": 3, "rationale": "tâche '%s' en attente depuis %s" % (oldest.get("type"), oldest.get("first_seen")),
                      "action": "vérifier pourquoi elle n'est pas exécutée (exécuteur manquant ? budget ?)"})

    return {
        "generated_at": None, "domain": domain,
        "subjects_ranked": ranked,
        "backlog_pending": len(pend), "backlog_by_type": by_type,
        "persistent_tasks": [{"task_id": t["task_id"], "type": t["type"], "subject": t.get("subject"),
                              "first_seen": t.get("first_seen")} for t in persistent],
        "cost_weeks": ledger.get("weeks", {}),
        "best_provider": best_provider,
        "recommendations": sorted(recos, key=lambda r: -r["priority"]),
        "note": "recommandations vérifiables ; le manager ne modifie jamais la connaissance ni l'architecture.",
    }
