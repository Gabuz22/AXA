#!/usr/bin/env python3
"""Agent inspector-evaluator — DÉTERMINISTE, 0 token. Évaluation FONCTIONNELLE de Gabriel AXA « Inspecteur ».

Choisit des tests du banc, les exécute via les moteurs déterministes, évalue les réponses par des
contrôles déterministes (aucune invention, pas de mélange, données manquantes signalées, prudence,
« je ne sais pas »), suit les scores et alimente le backlog en tâches correctives. Ne modifie JAMAIS la
connaissance ; il mesure et crée du travail.
"""
import safety_checks as S
from agents import base
import knowledge_graph as KG
import inspector_bench as IB

GRAPH = "agent-work/knowledge/graph.json"
RESULTS = "agent-work/knowledge/inspector/bench_results.json"
DOMAIN = "axa-contrat"


def run(ctx):
    ctx.self_wrote = True
    graph = KG.KnowledgeGraph(base.repo_path(GRAPH), load_json=S.load_json)
    subjects = sorted({n.get("subject") for n in graph.nodes(layer=2, domain=DOMAIN) if n.get("subject")})
    if not subjects:
        ctx.summary = {"Banc Inspecteur": "graphe vide (lancer knowledge-curator d'abord)"}
        return [], ["inspector-evaluator: graphe vide"]
    rep = IB.run_bench(graph, DOMAIN, subjects)
    if not ctx.dry_run:
        S.write_json(base.repo_path(RESULTS), {"version": "1.0.0", "generated_at": S.now_iso(),
                                               "domain": DOMAIN, **rep})
    ctx.summary = {
        "Tests exécutés": rep["n_tests"],
        "Score global": "%.2f" % rep["score_global"],
        "Score par famille": ", ".join("%s:%.2f" % (k, v) for k, v in rep["score_par_famille"].items()),
        "Tâches correctives": len(rep["taches_correctives"]),
    }
    return [], ["inspector-evaluator: banc %d tests, score global %.2f, %d tâche(s) corrective(s)"
                % (rep["n_tests"], rep["score_global"], len(rep["taches_correctives"]))]
