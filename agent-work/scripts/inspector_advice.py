#!/usr/bin/env python3
"""Moteur d'AVIS D'INSPECTEUR — « Que ferais-tu à ma place pour ce client, et pourquoi ? »

Assemble, DÉTERMINISTIQUEMENT, tout ce que la plateforme sait faire en un avis structuré de niveau
inspecteur : lecture du profil → risques applicables PRIORISÉS (protéger avant d'épargner, les dettes
d'abord — heuristiques métier étiquetées) → AUDIT DE L'EXISTANT (couvert / trou / doublon) → plan
d'action ordonné avec pourquoi, questions à poser, pièges fréquents → objections probables → réserves.

Ce moteur n'affirme JAMAIS une éligibilité ni un tarif : il produit un avis CONDITIONNEL, sourcé sur les
fiches, avec validation humaine requise. Les heuristiques (priorités, pièges, objections) proviennent du
raisonnement de Claude (metier_inspecteur.json, origin=simulation_assistee_par_claude) — séparées des
faits du cas et des clauses.
"""
import knowledge_graph as KG
import inspector_case as IC
import inspector_needs as INn


# ------------------------------------------------------------------ lecture du profil (faits uniquement)
def read_profile(case):
    """Drapeaux de profil dérivés des FAITS (confirmé/déclaré) et listes du cas — jamais des hypothèses."""
    facts = IC.facts(case)
    txt = KG._norm(" ".join(str(v) for v in facts.values()))
    flags = set()
    if any(k in txt for k in ("non salarie", "tns", "independant", "liberal", "artisan", "commercant", "chef d'entreprise", "gerant")):
        flags.add("tns")
    elif "salarie" in txt:
        flags.add("salarie")
    if "enfant" in txt or facts.get("enfants"):
        flags.add("enfants")
    if facts.get("emprunts") or facts.get("dettes") or any("achat_immobilier" == e or "credit" in KG._norm(str(e)) for e in case.get("evenements", [])):
        flags.add("credit")
    age = facts.get("age")
    if isinstance(age, (int, float)) and age >= 55:
        flags.add("senior")
    if any(k in txt for k in ("marie", "pacse", "couple")):
        flags.add("couple")
    if "celibataire" in txt and "enfants" not in flags:
        flags.add("solo")                      # leçon exp_003 : sans personne à charge, autres priorités
    return {"flags": sorted(flags), "faits": facts}


# ------------------------------------------------------------------ risques applicables + priorisation
def applicable_risks(case, metier, flags):
    """Risques à traiter : besoins exprimés/déduits (matrice) + implications du profil (règles)."""
    rids, why = {}, {}
    for b in case.get("besoins_exprimes", []) + case.get("besoins_deduits", []) + case.get("objectifs", []):
        for rid, _spec in INn.match_risks(b, metier):
            rids[rid] = True
            why.setdefault(rid, "besoin exprimé/déduit : « %s »" % b)
    for ev in case.get("evenements", []):
        spec = (metier.get("evenements_vie") or {}).get(KG._norm(ev).replace(" ", "_"))
        if spec:
            for rid in spec.get("risques", []):
                rids[rid] = True
                why.setdefault(rid, "événement de vie : %s" % ev)
    for regle in (metier.get("priorites_risques", {}).get("regles") or []):
        if regle.get("si") in flags:
            for rid in regle.get("risques", []):
                rids[rid] = True
                why.setdefault(rid, "profil %s — %s" % (regle["si"], regle.get("pourquoi", "")))
    return rids, why


def prioritize(rids, metier, flags):
    """Ordre d'inspecteur : socle (catastrophique→confort) puis remontée des risques boostés par le profil."""
    socle = metier.get("priorites_risques", {}).get("ordre_socle") or list(rids)
    ordered = [r for r in socle if r in rids] + [r for r in rids if r not in socle]
    boosted = []
    for regle in (metier.get("priorites_risques", {}).get("regles") or []):
        if regle.get("si") in flags:
            boosted += [r for r in regle.get("risques", []) if r in rids]
    # stable : les boostés remontent en tête dans l'ordre du socle
    head = [r for r in ordered if r in boosted]
    tail = [r for r in ordered if r not in boosted]
    out = head + tail
    # rétrogradations (leçon exp_003 : « solo » -> le décès n'est pas prioritaire sans personne à charge)
    demoted = []
    for regle in (metier.get("priorites_risques", {}).get("regles") or []):
        if regle.get("si") in flags:
            demoted += regle.get("retrograde", [])
    return [r for r in out if r not in demoted] + [r for r in out if r in demoted]


