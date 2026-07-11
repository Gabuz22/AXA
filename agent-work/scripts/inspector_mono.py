#!/usr/bin/env python3
"""Raisonnement MONO-CONTRAT — déterministe, 0 token.

Deux sorties :
  1) `reasoning_sheet(graph, subject)` : fiche structurée (finalité, architecture des garanties,
     déclencheurs, conditions, exclusions, limites, concepts structurants, environnement, confusions,
     situations favorables/défavorables, incertitudes, preuves). Assemblée depuis le graphe.
  2) `apply_case(graph, subject, case)` : confronte le contrat à un CAS client — éléments pertinents,
     clauses potentiellement pertinentes, conditions à vérifier, exclusions à vérifier, données
     manquantes, compatibilité, confiance, conclusion PROVISOIRE et conditionnelle.

Ne conclut jamais une éligibilité. Sépare prouvé / interprété / à vérifier. Les trous sémantiques
(finalité, confusions) qui exigent une compréhension L4 sont signalés « à approfondir (LLM) ».
"""
import knowledge_graph as KG
import coverage_model as CM
import inspector_case as IC
import inspector_needs as INn
import knowledge_status as KS

_PRINCIPAL = ("principal", "principale", "obligatoire", "socle")


def _by_subtype(graph, subject, domain):
    out = {}
    for n in graph.nodes(layer=2, subject=subject, domain=domain):
        out.setdefault(n.get("subtype") or "autre", []).append(n)
    return out


def _labels(nodes):
    return [n.get("label") for n in nodes]


def _understanding(graph, subject, domain):
    """Explications L4 disponibles (interprétation, séparée, ÉTIQUETÉE origine+statut). Vide => à approfondir."""
    txt = []
    ent_ids = {e["id"] for e in graph.nodes(layer=2, subject=subject, domain=domain)}
    for edge in graph.data["edges"].values():
        if edge.get("status") == "active" and edge.get("type") == "explains" and edge.get("dst") in ent_ids:
            u = graph.get_node(edge["src"])
            if u:
                txt.append({"element": _label_of(graph, edge["dst"]),
                            "aspect": (u.get("content") or {}).get("aspect"),
                            "explication": (u.get("content") or {}).get("text"),
                            "confidence": u.get("confidence"), "nature": "interpretation",
                            "origine": u.get("provenance_agent"),
                            "statut": KS.node_status(graph, u), "validation_required": True})
    return txt


def _aspect_of(understanding, subject, aspect):
    """Compréhension contrat-niveau (portée par l'ancre subtype='contrat', element == subject)."""
    for u in understanding:
        if KG._norm(u.get("element")) == KG._norm(subject) and u.get("aspect") == aspect:
            return {"texte": u["explication"], "nature": "interpretation", "origine": u.get("origine"),
                    "statut": u.get("statut"), "validation_required": True}
    return None


def _articulations(graph, subject, domain):
    """Relations L3 INTERNES au contrat (hors explains/governed_by), étiquetées origine+statut."""
    ents = {e["id"]: e for e in graph.nodes(layer=2, subject=subject, domain=domain)}
    out = []
    for edge in graph.data["edges"].values():
        if edge.get("status") != "active" or edge.get("type") in ("explains", "governed_by"):
            continue
        if edge.get("src") in ents and edge.get("dst") in ents:
            out.append({"type": edge["type"], "de": ents[edge["src"]].get("label"),
                        "vers": ents[edge["dst"]].get("label"),
                        "origine": edge.get("provenance_agent"), "statut": KS.edge_status(graph, edge),
                        "validation_required": edge.get("validation_required", True)})
    return out


def _label_of(graph, nid):
    n = graph.get_node(nid)
    return n.get("label") if n else nid


