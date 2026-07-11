#!/usr/bin/env python3
"""Raisonnement MULTI-CONTRATS — comparaison structurelle par mécanisme, déterministe, 0 token.

Compare les contrats selon des mécanismes RÉELS (garanties, définitions, déclencheurs, conditions,
exclusions, plafonds…) et non de simples mots-clés, puis CLASSE prudemment chaque paire :
substituables / complémentaires / partiellement comparables / non comparables / doublon. Détecte aussi
les trous de couverture. Conserve les PREUVES propres à chaque contrat (jamais de mélange).

Échoue proprement lorsque les contrats ne sont pas réellement comparables (aucun mécanisme partagé).
Une différence de vocabulaire n'est pas une différence contractuelle.
"""
import re
import knowledge_graph as KG

STRUCTURANTES = {"garantie", "exclusion", "condition", "declencheur", "plafond", "definition"}
SECONDAIRES = {"option", "formalite", "point_vigilance", "formule", "delai"}


def _words(t):
    return {w for w in re.findall(r"[a-z0-9]+", KG._norm(t)) if len(w) > 3}


def _cat_words(graph, subject, domain, subtype):
    ws = set()
    for n in graph.nodes(layer=2, subject=subject, domain=domain):
        if n.get("subtype") == subtype:
            ws |= _words(n.get("label"))
            for k in (n.get("content", {}) or {}).get("keywords", []) or []:
                ws |= _words(k)
    return ws


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    return round(len(a & b) / len(a | b), 3)


def _subtypes(graph, subject, domain):
    return {n.get("subtype") for n in graph.nodes(layer=2, subject=subject, domain=domain)}


def classify_pair(graph, a, b, domain):
    """Classe la relation entre deux contrats d'après les mécanismes partagés. Prudent, avec preuves."""
    sa, sb = _subtypes(graph, a, domain), _subtypes(graph, b, domain)
    shared = (sa & sb)
    if not shared:
        return {"a": a, "b": b, "relation": "non_comparables", "shared_mechanisms": [],
                "note": "aucun mécanisme partagé"}
    gar = _jaccard(_cat_words(graph, a, domain, "garantie"), _cat_words(graph, b, domain, "garantie"))
    struct_shared = sorted(shared & STRUCTURANTES)
    if gar >= 0.6:
        rel = "doublon_probable" if gar >= 0.8 else "substituables"
    elif struct_shared and gar >= 0.15:
        rel = "partiellement_comparables"
    elif struct_shared:
        rel = "complementaires"
    else:
        rel = "peu_comparables"
    return {"a": a, "b": b, "relation": rel, "recouvrement_garanties": gar,
            "mecanismes_structurants_partages": struct_shared,
            "mecanismes_secondaires_partages": sorted(shared & SECONDAIRES),
            "validation_required": rel in ("doublon_probable", "substituables"),
            "note": "classement déterministe (recoupement de mécanismes) — une différence de vocabulaire n'est pas une différence contractuelle ; à confirmer"}


def coverage_gaps(graph, subjects, domain, categories):
    """Catégories (mécanismes) couvertes par CERTAINS contrats mais absentes d'autres = candidats de trou."""
    gaps = []
    for cat in categories:
        present = [s for s in subjects if any(n.get("subtype") == cat
                                              for n in graph.nodes(layer=2, subject=s, domain=domain))]
        absent = [s for s in subjects if s not in present]
        if present and absent:
            gaps.append({"mecanisme": cat, "present": present, "absent": absent,
                         "structurant": cat in STRUCTURANTES,
                         "nature": "trou_potentiel" if cat in STRUCTURANTES else "difference_secondaire"})
    return gaps


def compare(graph, subjects, domain="axa-contrat", categories=None):
    pairs = []
    for i in range(len(subjects)):
        for j in range(i + 1, len(subjects)):
            pairs.append(classify_pair(graph, subjects[i], subjects[j], domain))
    return {
        "subjects": list(subjects),
        "pairs": pairs,
        "coverage_gaps": coverage_gaps(graph, subjects, domain, categories or list(STRUCTURANTES)),
        "avertissement": "Comparaison structurelle prudente. Preuves conservées par contrat (jamais mélangées). Toute paire 'substituables/doublon' reste à confirmer.",
    }
