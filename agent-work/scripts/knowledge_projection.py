#!/usr/bin/env python3
"""Projection LECTURE SEULE du graphe vers une vue exploitable par des IA — déterministe, versionnée.

Génère, pour chaque sujet, une vue enrichie DÉRIVÉE du graphe (jamais l'inverse) : synthèse, connaissances
par catégorie, relations, environnement, compréhension, preuves, incertitudes, fraîcheur. Les COUCHES
restent séparées (preuve / normalisé / relation / interprétation / environnement) et chaque élément porte
sa provenance, sa confiance et `validation_required`.

Isolée du produit : écrit uniquement sous `agent-work/knowledge/projection/`. Ne modifie AUCUN master ni
la Vue IA. Reconstructible (fonction pure du graphe), versionnée (empreinte du graphe). 0 token.
"""
import hashlib
import knowledge_graph as KG
import coverage_model as CM

PROJECTION_DIR = "agent-work/knowledge/projection"
PROJECTION_VERSION = "1.0.0"


def _sources_of(graph, node):
    """Résout les preuves L1 rattachées à une entité (document, page, citation). Séparé du contenu."""
    out = []
    for s in node.get("sources", []):
        if s.get("evidence"):
            ev = graph.get_node(s["evidence"])
            if ev:
                c = ev.get("content", {})
                out.append({"document": c.get("document"), "page": c.get("page"),
                            "citation": c.get("citation")})
        elif s.get("document"):
            out.append({"document": s.get("document"), "page": s.get("page"), "citation": s.get("citation")})
    return out


def _label(graph, nid):
    n = graph.get_node(nid)
    return n.get("label") if n else nid


def project_subject(graph, subject, domain, expected=None):
    """Vue dérivée d'un sujet. Couches séparées, provenance conservée. Déterministe."""
    ents = graph.nodes(layer=2, subject=subject, domain=domain)
    by_cat = {}
    incertitudes = []
    for e in ents:
        item = {"label": e.get("label"), "resume": (e.get("content") or {}).get("resume"),
                "confidence": e.get("confidence"), "sources": _sources_of(graph, e),
                "validation_required": bool((e.get("content") or {}).get("validation_required", False)),
                "version": e.get("version", 1)}
        by_cat.setdefault(e.get("subtype") or "autre", []).append(item)
        if float(e.get("confidence", 1.0)) < 0.5 or e.get("ambiguities"):
            incertitudes.append({"label": e.get("label"), "confidence": e.get("confidence"),
                                 "ambiguities": e.get("ambiguities", [])})

    # L3 relations internes (entre entités du sujet)
    ent_ids = {e["id"] for e in ents}
    relations = []
    for edge in graph.data["edges"].values():
        if edge.get("status") != "active" or edge.get("type") == "explains":
            continue
        if edge.get("src") in ent_ids and edge.get("type") != "governed_by":
            if edge.get("dst") in ent_ids:
                relations.append({"type": edge["type"], "de": _label(graph, edge["src"]),
                                  "vers": _label(graph, edge["dst"]), "directed": edge.get("directed", True),
                                  "confidence": edge.get("confidence"),
                                  "validation_required": edge.get("validation_required", True)})

    # environnement (couche SÉPARÉE) : governed_by vers reglementation/fiscalite
    environnement = []
    for edge in graph.data["edges"].values():
        if edge.get("status") == "active" and edge.get("type") == "governed_by" and edge.get("src") in ent_ids:
            cn = graph.get_node(edge["dst"])
            if cn:
                environnement.append({"clause": _label(graph, edge["src"]), "concept": cn.get("label"),
                                      "domaine": cn.get("domain"), "fraicheur": cn.get("freshness"),
                                      "validation_required": edge.get("validation_required", True)})

    # L4 compréhension (interprétation, séparée du prouvé)
    comprehension = []
    for e in ents:
        for edge in graph.edges_of(e["id"], rtype="explains", direction="in"):
            u = graph.get_node(edge["src"])
            if u:
                comprehension.append({"element": e.get("label"), "aspect": (u.get("content") or {}).get("aspect"),
                                      "explication": (u.get("content") or {}).get("text"),
                                      "confidence": u.get("confidence"), "nature": "interpretation"})

    # preuves L1 (échantillon)
    preuves = [{"document": (n.get("content") or {}).get("document"),
                "page": (n.get("content") or {}).get("page"),
                "citation": (n.get("content") or {}).get("citation")}
               for n in graph.nodes(layer=1, subject=subject, domain=domain)]

    report = CM.explain(graph, subject, domain, expected)
    return {
        "projection_version": PROJECTION_VERSION, "subject": subject, "domain": domain,
        "synthese": {"depth_score": report["depth_score"], "semantic_coverage": report["semantic_coverage"],
                     "profondeur": report["depth"], "rates": report["rates"]},
        "connaissances": by_cat,                # L2, séparé par catégorie
        "relations": relations,                 # L3
        "environnement": environnement,         # domaine séparé
        "comprehension": comprehension,         # L4 (interprétation)
        "preuves": preuves,                     # L1
        "incertitudes": incertitudes,
        "fraicheur": {"axe": report["vector"].get("freshness")},
        "axes_faibles": report["weak_axes"],
    }


def graph_fingerprint(graph):
    keys = sorted(graph.data.get("nodes", {}).keys()) + sorted(graph.data.get("edges", {}).keys())
    return "p_" + hashlib.sha256("|".join(keys).encode("utf-8")).hexdigest()[:16]


def write_projections(graph, domain, subjects, adapter, write_json, now, base_dir=PROJECTION_DIR, dry_run=False):
    """Écrit une projection par sujet + un index. Isolé sous agent-work/knowledge/projection/. Retourne
    le nombre de projections écrites. Ne touche jamais au produit."""
    import os
    from agents import base
    if dry_run or write_json is None:
        return 0
    expected = adapter.expected_categories() if hasattr(adapter, "expected_categories") else []
    fp = graph_fingerprint(graph)
    index = {"projection_version": PROJECTION_VERSION, "domain": domain, "generated_at": now(),
             "graph_fingerprint": fp, "subjects": []}
    n = 0
    for s in subjects:
        proj = project_subject(graph, s, domain, expected)
        fname = KG.ascii_slug(s) or ("sujet_%d" % n)
        write_json(base.repo_path(os.path.join(base_dir, fname + ".json")), proj)
        index["subjects"].append({"subject": s, "file": fname + ".json",
                                  "depth_score": proj["synthese"]["depth_score"]})
        n += 1
    write_json(base.repo_path(os.path.join(base_dir, "index.json")), index)
    return n
