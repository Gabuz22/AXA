#!/usr/bin/env python3
"""Migration one-shot IDEMPOTENTE — réactive les tâches 'completed' brûlées.

Contexte : un ancien bug marquait une exécution 'no_work' (aucun appel LLM utile, aucune proposition)
comme 'completed' sur la seule base d'un exit code 0. Ces tâches, définitivement 'completed', étaient
exclues du scheduler (ready_tasks) et bloquées par la déduplication. Cette migration réactive
UNIQUEMENT ces tâches brûlées (completed sans proposition VALIDE liée, sans completion_reason
='analyzed_no_data') et ne rouvre JAMAIS une tâche réellement terminée. Rejouable sans effet.

Usage :
    python migrate_unstick_tasks.py            # applique et écrit la file
    python migrate_unstick_tasks.py --dry-run  # montre l'effet, n'écrit rien
"""
import os, sys, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import safety_checks as S
import orch

ORCH_DIR = os.path.join(S.AGENT_WORK, "orchestrator")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="n'écrit pas la file ; montre seulement l'effet")
    ap.add_argument("--base-dir", default=ORCH_DIR)
    args = ap.parse_args()

    queue = orch.TaskQueue(args.base_dir)
    before = queue.counts()
    idx = orch._valid_extraction_index()
    print("=== AVANT ===")
    print("statuts :", json.dumps(before, ensure_ascii=False))
    print("propositions d'extraction VALIDES (index (contrat, catégorie)) :", len(idx))

    reopened = orch.unstick_burned_tasks(queue)

    print("=== RÉACTIVÉES (%d) ===" % len(reopened))
    for tid in reopened:
        t = queue._by_id(tid)
        print("  %s  contrat=%s  catégorie=%s  -> %s" % (tid, t.get("contract"), t.get("category"), t.get("status")))
    print("=== APRÈS ===")
    print("statuts :", json.dumps(queue.counts(), ensure_ascii=False))

    if args.dry_run:
        print("(dry-run : file NON écrite)")
        return 0
    queue.save()
    print("file écrite : %s" % queue.path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
