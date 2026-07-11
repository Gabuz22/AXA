#!/usr/bin/env python3
"""Statuts de VALIDATION de la connaissance — dérivés DÉTERMINISTIQUEMENT de la provenance / fraîcheur /
confiance / statut du graphe. 0 token.

Objectif : une connaissance ne doit JAMAIS être exposée comme validée uniquement parce qu'elle existe dans
le graphe. Chaque nœud/arête reçoit un statut clair, et une politique dit ce qui est exposable comme
vérité vs seulement visible-si-étiqueté.
"""
STATUSES = ("validated", "pending_review", "rejected", "simulated_claude",
            "derived_deterministic", "stale", "contradictory", "uncertain")

# Provenances -> nature de la connaissance.
_VALIDATED = {"ingest-structured"}                 # issu des masters validés (humain)
_DERIVED = {"environment-ingest", "knowledge-curator", "ingest"}   # dérivation déterministe
_PENDING = {"extraction-llm", "knowledge-builder"} # LLM / propositions : revue requise
_SIMULATED = {"simulation_assistee_par_claude"}

# Statuts EXPOSABLES comme vérité (les autres : visibles seulement si clairement étiquetés).
EXPOSABLE_AS_TRUTH = {"validated", "derived_deterministic"}
NEVER_EXPOSE = {"rejected"}


def node_status(graph, node, now=None):
    if node.get("status") == "superseded":
        return "rejected"
    if node.get("status") == "contested":
        return "contradictory"
    prov = node.get("provenance_agent")
    if prov in _SIMULATED:
        return "simulated_claude"
    if not graph.is_fresh(node, now):
        return "stale"
    if prov in _PENDING:
        return "pending_review"
    if prov in _VALIDATED:
        return "validated"
    if prov in _DERIVED:
        return "derived_deterministic"
    if float(node.get("confidence", 0.0)) < 0.5 or node.get("ambiguities"):
        return "uncertain"
    return "derived_deterministic"


def edge_status(graph, edge, now=None):
    if edge.get("status") == "superseded":
        return "rejected"
    prov = edge.get("provenance_agent")
    if prov in _SIMULATED:
        return "simulated_claude"
    if edge.get("type") == "contradicts":
        return "contradictory"
    if prov in _SIMULATED or (edge.get("type") in ("explains",) and edge.get("validation_required") is False):
        pass
    if prov in _PENDING:
        return "pending_review"
    if not edge.get("validation_required", True):
        return "derived_deterministic"          # lien structurel déterministe (ex. explains)
    if prov in _DERIVED:
        return "derived_deterministic"           # ex. governed_by déterministe (recoupement de termes)
    return "pending_review"


def is_exposable_as_truth(status):
    return status in EXPOSABLE_AS_TRUTH


def partition(graph, subject, domain, now=None):
    """Répartit la connaissance d'un sujet en BLOCS étiquetés (jamais mélangés)."""
    ents = graph.nodes(layer=2, subject=subject, domain=domain)
    ent_ids = {e["id"] for e in ents}
    blocks = {"validated_knowledge": [], "derived_relations": [], "pending_interpretations": [],
              "simulated_claude": [], "uncertainties": [], "human_review_required": [],
              "stale": [], "contradictory": []}
    counts = {s: 0 for s in STATUSES}
    for n in ents:
        st = node_status(graph, n, now)
        counts[st] = counts.get(st, 0) + 1
        item = {"label": n.get("label"), "subtype": n.get("subtype"), "statut": st,
                "confidence": n.get("confidence")}
        if st == "validated":
            blocks["validated_knowledge"].append(item)
        elif st == "simulated_claude":
            blocks["simulated_claude"].append(item)
        elif st == "stale":
            blocks["stale"].append(item)
        elif st == "contradictory":
            blocks["contradictory"].append(item)
        elif st == "uncertain":
            blocks["uncertainties"].append(item)
        elif st == "pending_review":
            blocks["pending_interpretations"].append(item)
        # derived_deterministic entités = connaissance dérivée (rare pour L2)
    for edge in graph.data["edges"].values():
        if edge.get("status") != "active" or edge.get("type") == "explains":
            continue
        if edge.get("src") in ent_ids or edge.get("dst") in ent_ids:
            st = edge_status(graph, edge, now)
            counts[st] = counts.get(st, 0) + 1
            rel = {"type": edge.get("type"), "src": edge.get("src"), "dst": edge.get("dst"), "statut": st}
            if st == "derived_deterministic":
                blocks["derived_relations"].append(rel)
            elif st == "simulated_claude":
                blocks["simulated_claude"].append(rel)
            elif st == "pending_review":
                blocks["pending_interpretations"].append(rel)
    # tout ce qui n'est pas exposable-vérité et non vide -> revue humaine
    for key in ("pending_interpretations", "simulated_claude", "contradictory", "stale"):
        blocks["human_review_required"] += [x for x in blocks[key]]
    return {"blocks": blocks, "counts": {k: v for k, v in counts.items() if v},
            "legend": {"exposable_as_truth": sorted(EXPOSABLE_AS_TRUTH),
                       "visible_if_labeled_only": sorted(set(STATUSES) - EXPOSABLE_AS_TRUTH - NEVER_EXPOSE),
                       "never_exposed": sorted(NEVER_EXPOSE)}}
