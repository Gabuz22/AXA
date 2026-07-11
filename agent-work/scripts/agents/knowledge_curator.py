#!/usr/bin/env python3
"""Agent knowledge-curator — DÉTERMINISTE, zéro token, cœur autonome de la plateforme de connaissances.

À chaque exécution : (1) ingère le domaine dans le graphe (connaissance structurée + propositions des
agents producteurs), (2) calcule la couverture de PROFONDEUR de chaque sujet, (3) génère le backlog de
tâches déterministes (approfondissement + opérations). C'est ainsi que « le système découvre lui-même son
travail » sans consommer de tokens. Les exécuteurs (capacités LLM, phase 3+) puiseront dans ce backlog.

Ne modifie aucun agent, aucune proposition, aucun produit : lit des sources existantes, écrit uniquement
sous agent-work/knowledge/. Générique : pilote un DomainAdapter (AXA aujourd'hui, autres demain).
"""
import safety_checks as S
from agents import base
import domain_adapter
import knowledge_graph as KG
import knowledge_ingest as KI
import knowledge_tasks as KT
import environment_ingest as EI

AGENT_CODE_VERSION = "2.8.0"

GRAPH = "agent-work/knowledge/graph.json"
DOMAINS = ("axa-contrat",)                     # domaines curés (ajouter un adaptateur suffit à en couvrir un nouveau)


def _wj(ctx):
    def w(path, data, **kw):
        if not ctx.dry_run:
            S.write_json(path, data, **kw)
    return w


def run(ctx):
    ctx.self_wrote = True                       # gère son propre état (graphe + backlog) ; ne retourne pas de proposition
    write = _wj(ctx)
    totals = {"entities": 0, "evidence": 0, "subjects": 0, "tasks_total": 0, "tasks_new": 0}
    per_domain = {}
    for domain_id in DOMAINS:
        try:
            adapter = domain_adapter.get(domain_id)
        except Exception as e:
            return [], ["knowledge-curator: adaptateur %s indisponible: %s" % (domain_id, e)]
        graph = KG.KnowledgeGraph(base.repo_path(GRAPH), load_json=S.load_json, write_json=write)
        migrated = KG.migrate(graph)            # met à niveau les anciens nœuds/arêtes (idempotent)
        ing = KI.ingest(adapter, graph)         # déterministe, 0 token
        env = EI.ingest_environment(adapter, graph)   # ancrage réglementaire/fiscal (domaines séparés), 0 token/réseau
        subjects = ing.get("subjects", [])
        tasks = KT.generate(graph, domain_id, subjects)
        total, new = KT.persist(tasks, S.load_json, write, S.now_iso, dry_run=ctx.dry_run)
        depth = _avg_depth(graph, domain_id, subjects)
        per_domain[domain_id] = {"subjects": len(subjects), "tasks": total, "new": new,
                                 "graph": ing.get("graph", {}), "depth_moyenne": depth}
        totals["entities"] += ing.get("entities_structured", 0) + ing.get("entities_proposals", 0)
        totals["evidence"] += ing.get("evidence_structured", 0) + ing.get("evidence_proposals", 0)
        totals["subjects"] += len(subjects)
        totals["tasks_total"] = total
        totals["tasks_new"] += new

    st = KT.summary(tasks)
    graph_check = KG.validate_graph(graph)      # observabilité : le graphe respecte-t-il son contrat ?
    gs = graph.stats()                          # stats FINALES (après ingestion + environnement)
    ctx.summary = {
        "Domaines curés": len(DOMAINS),
        "Sujets": totals["subjects"],
        "Schema graphe OK": "oui" if graph_check["ok"] else "NON (%d noeuds/%d aretes)" % (
            graph_check["node_errors"], graph_check["edge_errors"]),
        "Migres (compat)": migrated,
        "Graphe (L1/L2/L3/L4)": "%d/%d/%d/%d" % (gs["evidence"], gs["normalized"],
                                                 gs["relations"], gs["understanding"]),
        "Profondeur moyenne": "%.2f" % per_domain[DOMAINS[0]]["depth_moyenne"],
        "Backlog de connaissance": totals["tasks_total"],
        "Nouvelles tâches": totals["tasks_new"],
        "Types de tâches": ", ".join("%s:%d" % (k, v) for k, v in sorted(st["by_type"].items())),
    }
    return [], ["knowledge-curator: %d sujet(s), %d tâche(s) au backlog (%d nouvelle(s)), 0 token"
                % (totals["subjects"], totals["tasks_total"], totals["tasks_new"])]


def _avg_depth(graph, domain, subjects):
    import coverage_model as CM
    if not subjects:
        return 0.0
    return round(sum(CM.depth_score(CM.coverage_vector(graph, s, domain)) for s in subjects) / len(subjects), 3)
