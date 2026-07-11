#!/usr/bin/env python3
"""Revue HIÉRARCHISÉE de la connaissance — réduit le volume réellement ambigu soumis à l'humain.

Quatre niveaux :
  N1 (déterministe) : schéma, citation/page, doublon, catégorie, source, périmètre.
  N2 (déterministe) : cohérence logique, rattachement au bon contrat/concept, plausibilité, contradiction.
  N3 (second modèle) : uniquement sur les éléments SENSIBLES (exclusions, montants, plafonds, conditions,
                       contradictions) — hook, exécuté par un LLM plus fort si disponible.
  N4 (humain)       : seulement lorsque nécessaire.

Objectif : ne PAS supprimer la revue humaine, mais ne lui présenter que ce qui compte (erreurs possibles,
exclusions, montants, conditions sensibles, contradictions, faible confiance, forte conséquence).
Déterministe, 0 token.
"""
import re
import knowledge_graph as KG

SENSITIVE_SUBTYPES = {"exclusion", "plafond", "franchise", "condition", "fiscalite", "cotisation",
                      "delai", "point_vigilance", "formule"}
_MONTANT = re.compile(r"(\d[\d\s.,]*\s?(?:€|eur|euros|%|pourcent))", re.I)
LOW_CONF = 0.5


def _text_of(node):
    c = node.get("content") or {}
    return " ".join(str(c.get(k) or "") for k in ("resume", "texte", "citation", "diff")) + " " + str(node.get("label") or "")


def is_sensitive(node):
    if node.get("subtype") in SENSITIVE_SUBTYPES:
        return True
    return bool(_MONTANT.search(_text_of(node)))


def assess_node(graph, node):
    """Évalue un nœud L2 : niveaux franchis + escalade (auto / model / human). Déterministe."""
    reasons = []
    # N1 — structure
    n1 = True
    if node.get("layer") == 2 and not node.get("subject"):
        n1 = False; reasons.append("N1: sans sujet")
    if node.get("layer") == 2 and float(node.get("confidence", 0)) > 0 and not node.get("sources"):
        reasons.append("N1: entité sans preuve (dérivée)")   # non bloquant mais signalé
    # N2 — sémantique
    n2 = True
    if not node.get("subtype"):
        n2 = False; reasons.append("N2: catégorie absente")
    sensitive = is_sensitive(node)
    low_conf = float(node.get("confidence", 1.0)) < LOW_CONF or bool(node.get("ambiguities"))
    contradiction = _in_contradiction(graph, node["id"])

    if not (n1 and n2):
        escalate, priority = "human", 4
        reasons.append("structure/sémantique à corriger")
    elif contradiction:
        escalate, priority = "human", 5
        reasons.append("contradiction à arbitrer")
    elif sensitive and low_conf:
        escalate, priority = "human", 5
        reasons.append("élément sensible ET faible confiance")
    elif sensitive:
        escalate, priority = "model", 3
        reasons.append("élément sensible (exclusion/montant/plafond/condition)")
    elif low_conf:
        escalate, priority = "model", 2
        reasons.append("faible confiance / ambiguïté")
    else:
        escalate, priority = "auto", 0
    return {"id": node["id"], "kind": "node", "subtype": node.get("subtype"), "label": node.get("label"),
            "subject": node.get("subject"), "sensitive": sensitive, "low_conf": low_conf,
            "contradiction": contradiction, "escalate": escalate, "priority": priority, "reasons": reasons}


def _in_contradiction(graph, nid):
    for e in graph.data["edges"].values():
        if e.get("status") == "active" and e.get("type") == "contradicts" and nid in (e.get("src"), e.get("dst")):
            return True
    return False


def review_graph(graph, domain=None, limit=200):
    """Revue de tous les nœuds L2 actifs. Retourne la file priorisée (hors 'auto') + statistiques de
    réduction de la revue humaine."""
    items = [assess_node(graph, n) for n in graph.nodes(layer=2, domain=domain)]
    counts = {"auto": 0, "model": 0, "human": 0}
    for it in items:
        counts[it["escalate"]] = counts.get(it["escalate"], 0) + 1
    total = len(items) or 1
    queue = sorted((it for it in items if it["escalate"] != "auto"),
                   key=lambda x: (-x["priority"], x.get("subject") or ""))[:limit]
    return {
        "total": len(items), "auto": counts["auto"], "second_model": counts["model"], "human": counts["human"],
        "auto_ratio": round(counts["auto"] / total, 3),
        "human_ratio": round(counts["human"] / total, 3),
        "queue": queue,
    }
