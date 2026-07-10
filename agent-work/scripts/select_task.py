#!/usr/bin/env python3
"""Sélection d'UNE micro-tâche adaptée à l'agent planifié et au quota disponible.

Lecture seule : renvoie la tâche choisie (ou None). La mise à jour du backlog (attempts, statut)
est faite par l'orchestrateur après un run réussi, et jamais en dry-run.
"""
import os
import safety_checks as S

BACKLOG = os.path.join(S.AGENT_WORK, "backlog", "backlog.json")


def load_backlog():
    return S.load_json(BACKLOG, default={"version": "1.0.0", "tasks": []})


def select(agent_id, max_attempts=5):
    """Choisit la tâche 'todo' (ou 'blocked' sous le seuil de tentatives) de plus haute priorité
    pour cet agent. None si aucune."""
    bl = load_backlog()
    candidates = [t for t in bl.get("tasks", [])
                  if t.get("recommended_agent") == agent_id
                  and t.get("status") in ("todo", "in_progress")
                  and int(t.get("attempts", 0)) < max_attempts]
    if not candidates:
        return None
    candidates.sort(key=lambda t: (-int(t.get("priority", 0)), int(t.get("attempts", 0)), t.get("id", "")))
    return candidates[0]


def mark_attempt(agent_id, task_id, status, dry_run, blocked_reason=None):
    """Incrémente attempts et met à jour le statut d'une tâche (non exécuté en dry-run)."""
    if dry_run:
        return
    bl = load_backlog()
    for t in bl.get("tasks", []):
        if t.get("id") == task_id:
            t["attempts"] = int(t.get("attempts", 0)) + 1
            t["last_attempt"] = S.now_iso()
            if status:
                t["status"] = status
            if blocked_reason:
                t["blocked_reason"] = blocked_reason
            break
    S.write_json(BACKLOG, bl)


if __name__ == "__main__":
    import sys
    aid = sys.argv[1] if len(sys.argv) > 1 else "quality"
    t = select(aid)
    print(t.get("id") if t else "AUCUNE_TACHE")
