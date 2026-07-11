#!/usr/bin/env python3
"""Modèle de CAS CLIENT générique et strict — la base du raisonnement à partir d'une situation.

Règle centrale : chaque donnée porte un STATUT (confirmé/déclaré/déduit/hypothèse/inconnu/à_vérifier). Le
système ne doit JAMAIS utiliser une hypothèse comme un fait. Les besoins EXPRIMÉS et DÉDUITS restent
séparés. Aucune donnée réelle : uniquement des cas anonymisés/synthétiques. Générique (réutilisable hors
AXA). Aucune dépendance réseau/LLM.
"""
import hashlib

FACT_STATUS = ("confirme", "declare", "deduit", "hypothese", "inconnu", "a_verifier")
# Statuts que l'on PEUT traiter comme des faits établis pour conclure.
FACT_LIKE = ("confirme", "declare")

# Champs standard d'un cas (tous optionnels ; un cas peut être volontairement incomplet).
CASE_FIELDS = (
    "age", "statut_professionnel", "profession", "revenus", "patrimoine", "situation_familiale",
    "enfants", "dettes", "emprunts", "regime_social", "horizon", "budget", "tolerance_risque",
    "priorite", "evenements_recents",
)


def new_datum(value, status="declare"):
    if status not in FACT_STATUS:
        raise ValueError("statut inconnu: %s" % status)
    return {"value": value, "status": status}


def new_case(case_id=None, **kw):
    """Construit un cas vide/partiel. `fields` = {champ: {value,status}}. Listes séparées pour besoins
    exprimés vs déduits, contraintes, objectifs, contrats existants, documents, inconnues."""
    cid = case_id or ("case_" + hashlib.sha256(repr(sorted(kw.items())).encode()).hexdigest()[:12])
    return {
        "case_id": cid, "origin": kw.get("origin", "synthetique"),
        "fields": kw.get("fields", {}),
        "besoins_exprimes": list(kw.get("besoins_exprimes", [])),
        "besoins_deduits": list(kw.get("besoins_deduits", [])),
        "objectifs": list(kw.get("objectifs", [])),
        "contraintes": list(kw.get("contraintes", [])),
        "contrats_existants": list(kw.get("contrats_existants", [])),
        "documents_disponibles": list(kw.get("documents_disponibles", [])),
        "evenements": list(kw.get("evenements", [])),
        "inconnues": list(kw.get("inconnues", [])),
        "demandes_explicites": list(kw.get("demandes_explicites", [])),
    }


def facts(case):
    """Champs utilisables comme FAITS (statut confirmé/déclaré) — jamais les hypothèses/déductions."""
    return {k: v["value"] for k, v in case.get("fields", {}).items()
            if isinstance(v, dict) and v.get("status") in FACT_LIKE}


def assumptions(case):
    return {k: v["value"] for k, v in case.get("fields", {}).items()
            if isinstance(v, dict) and v.get("status") in ("deduit", "hypothese")}


def unknowns(case):
    out = list(case.get("inconnues", []))
    for k, v in case.get("fields", {}).items():
        if isinstance(v, dict) and v.get("status") in ("inconnu", "a_verifier"):
            out.append(k)
    return sorted(set(out))


def validate_case(case):
    """(ok, errors) — vérifie la structure et les statuts. Ne modifie rien."""
    errs = []
    if not case.get("case_id"):
        errs.append("case_id manquant")
    for k, v in case.get("fields", {}).items():
        if not isinstance(v, dict) or "value" not in v or "status" not in v:
            errs.append("champ %s : doit être {value,status}" % k)
        elif v["status"] not in FACT_STATUS:
            errs.append("champ %s : statut invalide %r" % (k, v.get("status")))
    for key in ("besoins_exprimes", "besoins_deduits", "objectifs", "contraintes"):
        if not isinstance(case.get(key, []), list):
            errs.append("%s doit être une liste" % key)
    return (not errs, errs)


def completeness(case, required=("age", "statut_professionnel", "situation_familiale", "objectifs")):
    """Score de complétude [0..1] + champs manquants — pour décider s'il faut demander des informations."""
    have = 0
    missing = []
    for r in required:
        if r == "objectifs":
            ok = bool(case.get("objectifs"))
        else:
            d = case.get("fields", {}).get(r)
            ok = bool(d and d.get("status") in FACT_LIKE)
        have += int(ok)
        if not ok:
            missing.append(r)
    return {"score": round(have / len(required), 3), "missing": missing}
