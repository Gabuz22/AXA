#!/usr/bin/env python3
"""Décomposition du BESOIN à partir d'un cas client — déterministe, 0 token.

Produit une arborescence : cas → objectifs → risques → besoins → concepts → garanties possibles →
contrats possibles → données nécessaires → contraintes → arbitrages → solutions possibles. Les besoins
EXPRIMÉS et DÉDUITS restent séparés. Aucune éligibilité affirmée : uniquement des CANDIDATS à vérifier.

Générique : opère sur le graphe de connaissances (entités L2 = garanties/exclusions/… par sujet).
"""
import re
import knowledge_graph as KG
import inspector_case as IC

# Axes d'arbitrage standard (le moteur d'optimisation les explicitera).
ARBITRAGE_AXES = ("protection", "cout", "duree", "fiscalite", "liquidite", "flexibilite", "simplicite")


def _words(t):
    # tokenise sur les caractères alphanumériques (coupe apostrophes/ponctuation) ; mots significatifs.
    return {w for w in re.findall(r"[a-z0-9]+", KG._norm(t)) if len(w) > 3}


def _entity_terms(node):
    terms = _words(node.get("label"))
    for k in (node.get("content", {}) or {}).get("keywords", []) or []:
        terms |= _words(k)
    return terms


def _match_contracts(graph, domain, need_text):
    """Contrats (sujets) dont au moins une garantie recoupe le besoin. Retourne {sujet: [garanties]}."""
    nw = _words(need_text)
    if not nw:
        return {}
    hits = {}
    for n in graph.nodes(layer=2, domain=domain):
        if n.get("subtype") not in ("garantie", "option", "formule"):
            continue
        if nw & _entity_terms(n):
            hits.setdefault(n.get("subject"), []).append(n.get("label"))
    return hits


def _data_needed_for(graph, domain, subject):
    """Conditions/exclusions/déclencheurs d'un contrat = ce qu'il faudra VÉRIFIER pour juger un cas."""
    out = []
    for n in graph.nodes(layer=2, subject=subject, domain=domain):
        if n.get("subtype") in ("condition", "exclusion", "declencheur", "delai", "plafond"):
            out.append({"type": n.get("subtype"), "libelle": n.get("label"), "statut": "a_verifier"})
    return out[:12]


def decompose(case, graph, domain, subjects=None):
    """Arborescence de décomposition. Ne conclut jamais : produit des candidats + données manquantes."""
    ok, errs = IC.validate_case(case)
    tree = {"case_id": case.get("case_id"), "case_valid": ok, "case_errors": errs}

    needs = ([{"besoin": b, "origine": "exprime"} for b in case.get("besoins_exprimes", [])] +
             [{"besoin": b, "origine": "deduit"} for b in case.get("besoins_deduits", [])])
    objectifs = list(case.get("objectifs", []))
    # Si aucun besoin explicite mais des objectifs, on les traite comme besoins (déduits).
    if not needs and objectifs:
        needs = [{"besoin": o, "origine": "deduit"} for o in objectifs]

    branches = []
    contrats_globaux = set()
    for nd in needs:
        matches = _match_contracts(graph, domain, nd["besoin"])
        contrats_globaux |= set(matches.keys())
        data_needed = {}
        for s in matches:
            data_needed[s] = _data_needed_for(graph, domain, s)
        branches.append({
            "besoin": nd["besoin"], "origine": nd["origine"],
            "contrats_possibles": sorted(matches.keys()),
            "garanties_possibles": matches,
            "donnees_necessaires": data_needed,
            "note": "candidats déterministes (recoupement de termes) — à confirmer par analyse",
        })

    comp = IC.completeness(case)
    return {
        **tree,
        "objectifs": objectifs,
        "besoins": branches,
        "contrats_a_examiner": sorted(contrats_globaux),
        "contraintes": list(case.get("contraintes", [])),
        "faits": IC.facts(case),
        "hypotheses": IC.assumptions(case),
        "inconnues": IC.unknowns(case),
        "informations_manquantes": comp["missing"],
        "completude": comp["score"],
        "arbitrages_a_expliciter": list(ARBITRAGE_AXES),
        "avertissement": "Aucune éligibilité affirmée. Cas possiblement incomplet : toute conclusion reste conditionnelle et sujette à vérification humaine.",
    }