# ------------------------------------------------------------------ audit de l'existant
def audit_existing(case, metier, rids):
    """Pour chaque risque applicable : couvert par l'existant ? doublon ? trou ? (à confirmer sur pièces)."""
    existing = [str(c) for c in case.get("contrats_existants", [])]
    def owners(rid):
        contracts = (metier.get("risques", {}).get(rid) or {}).get("contrats", [])
        out = []
        for e in existing:
            en = KG._norm(e)
            for c in contracts:
                cn = KG._norm(c)
                if en and (en in cn or cn in en or en.split()[0] == cn.split()[0]):
                    out.append(c)
                    break
        return out
    audit = {}
    for rid in rids:
        ow = owners(rid)
        audit[rid] = {"couvert_par": ow,
                      "statut": ("doublon_potentiel" if len(ow) > 1 else
                                 "couvert_a_verifier" if ow else "trou_potentiel")}
    return {"contrats_existants": existing, "par_risque": audit,
            "note": "audit heuristique (rattachement par nom + matrice) : à confirmer sur les contrats réels du client"}


# ------------------------------------------------------------------ l'avis
def advise(case, graph, metier, domain="axa-contrat"):
    ok, errs = IC.validate_case(case)
    profile = read_profile(case)
    flags = set(profile["flags"])
    rids, why = applicable_risks(case, metier, flags)
    order = prioritize(rids, metier, flags)
    audit = audit_existing(case, metier, rids)
    comp = IC.completeness(case)

    plan, pieges_all, objections = [], {}, []
    for i, rid in enumerate(order, 1):
        spec = metier.get("risques", {}).get(rid) or {}
        a = audit["par_risque"].get(rid, {})
        candidats = [c for c in spec.get("contrats", []) if c not in a.get("couvert_par", [])]
        pieges = {}
        for c in spec.get("contrats", []):
            for p in (metier.get("pieges_frequents", {}).get(c) or []):
                pieges.setdefault(c, []).append(p)
        pieges_all.update(pieges)
        plan.append({
            "etape": i, "risque": rid, "libelle": spec.get("libelle", rid),
            "pourquoi": why.get(rid, ""),
            "statut_existant": a.get("statut"), "couvert_par": a.get("couvert_par", []),
            "contrats_a_examiner": candidats,
            "questions_a_poser": spec.get("questions", []),
            "pieges_frequents": pieges,
        })
        for ob in (metier.get("objections", {}).get(rid) or []):
            objections.append({"risque": rid, **ob})

    doublons = [r for r, a in audit["par_risque"].items() if a["statut"] == "doublon_potentiel"]
    trous = [r for r, a in audit["par_risque"].items() if a["statut"] == "trou_potentiel"]

    # RETOURS D'EXPÉRIENCE (bibliothèque des raisonnements) : « j'ai déjà rencontré des situations proches »
    experience = {"dossiers_similaires": 0, "lecons": []}
    lib = metier.get("_experience") or {}
    for d in lib.get("dossiers", []):
        sit = d.get("situation", {})
        common_flags = set(sit.get("flags", [])) & flags
        common_risks = set(sit.get("risques", [])) & set(rids)
        if common_flags or len(common_risks) >= 2:
            experience["dossiers_similaires"] += 1
        for le in d.get("lecons", []):
            if set(le.get("si", [])) <= flags:
                experience["lecons"].append({"lecon": le["lecon"], "type": le.get("type"),
                                             "source": d["id"], "origine": lib.get("origin")})

    return {
        "case_id": case.get("case_id"), "case_valid": ok, "case_errors": errs,
        "profil": profile,
        "principe_de_priorisation": metier.get("priorites_risques", {}).get("principe"),
        "risques_priorises": order,
        "audit_existant": audit,
        "trous_de_couverture_potentiels": trous,
        "doublons_potentiels": doublons,
        "plan_action": plan,
        "retours_experience": experience,
        "objections_probables": objections,
        "informations_manquantes": comp["missing"] + IC.unknowns(case),
        "hypotheses": IC.assumptions(case),
        "reserves": [
            "avis CONDITIONNEL fondé sur les faits déclarés : toute donnée manquante peut changer les priorités",
            "aucune éligibilité, aucun tarif, aucune règle fiscale affirmés : à vérifier sur pièces et sources à jour",
            "heuristiques métier étiquetées %s : à confirmer par un inspecteur humain" % (metier.get("origin") or "?"),
        ],
        "validation_humaine_requise": True,
        "origin_heuristiques": metier.get("origin"),
    }
