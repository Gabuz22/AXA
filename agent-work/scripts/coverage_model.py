#!/usr/bin/env python3
"""Couverture MULTI-DIMENSIONNELLE d'un sujet, calculée DÉTERMINISTIQUEMENT sur le graphe de connaissances.

On ne mesure plus « nombre de pages lues » mais la PROFONDEUR de compréhension, selon plusieurs axes. Une
entité extraite (L2) mais sans relation (L3) ni explication (L4) est « connue mais superficielle » → elle
génère du travail d'APPROFONDISSEMENT, même si aucune phrase nouvelle n'est à extraire. C'est le passage
d'« extraire » à « comprendre ».

100 % générique (aucun domaine) : opère sur knowledge_graph. Déterministe → aucun token consommé pour
mesurer la couverture ni décider quoi approfondir ; l'LLM n'est appelé qu'ensuite, sur les axes faibles.
"""
import hashlib
import knowledge_graph as KG

# Axes de couverture. Poids = importance relative dans le score global (sommés à 1).
DIMENSIONS = ("evidence", "normalized", "relations", "understanding", "environment", "freshness")
WEIGHTS = {"evidence": 0.20, "normalized": 0.20, "relations": 0.20,
           "understanding": 0.20, "environment": 0.10, "freshness": 0.10}

# Type de tâche d'approfondissement produit quand un axe est faible.
_DIM_TASK = {
    "normalized": "normaliser",       # preuve présente mais pas d'entité canonique
    "relations": "relier",            # entité isolée -> chercher ses relations
    "understanding": "expliquer",     # entité sans synthèse L4
    "environment": "environnement",   # aucun ancrage réglementaire/fiscal externe
    "freshness": "rafraichir",        # information périmée (TTL dépassé)
    "evidence": "sourcer",            # rien de sourcé sur ce sujet
}


def coverage_vector(graph, subject, domain=None):
    """Retourne {axe: [0..1]} pour un sujet, calculé sur le graphe. Déterministe, sans LLM.

    evidence      : présence de preuve L1.
    normalized    : proportion de preuves converties en entités L2 (au moins une => amorcé).
    relations     : proportion d'entités L2 possédant au moins une relation L3.
    understanding : proportion d'entités L2 possédant une explication L4.
    environment   : présence d'au moins une relation transverse vers un autre domaine (governed_by…).
    freshness     : proportion de nœuds encore frais (TTL respecté).
    """
    ev = graph.nodes(layer=1, subject=subject, domain=domain)
    ents = graph.nodes(layer=2, subject=subject, domain=domain)
    n_ent = len(ents)

    v = {}
    v["evidence"] = 1.0 if ev else 0.0
    v["normalized"] = 1.0 if ents else (0.0 if ev else 0.0)
    if n_ent:
        related = sum(1 for e in ents if graph.edges_of(e["id"], direction="any"))
        explained = sum(1 for e in ents if graph.has_understanding(e["id"]))
        # environnement = PRÉSENCE d'au moins un ancrage transverse (clause -> réglementation/fiscalité),
        # pas un ratio par entité (toutes les entités n'ont pas vocation à un ancrage externe).
        has_cross = False
        for e in ents:
            for edge in graph.edges_of(e["id"], direction="any"):
                other = graph.get_node(edge["dst"] if edge["src"] == e["id"] else edge["src"])
                if other and other.get("domain") and e.get("domain") and other["domain"] != e["domain"]:
                    has_cross = True
                    break
            if has_cross:
                break
        v["relations"] = round(related / n_ent, 3)
        v["understanding"] = round(explained / n_ent, 3)
        v["environment"] = 1.0 if has_cross else 0.0
    else:
        v["relations"] = v["understanding"] = v["environment"] = 0.0
    allnodes = ev + ents
    v["freshness"] = round(sum(1 for n in allnodes if graph.is_fresh(n)) / len(allnodes), 3) if allnodes else 1.0
    return v


def depth_score(vector):
    """Score global de PROFONDEUR [0..1] (moyenne pondérée des axes)."""
    return round(sum(WEIGHTS[d] * float(vector.get(d, 0.0)) for d in DIMENSIONS), 3)


def weakest_dimensions(vector, threshold=0.6):
    """Axes sous le seuil, du plus faible au moins faible — ce qu'il faut approfondir en priorité."""
    weak = [(d, vector.get(d, 0.0)) for d in DIMENSIONS if vector.get(d, 0.0) < threshold]
    return [d for d, _ in sorted(weak, key=lambda x: x[1])]


def generate_deepening_tasks(graph, subject, domain=None, threshold=0.6, origin_agent="coverage-model"):
    """Tâches d'APPROFONDISSEMENT déterministes pour les axes faibles d'un sujet. Ids stables (dédup,
    idempotence). Ne relit rien : décide uniquement d'après l'état du graphe. Le fait qu'une entité soit
    « connue » n'empêche pas de générer relier/expliquer/comparer : c'est là qu'est la profondeur."""
    vec = coverage_vector(graph, subject, domain)
    tasks = []
    for dim in weakest_dimensions(vec, threshold):
        ttype = _DIM_TASK[dim]
        tid = "kd_" + hashlib.sha256(("%s|%s|%s" % (domain, subject, ttype)).encode("utf-8")).hexdigest()[:16]
        tasks.append({
            "task_id": tid, "type": ttype, "kind": "deepening", "subject": subject, "domain": domain,
            "dimension": dim, "current": vec.get(dim, 0.0), "target": threshold,
            "reason": "Axe '%s' faible (%.2f < %.2f) pour « %s » : approfondir (%s)."
                      % (dim, vec.get(dim, 0.0), threshold, subject, ttype),
            "priority": 4 if dim in ("normalized", "relations") else 3,
            "origin_agent": origin_agent,
        })
    return {"subject": subject, "domain": domain, "vector": vec,
            "depth_score": depth_score(vec), "tasks": tasks}
