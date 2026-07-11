#!/usr/bin/env python3
"""Comparaison inter-contrats & détection prudente de contradictions — déterministe, 0 token.

Compare les contrats par catégorie (garanties, exclusions, définitions, plafonds…) et SIGNALE des
candidats de tension. Distinction essentielle : une DIFFÉRENCE n'est pas une CONTRADICTION. Le module
classe prudemment (différence normale / couverture asymétrique / candidat de contradiction) et n'AFFIRME
jamais : les vraies contradictions relèvent d'une vérification (LLM/humain).
"""
import knowledge_graph as KG

_NEG = ("exclu", "sauf", "ne sont pas", "aucune", "hors", "ne couvre pas", "non garanti", "sans", "ne peut")


def _cat_entities(graph, subject, domain, cat):
    cn = KG._norm(cat)
    return [n for n in graph.nodes(layer=2, subject=subject, domain=domain)
            if cn and (cn in KG._norm(n.get("subtype")) or KG._norm(n.get("subtype")) in cn)]


def compare_contracts(graph, subjects, domain, categories):
    """Matrice catégorie × contrat (libellés) + différences de COUVERTURE (présent ici / absent là)."""
    matrix, diffs = {}, []
    for cat in categories:
        row = {s: [n.get("label") for n in _cat_entities(graph, s, domain, cat)] for s in subjects}
        matrix[cat] = row
        have = [s for s, v in row.items() if v]
        miss = [s for s, v in row.items() if not v]
        if have and miss:
            diffs.append({"category": cat, "kind": "couverture_asymetrique",
                          "present": have, "absent": miss,
                          "note": "différence de couverture documentaire, PAS une contradiction"})
    return {"matrix": matrix, "differences": diffs}


def _words(t):
    return {w for w in KG._norm(t).split() if len(w) > 3}


def classify_tension(label_a, subtype_a, label_b, subtype_b):
    """Classe prudemment une paire d'éléments d'un même sujet. Retourne un label de NATURE, jamais une
    affirmation de contradiction."""
    a_neg = any(n in KG._norm(label_a) for n in _NEG)
    b_neg = any(n in KG._norm(label_b) for n in _NEG)
    overlap = len(_words(label_a) & _words(label_b))
    if {subtype_a, subtype_b} == {"garantie", "exclusion"} and (a_neg or b_neg) and overlap >= 2:
        return "candidat_contradiction"          # garantit X mais exclut X -> à vérifier
    if subtype_a == subtype_b and overlap >= 3:
        return "variante_ou_doublon"             # même catégorie, très proche -> variante ou doublon
    return "difference_normale"


def contradiction_candidates(graph, subject, domain=None):
    """Candidats de tension INTERNES à un sujet (jamais affirmés). Réutilise la logique prudente."""
    ents = graph.nodes(layer=2, subject=subject, domain=domain)
    out = []
    for i in range(len(ents)):
        for j in range(i + 1, len(ents)):
            a, b = ents[i], ents[j]
            nature = classify_tension(a.get("label"), a.get("subtype"), b.get("label"), b.get("subtype"))
            if nature == "candidat_contradiction":
                out.append({"a": a["id"], "b": b["id"], "label_a": a.get("label"), "label_b": b.get("label"),
                            "nature": nature, "validation_required": True})
    return out


def build_report(graph, subjects, domain, categories):
    return {
        "comparison": compare_contracts(graph, subjects, domain, categories),
        "contradiction_candidates": {s: contradiction_candidates(graph, s, domain) for s in subjects},
        "note": "différences de couverture ≠ contradictions ; tout candidat reste à vérifier (LLM/humain).",
    }