def reasoning_sheet(graph, subject, domain="axa-contrat", expected=None):
    subs = _by_subtype(graph, subject, domain)
    gar = subs.get("garantie", [])
    principal = [g.get("label") for g in gar if any(p in KG._norm(g.get("label")) for p in _PRINCIPAL)]
    secondaire = [g.get("label") for g in gar if g.get("label") not in principal]
    understanding = _understanding(graph, subject, domain)
    report = CM.explain(graph, subject, domain, expected)
    # environnement (governed_by) — couche séparée
    env = []
    ent_ids = {e["id"] for e in graph.nodes(layer=2, subject=subject, domain=domain)}
    for edge in graph.data["edges"].values():
        if edge.get("status") == "active" and edge.get("type") == "governed_by" and edge.get("src") in ent_ids:
            cn = graph.get_node(edge["dst"])
            if cn:
                env.append({"concept": cn.get("label"), "domaine": cn.get("domain"), "fraicheur": cn.get("freshness")})
    fin = _aspect_of(understanding, subject, "finalite")
    conf = _aspect_of(understanding, subject, "confusions_frequentes")
    return {
        "subject": subject, "domain": domain,
        "finalite": fin or "à approfondir (LLM)",
        "logique_contractuelle": _aspect_of(understanding, subject, "logique_contractuelle"),
        "situations_favorables": _aspect_of(understanding, subject, "situations_favorables"),
        "situations_defavorables": _aspect_of(understanding, subject, "situations_defavorables"),
        "articulations": _articulations(graph, subject, domain),
        "architecture_garanties": {"principales": principal, "secondaires": secondaire, "total": len(gar)},
        "declencheurs": _labels(subs.get("declencheur", [])),
        "conditions": _labels(subs.get("condition", [])),
        "exclusions": _labels(subs.get("exclusion", [])),
        "limites_plafonds": _labels(subs.get("plafond", []) + subs.get("franchise", []) + subs.get("delai", [])),
        "options": _labels(subs.get("option", [])),
        "points_vigilance": _labels(subs.get("point_vigilance", [])),
        "concepts_structurants": [e["concept"] for e in env][:8],
        "environnement": env,
        "preuves": [{"document": (n.get("content") or {}).get("document"),
                     "page": (n.get("content") or {}).get("page"),
                     "citation": (n.get("content") or {}).get("citation")}
                    for n in graph.nodes(layer=1, subject=subject, domain=domain)][:30],
        "comprehension": understanding,
        "confusions_frequentes": conf or "à approfondir (LLM)",
        "incertitudes": [i for i in report["explanations"] if i["axis"] in ("understanding", "relations")],
        "profondeur": report["depth_score"], "couverture_semantique": report["semantic_coverage"],
        "validation": KS.partition(graph, subject, domain),
        "avertissement": "Fiche dérivée du graphe (lecture seule). Blocs de validation SÉPARÉS : "
                         "'validated_knowledge' (masters validés) exposable comme vérité ; "
                         "'pending_interpretations'/'simulated_claude'/'stale'/'contradictory' visibles "
                         "UNIQUEMENT étiquetés, jamais comme clause/règle certaine. Vérifier les preuves.",
    }


def apply_case(graph, subject, case, domain="axa-contrat"):
    """Confronte le contrat au cas. Ne conclut jamais : conclusion PROVISOIRE + réserves."""
    subs = _by_subtype(graph, subject, domain)
    needs = case.get("besoins_exprimes", []) + case.get("besoins_deduits", []) + case.get("objectifs", [])
    need_text = " ".join(needs)
    matched = INn._match_contracts(graph, domain, need_text).get(subject, [])
    exclusions = _labels(subs.get("exclusion", []))
    conditions = _labels(subs.get("condition", []) + subs.get("declencheur", []))
    comp = IC.completeness(case)
    n_needs = max(1, len(needs))
    compat = round(min(1.0, len(matched) / n_needs), 3) if needs else 0.0
    # confiance bornée par la complétude du cas (un cas incomplet ne permet pas de conclure)
    confidence = round(min(compat, comp["score"] if comp["score"] else 0.3), 3)
    return {
        "subject": subject, "case_id": case.get("case_id"),
        "elements_cas_pertinents": IC.facts(case),
        "hypotheses": IC.assumptions(case),
        "clauses_potentiellement_pertinentes": matched,
        "conditions_a_verifier": conditions,
        "exclusions_a_verifier": exclusions,
        "donnees_manquantes": comp["missing"] + case.get("inconnues", []),
        "compatibilite": compat,
        "confiance": confidence,
        "conclusion_provisoire": _provisional(subject, matched, compat, comp),
        "limites_du_raisonnement": [
            "compatibilité = recoupement de termes (déterministe), pas une éligibilité",
            "conditions et exclusions NON vérifiées automatiquement : à confirmer sur pièces",
            "cas possiblement incomplet : conclusion conditionnelle",
        ],
        "validation_humaine_requise": bool(comp["missing"] or exclusions),
    }


def _provisional(subject, matched, compat, comp):
    if not matched:
        return "Le contrat « %s » ne paraît pas répondre au besoin exprimé (aucune garantie recoupée). À confirmer." % subject
    if comp["missing"]:
        return ("Le contrat « %s » pourrait être pertinent (compatibilité %.0f%%), MAIS le cas est incomplet "
                "(manque : %s) : conclusion conditionnelle, vérification requise." % (subject, compat * 100, ", ".join(comp["missing"])))
    return ("Le contrat « %s » paraît pertinent (compatibilité %.0f%%) sous réserve de vérifier conditions "
            "et exclusions sur pièces." % (subject, compat * 100))
