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


def _mnorm(t):
    # normalisation de MATCHING : minuscules + SANS ACCENTS (« crédit » doit matcher « credit »).
    import corpus_intel as CI
    return CI.norm(t)


def _words(t):
    # tokenise sur les caractères alphanumériques (coupe apostrophes/ponctuation) ; mots significatifs.
    return {w for w in re.findall(r"[a-z0-9]+", _mnorm(t)) if len(w) > 3}


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


def match_risks(need_text, metier):
    """Risques de la matrice MÉTIER dont un mot-clé apparaît dans le besoin. Retourne [(risk_id, spec)].
    Beaucoup plus PRÉCIS que le recoupement lexical entité-par-entité (l'inspecteur raisonne par risque)."""
    if not metier:
        return []
    nw = _words(need_text)
    ntext = _mnorm(need_text)
    hits = []
    for rid, spec in (metier.get("risques") or {}).items():
        for kw in spec.get("mots_cles", []):
            kws = _words(kw)
            # TOUS les mots significatifs du mot-clé présents, OU la phrase entière en FRONTIÈRES DE MOTS
            # (évite « per » qui matcherait en sous-chaîne dans « anticiPER »). Insensible aux accents.
            phrase = re.search(r"(?<![a-z0-9])" + re.escape(_mnorm(kw)) + r"(?![a-z0-9])", ntext)
            if (kws and kws <= nw) or phrase:
                hits.append((rid, spec))
                break
    return hits


def _data_needed_for(graph, domain, subject):
    """Conditions/exclusions/déclencheurs d'un contrat = ce qu'il faudra VÉRIFIER pour juger un cas."""
    out = []
    for n in graph.nodes(layer=2, subject=subject, domain=domain):
        if n.get("subtype") in ("condition", "exclusion", "declencheur", "delai", "plafond"):
            out.append({"type": n.get("subtype"), "libelle": n.get("label"), "statut": "a_verifier"})
    return out[:12]


def decompose(case, graph, domain, subjects=None, metier=None):
    """Arborescence de décomposition. Ne conclut jamais : produit des candidats + données manquantes.
    Si `metier` (matrice risques→contrats, heuristique Claude étiquetée) est fourni, le matching passe
    par les RISQUES (précis) ; sinon repli sur le recoupement lexical (large)."""
    ok, errs = IC.validate_case(case)
    tree = {"case_id": case.get("case_id"), "case_valid": ok, "case_errors": errs}

    needs = ([{"besoin": b, "origine": "exprime"} for b in case.get("besoins_exprimes", [])] +
             [{"besoin": b, "origine": "deduit"} for b in case.get("besoins_deduits", [])])
    objectifs = list(case.get("objectifs", []))
    # Si aucun besoin explicite mais des objectifs, on les traite comme besoins (déduits).
    if not needs and objectifs:
        needs = [{"besoin": o, "origine": "deduit"} for o in objectifs]
    # ÉVÉNEMENTS DE VIE (raisonnement temporel de l'inspecteur) : chaque événement du cas déduit des
    # risques accrus (matrice métier) -> besoins DÉDUITS supplémentaires, jamais mélangés aux exprimés.
    ev_notes = []
    if metier:
        evs = (metier.get("evenements_vie") or {})
        already = {KG._norm(n["besoin"]) for n in needs}
        for ev in case.get("evenements", []):
            spec = evs.get(KG._norm(ev).replace(" ", "_")) or evs.get(ev)
            if not spec:
                continue
            ev_notes.append({"evenement": ev, "note": spec.get("note")})
            for rid in spec.get("risques", []):
                lib = (metier.get("risques", {}).get(rid) or {}).get("libelle", rid)
                if KG._norm(lib) not in already:
                    # le risque est CONNU (pas de re-matching lexical) : on le force sur la branche.
                    needs.append({"besoin": lib, "origine": "deduit", "via_evenement": ev, "risque_force": rid})
                    already.add(KG._norm(lib))

    branches = []
    contrats_globaux = set()
    for nd in needs:
        if nd.get("risque_force") and metier and nd["risque_force"] in (metier.get("risques") or {}):
            risks = [(nd["risque_force"], metier["risques"][nd["risque_force"]])]
        else:
            risks = match_risks(nd["besoin"], metier)
        questions = []
        if risks:
            # matching PAR RISQUE (matrice métier) : précis, avec questions d'inspecteur
            contracts = sorted({c for _rid, spec in risks for c in spec.get("contrats", [])})
            matches = {c: _match_contracts(graph, domain, nd["besoin"]).get(c, []) for c in contracts}
            questions = [q for _rid, spec in risks for q in spec.get("questions", [])]
            note = ("candidats par MATRICE DE RISQUES (heuristique métier %s — à confirmer) : %s"
                    % (metier.get("origin", "?"), ", ".join(rid for rid, _ in risks)))
        else:
            matches = _match_contracts(graph, domain, nd["besoin"])
            contracts = sorted(matches.keys())
            note = "candidats déterministes (recoupement de termes) — à confirmer par analyse"
        contrats_globaux |= set(contracts)
        data_needed = {s: _data_needed_for(graph, domain, s) for s in contracts}
        branches.append({
            "besoin": nd["besoin"], "origine": nd["origine"],
            "risques_identifies": [rid for rid, _ in risks],
            "contrats_possibles": contracts,
            "garanties_possibles": matches,
            "questions_a_poser": questions,
            "donnees_necessaires": data_needed,
            "note": note,
        })

    comp = IC.completeness(case)
    return {
        **tree,
        "objectifs": objectifs,
        "evenements_de_vie": ev_notes,
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
