#!/usr/bin/env python3
"""Générateur DÉTERMINISTE de tâches de connaissance — le système découvre lui-même son travail.

Réunit deux familles de tâches, toutes calculées sur le graphe (zéro token) :
  • APPROFONDISSEMENT (coverage_model) : relier / expliquer / comparer / environnement / sourcer /
    normaliser / rafraichir — les axes de profondeur faibles d'un sujet, même s'il est déjà « connu ».
  • OPÉRATIONS (knowledge_ops) : doublons, candidats de contradiction, nœuds périmés.

Sortie : un backlog persistant `agent-work/knowledge/tasks.json`, dédupliqué par id stable (idempotent).
Les EXÉCUTEURS (agents de capacité, phase 3+) y puisent les tâches de leur type. Rien n'est enfilé dans
la file d'exécution tant qu'aucun exécuteur n'existe (pas de tâche no-op).
"""
import knowledge_graph as KG
import coverage_model as CM
import knowledge_ops as KO

BACKLOG = "agent-work/knowledge/tasks.json"


def generate(graph, domain, subjects, threshold=0.6):
    """Toutes les tâches déterministes pour une liste de sujets. Ids stables, aucune duplication interne."""
    by_id = {}

    def put(t):
        by_id[t["task_id"]] = t

    for s in subjects:
        res = CM.generate_deepening_tasks(graph, s, domain, threshold)
        for t in res["tasks"]:
            t["kind"] = "deepening"
            put(t)
        for (a, b) in KO.find_contradiction_candidates(graph, s, domain):
            put({"task_id": KO.task_id("contradiction", a, b), "type": "contradiction",
                 "kind": "operation", "subject": s, "domain": domain, "nodes": [a, b],
                 "reason": "Tension possible garantie/exclusion à arbitrer (candidat, non affirmé).",
                 "priority": 4, "origin_agent": "knowledge-ops"})

    for (keep, dup) in KO.find_duplicates(graph, domain):
        put({"task_id": KO.task_id("dedup", keep, dup), "type": "dedup", "kind": "operation",
             "domain": domain, "nodes": [keep, dup],
             "reason": "Entités quasi-identiques : fusion/supersession à confirmer.",
             "priority": 2, "origin_agent": "knowledge-ops"})

    for nid in KO.find_stale(graph):
        put({"task_id": KO.task_id("refresh", nid), "type": "rafraichir", "kind": "operation",
             "domain": domain, "nodes": [nid],
             "reason": "Connaissance périmée (TTL dépassé) : revérifier la source.",
             "priority": 3, "origin_agent": "knowledge-ops"})

    return list(by_id.values())


def persist(tasks, load_json, write_json, now, base_path=BACKLOG, dry_run=False):
    """Fusionne dans le backlog persistant (dédup par task_id, conserve first_seen). Ne touche à rien
    d'autre. Retourne (total, nouveaux)."""
    cur = None
    try:
        cur = load_json(base_path, default=None)
    except Exception:
        cur = None
    cur = cur or {"version": "1.0.0", "tasks": []}
    by_id = {t["task_id"]: t for t in cur.get("tasks", [])}
    new = 0
    for t in tasks:
        prev = by_id.get(t["task_id"])
        if prev is None:
            new += 1
        t["first_seen"] = (prev or {}).get("first_seen") or now()
        t["updated_at"] = now()
        by_id[t["task_id"]] = t
    cur["tasks"] = list(by_id.values())
    cur["updated_at"] = now()
    if not dry_run:
        write_json(base_path, cur)
    return len(cur["tasks"]), new


def summary(tasks):
    by_type, by_kind = {}, {}
    for t in tasks:
        by_type[t["type"]] = by_type.get(t["type"], 0) + 1
        by_kind[t.get("kind", "?")] = by_kind.get(t.get("kind", "?"), 0) + 1
    return {"total": len(tasks), "by_type": by_type, "by_kind": by_kind}
