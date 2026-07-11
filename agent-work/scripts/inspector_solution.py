#!/usr/bin/env python3
"""Construction de SOLUTIONS client + ARBITRAGE explicable — déterministe, 0 token.

À partir d'un cas décomposé, propose plusieurs scénarios (minimal / équilibré / renforcé / mono-contrat /
multi-contrats / conserver l'existant) et un arbitrage EXPLICABLE (pas de « meilleur » absolu : meilleur
POUR quel objectif, SOUS quelles hypothèses, à quel horizon, avec quels compromis).

Ne propose pas artificiellement plusieurs produits : une solution simple reste possible si elle est la
meilleure. N'invente JAMAIS un coût, une fiscalité ou un rendement absent des sources. Toute solution
distingue faits / hypothèses / inconnues et reste conditionnelle.
"""
import inspector_needs as INn
import inspector_case as IC

# Axes d'arbitrage (qualitatifs, dérivés du graphe ; jamais de chiffre inventé).
_AXES = ("couverture", "simplicite", "redondance")


def _needs_of(case):
    exp = [{"besoin": b, "origine": "exprime"} for b in case.get("besoins_exprimes", [])]
    ded = [{"besoin": b, "origine": "deduit"} for b in case.get("besoins_deduits", [])]
    if not (exp or ded):
        ded = [{"besoin": o, "origine": "deduit"} for o in case.get("objectifs", [])]
    return exp + ded


def _need_to_contracts(graph, domain, needs, metier=None):
    """{besoin: [contrats candidats]} + {contrat: set(besoins couverts)}. Matrice de risques (précise)
    quand `metier` est fourni ; recoupement lexical sinon."""
    by_need, by_contract = {}, {}
    for nd in needs:
        risks = INn.match_risks(nd["besoin"], metier)
        if risks:
            contracts = sorted({c for _rid, spec in risks for c in spec.get("contrats", [])})
        else:
            contracts = sorted(INn._match_contracts(graph, domain, nd["besoin"]).keys())
        by_need[nd["besoin"]] = contracts
        for c in contracts:
            by_contract.setdefault(c, set()).add(nd["besoin"])
    return by_need, by_contract


def _scenario(name, contracts, by_contract, all_needs, case, note):
    covered = set()
    for c in contracts:
        covered |= by_contract.get(c, set())
    non_couverts = [n for n in all_needs if n not in covered]
    # doublons = besoins couverts par >1 contrat du scénario
    counts = {}
    for c in contracts:
        for n in by_contract.get(c, set()):
            counts[n] = counts.get(n, 0) + 1
    doublons = [n for n, k in counts.items() if k > 1]
    return {
        "nom": name, "contrats_envisages": sorted(contracts),
        "besoins_couverts": sorted(covered), "besoins_non_couverts": non_couverts,
        "doublons": doublons, "nb_contrats": len(contracts),
        "avantages": _advantages(name, contracts, non_couverts, doublons),
        "inconvenients": _drawbacks(name, contracts, non_couverts, doublons),
        "donnees_manquantes": IC.completeness(case)["missing"] + case.get("inconnues", []),
        "hypotheses": IC.assumptions(case),
        "validation_requise": True,
        "note": note,
    }


def _advantages(name, contracts, non_couverts, doublons):
    adv = []
    if len(contracts) <= 1:
        adv.append("simplicité (un seul contrat à gérer)")
    if not non_couverts:
        adv.append("couvre l'ensemble des besoins identifiés")
    if not doublons:
        adv.append("pas de redondance")
    return adv or ["à évaluer"]


def _drawbacks(name, contracts, non_couverts, doublons):
    dr = []
    if non_couverts:
        dr.append("besoins non couverts : %s" % ", ".join(non_couverts))
    if doublons:
        dr.append("redondance possible : %s" % ", ".join(doublons))
    if len(contracts) > 2:
        dr.append("complexité de gestion (%d contrats)" % len(contracts))
    return dr or ["à évaluer"]


def build_scenarios(case, graph, domain="axa-contrat", metier=None):
    needs_struct = _needs_of(case)
    all_needs = [n["besoin"] for n in needs_struct]
    by_need, by_contract = _need_to_contracts(graph, domain, needs_struct, metier)
    ranked = sorted(by_contract.items(), key=lambda kv: -len(kv[1]))   # contrats par nb de besoins couverts

    scenarios = []
    if ranked:
        best_single = [ranked[0][0]]
        scenarios.append(_scenario("mono-contrat (couverture max)", best_single, by_contract, all_needs, case,
                                   "un seul contrat, le plus couvrant"))
        # multi-contrats glouton : ajouter des contrats jusqu'à couvrir tous les besoins
        chosen, covered = [], set()
        for c, ns in ranked:
            if not (ns - covered):
                continue
            chosen.append(c); covered |= ns
            if covered >= set(all_needs):
                break
        if len(chosen) > 1:
            scenarios.append(_scenario("multi-contrats (couverture complète)", chosen, by_contract, all_needs, case,
                                       "combinaison minimale couvrant tous les besoins identifiés"))
        scenarios.append(_scenario("renforcé (tous les candidats)", list(by_contract.keys()), by_contract, all_needs, case,
                                   "couverture maximale au prix de la complexité/redondance"))
    if case.get("contrats_existants"):
        scenarios.append(_scenario("conserver l'existant", list(case["contrats_existants"]), by_contract, all_needs, case,
                                   "réutilise les contrats déjà détenus (à vérifier)"))
    if not scenarios:
        scenarios.append({"nom": "aucune_solution", "contrats_envisages": [], "besoins_non_couverts": all_needs,
                          "note": "aucun contrat candidat identifié pour ces besoins — vérification/documentation requise",
                          "validation_requise": True})
    return {"case_id": case.get("case_id"), "besoins": all_needs, "besoins_par_contrat_candidat": {k: sorted(v) for k, v in by_contract.items()},
            "scenarios": scenarios,
            "avertissement": "Scénarios déterministes conditionnels. Aucun coût/fiscalité/rendement inventé. Distinction faits/hypothèses/inconnues conservée. Validation humaine requise."}


def arbitrate(scenarios, objectives=None):
    """Arbitrage EXPLICABLE : pour chaque axe, quel scénario est le meilleur ET sous quelles réserves.
    Jamais de « meilleur » absolu."""
    scen = [s for s in scenarios if s.get("nom") != "aucune_solution"]
    if not scen:
        return {"note": "aucun scénario à arbitrer", "recommandation_provisoire": None}
    def cov(s): return len(s.get("besoins_couverts", []))
    def simpl(s): return -s.get("nb_contrats", 99)
    def redund(s): return -len(s.get("doublons", []))
    best = {
        "couverture": max(scen, key=cov)["nom"],
        "simplicite": max(scen, key=simpl)["nom"],
        "faible_redondance": max(scen, key=redund)["nom"],
    }
    return {
        "meilleur_par_axe": best,
        "explication": [
            "« meilleur » dépend de l'objectif : couverture maximale ≠ simplicité ≠ absence de redondance.",
            "Aucun scénario n'est optimal sur tous les axes ; le choix dépend des priorités du client.",
        ],
        "compromis": "Plus de contrats -> meilleure couverture mais plus de complexité/redondance et de coût (non chiffré ici).",
        "recommandation_provisoire": ("Si priorité = simplicité : %s. Si priorité = couverture : %s. "
                                      "Choix à confirmer avec le client et à vérifier sur pièces."
                                      % (best["simplicite"], best["couverture"])),
        "objectifs_pris_en_compte": list(objectives or []),
        "validation_humaine_requise": True,
    }
