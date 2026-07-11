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
COVERAGE = "agent-work/knowledge/coverage.json"
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
        import claude_enrichment as CE
        CE.ingest_from_repo(graph, S.REPO_ROOT, domain_id)   # couche Claude étiquetée (jamais 'validée')
        subjects = ing.get("subjects", [])
        tasks = KT.generate(graph, domain_id, subjects)
        total, new = KT.persist(tasks, S.load_json, write, S.now_iso, dry_run=ctx.dry_run)
        _write_coverage_report(graph, domain_id, adapter, subjects, write, ctx.dry_run)
        import knowledge_projection as KP
        projected = KP.write_projections(graph, domain_id, subjects, adapter, write, S.now_iso, dry_run=ctx.dry_run)
        review = _write_review(graph, domain_id, write, ctx.dry_run)
        _write_comparisons(graph, domain_id, adapter, subjects, write, ctx.dry_run)
        _write_inspector(graph, domain_id, adapter, subjects, write, ctx.dry_run)
        _write_manager(domain_id, write, ctx.dry_run)
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
        "Projections IA écrites": projected,
        "Revue (auto/modele/humain)": "%d/%d/%d" % (review["auto"], review["second_model"], review["human"]),
        "Types de tâches": ", ".join("%s:%d" % (k, v) for k, v in sorted(st["by_type"].items())),
    }
    return [], ["knowledge-curator: %d sujet(s), %d tâche(s) au backlog (%d nouvelle(s)), 0 token"
                % (totals["subjects"], totals["tasks_total"], totals["tasks_new"])]


def _avg_depth(graph, domain, subjects):
    import coverage_model as CM
    if not subjects:
        return 0.0
    return round(sum(CM.depth_score(CM.coverage_vector(graph, s, domain)) for s in subjects) / len(subjects), 3)


REVIEW = "agent-work/knowledge/review.json"
MANAGER = "agent-work/knowledge/manager.json"


def _write_review(graph, domain, write, dry_run):
    """Revue hiérarchisée (déterministe) : ne présente à l'humain que le sensible/ambigu."""
    import knowledge_review as KR
    rep = KR.review_graph(graph, domain)
    if not dry_run and write is not None:
        write(base.repo_path(REVIEW), {"version": "1.0.0", "domain": domain, "generated_at": S.now_iso(), **rep})
    return rep


COMPARISONS = "agent-work/knowledge/comparisons.json"


def _write_text(path, text):
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _write_inspector(graph, domain, adapter, subjects, write, dry_run):
    """Projection Inspecteur (fiches + comparaison + matrices + outils + guide IA), isolée sous knowledge/inspector/."""
    import inspector_projection as IP
    wt = None if dry_run else _write_text
    return IP.write_inspector(graph, subjects, domain, adapter, write, wt, S.now_iso, dry_run=dry_run)


def _write_comparisons(graph, domain, adapter, subjects, write, dry_run):
    """Comparaison inter-contrats + candidats de contradiction (déterministe, prudent)."""
    import knowledge_compare as KC
    expected = adapter.expected_categories() if hasattr(adapter, "expected_categories") else []
    rep = KC.build_report(graph, subjects, domain, expected)
    if not dry_run and write is not None:
        write(base.repo_path(COMPARISONS), {"version": "1.0.0", "domain": domain, "generated_at": S.now_iso(), **rep})
    return rep


def _write_manager(domain, write, dry_run):
    """Recommandations stratégiques (déterministe) — ne modifie jamais la connaissance."""
    import knowledge_manager as KM
    rep = KM.analyze(S.load_json, base.repo_path, domain)
    rep["generated_at"] = S.now_iso()
    if not dry_run and write is not None:
        write(base.repo_path(MANAGER), rep)
    return rep


def _write_coverage_report(graph, domain, adapter, subjects, write, dry_run):
    """Rapport de couverture EXPLICABLE par sujet (observabilité + entrée du manager stratégique)."""
    if dry_run or write is None:
        return
    import coverage_model as CM
    expected = adapter.expected_categories() if hasattr(adapter, "expected_categories") else []
    reports = {s: CM.explain(graph, s, domain, expected) for s in subjects}
    write(base.repo_path(COVERAGE), {"version": "1.0.0", "domain": domain, "generated_at": S.now_iso(),
                                     "subjects": reports})
