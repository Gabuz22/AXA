#!/usr/bin/env python3
"""Restaure depuis la branche de propositions UNIQUEMENT l'état persistant produit par les agents.

CONTRAINTE (bug corrigé) : le CODE, la CONFIG et les SCHÉMAS doivent TOUJOURS venir de `main`. Restaurer
tout `agent-work/` depuis `agents/proposals` réexécutait l'ancienne version des agents. Ici on n'accepte
qu'une **allowlist** de chemins d'ÉTAT, puis on force le code depuis main (défense en profondeur).

Refs configurables (pour les tests) :
- MAIN_REF          (défaut : origin/main)
- AGENT_BRANCH_REF  (défaut : origin/$AGENT_BRANCH, AGENT_BRANCH défaut agents/proposals)
"""
import os, sys, subprocess

# État persistant PRODUIT par les agents (à réintégrer depuis la branche s'il existe).
PERSISTENT = [
    "agent-work/extraction/pending", "agent-work/extraction/reviewed", "agent-work/extraction/rejected",
    "agent-work/extraction/memory.json", "agent-work/extraction/production_history.json", "agent-work/extraction/learning.json",
    "agent-work/official-sources/pending", "agent-work/official-sources/reviewed", "agent-work/official-sources/rejected",
    "agent-work/official-sources/changes", "agent-work/official-sources/snapshots",
    "agent-work/concepts/pending", "agent-work/concepts/reviewed", "agent-work/concepts/rejected",
    # NB : agent-work/tests/ = SORTIES de l'agent adversarial (propositions + métriques), donc de l'ÉTAT.
    # Le CODE des tests unitaires est dans agent-work/scripts/tests/ (couvert par CODE_FROM_MAIN, jamais restauré).
    "agent-work/tests/pending", "agent-work/tests/reviewed", "agent-work/tests/rejected",
    "agent-work/tests/metrics_history.json", "agent-work/tests/last_metrics.json",
    "agent-work/ux-ai/pending", "agent-work/ux-ai/reviewed", "agent-work/ux-ai/rejected",
    # corpus-explorer : carte de couverture persistante + backlog de tâches typées + propositions.
    "agent-work/exploration/coverage_map.json", "agent-work/exploration/tasks.json",
    "agent-work/corpus-explorer/pending", "agent-work/corpus-explorer/reviewed", "agent-work/corpus-explorer/rejected",
    # plateforme de connaissances : le graphe unifié (source de vérité, alimenté par ingestion déterministe).
    "agent-work/knowledge/graph.json",
    "agent-work/quality/reports", "agent-work/quality/incidents",
    "agent-work/coordinator", "agent-work/runs/manifests",
    "agent-work/runs/provider_metrics.json", "agent-work/runs/provider_scores.json", "agent-work/runs/benchmark.json",
    "agent-work/orchestrator/task_queue.json", "agent-work/orchestrator/provider_state.json",
    "agent-work/orchestrator/cycle_summary.json", "agent-work/orchestrator/cycles",
    "agent-work/orchestrator/idempotency.json", "agent-work/orchestrator/model_discovery.json",
    "agent-work/backlog/completed.json", "agent-work/backlog/blocked.json",
]
# CODE / DÉFINITIONS : jamais restaurés depuis la branche ; forcés depuis main.
CODE_FROM_MAIN = ["agent-work/scripts", "agent-work/config", "agent-work/schemas", "agent-work/README.md"]


def _run(args):
    return subprocess.run(["git"] + args, capture_output=True, text=True)


def _exists(ref, path):
    return _run(["cat-file", "-e", "%s:%s" % (ref, path)]).returncode == 0


def restore(main_ref, branch_ref):
    restored, skipped = [], []
    if _run(["rev-parse", "--verify", branch_ref]).returncode != 0:
        print("[restore] branche '%s' absente : aucun état à restaurer." % branch_ref)
    else:
        for p in PERSISTENT:
            if _exists(branch_ref, p) and _run(["checkout", branch_ref, "--", p]).returncode == 0:
                restored.append(p)
            else:
                skipped.append(p)
    # Défense en profondeur : le code exécuté vient TOUJOURS de main.
    for p in CODE_FROM_MAIN:
        if _exists(main_ref, p):
            _run(["checkout", main_ref, "--", p])
    print("[restore] état persistant réintégré (%d) : %s" % (len(restored), ", ".join(restored) or "(rien)"))
    print("[restore] code/config/schemas/README forcés depuis %s (jamais depuis la branche)." % main_ref)
    return restored


def main():
    main_ref = os.environ.get("MAIN_REF", "origin/main")
    branch_ref = os.environ.get("AGENT_BRANCH_REF") or ("origin/" + os.environ.get("AGENT_BRANCH", "agents/proposals"))
    restore(main_ref, branch_ref)
    return 0


if __name__ == "__main__":
    sys.exit(main())
