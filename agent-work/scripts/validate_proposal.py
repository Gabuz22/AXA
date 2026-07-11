#!/usr/bin/env python3
"""Validation d'une proposition : schéma JSON + règles de sécurité métier (fail-closed).

- Valide contre schemas/proposal.schema.json (via `jsonschema` si présent, sinon validateur intégré).
- Applique des règles non négociables :
  * toute cible touchant un master/chemin protégé => validation_required DOIT être true ;
  * un changement réglementaire ne peut PAS être marqué validé par un agent ;
  * une proposition d'extraction/concept/relation SANS source résolvable est rejetée ;
  * chemins de cible sûrs (pas de `..`), extraits filtrés, taille bornée.

Utilisable en bibliothèque (validate) et en CLI (valide un fichier .json).
"""
import sys, os, re, json, argparse
import safety_checks as S

_SCHEMA = None


def schema():
    global _SCHEMA
    if _SCHEMA is None:
        _SCHEMA = S.load_json(os.path.join(S.SCHEMAS_DIR, "proposal.schema.json"))
    return _SCHEMA


# ------------------------------------------------------------------ validateur JSON Schema minimal
def _type_ok(val, t):
    return {
        "object": isinstance(val, dict), "array": isinstance(val, list),
        "string": isinstance(val, str), "integer": isinstance(val, int) and not isinstance(val, bool),
        "number": isinstance(val, (int, float)) and not isinstance(val, bool),
        "boolean": isinstance(val, bool), "null": val is None,
    }.get(t, False)


def _validate_lite(obj, sch, path, errors):
    t = sch.get("type")
    if t:
        types = t if isinstance(t, list) else [t]
        if not any(_type_ok(obj, x) for x in types):
            errors.append("%s: type attendu %s" % (path or "(racine)", types)); return
    if "enum" in sch and obj not in sch["enum"]:
        errors.append("%s: valeur hors enum %s" % (path, sch["enum"]))
    if isinstance(obj, str):
        if "minLength" in sch and len(obj) < sch["minLength"]:
            errors.append("%s: trop court" % path)
        if "maxLength" in sch and len(obj) > sch["maxLength"]:
            errors.append("%s: trop long" % path)
        if "pattern" in sch and not re.search(sch["pattern"], obj):
            errors.append("%s: ne respecte pas le motif" % path)
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        if "minimum" in sch and obj < sch["minimum"]:
            errors.append("%s: < minimum" % path)
        if "maximum" in sch and obj > sch["maximum"]:
            errors.append("%s: > maximum" % path)
    if isinstance(obj, dict):
        for req in sch.get("required", []):
            if req not in obj:
                errors.append("%s: champ requis manquant '%s'" % (path or "(racine)", req))
        props = sch.get("properties", {})
        for k, sub in props.items():
            if k in obj:
                _validate_lite(obj[k], sub, (path + "." + k) if path else k, errors)
    if isinstance(obj, list) and "items" in sch:
        for i, it in enumerate(obj):
            _validate_lite(it, sch["items"], "%s[%d]" % (path, i), errors)


def schema_errors(proposal):
    try:
        import jsonschema  # optionnel
        v = jsonschema.Draft7Validator(schema())
        return ["%s: %s" % ("/".join(str(x) for x in e.path), e.message) for e in v.iter_errors(proposal)]
    except ImportError:
        errs = []
        _validate_lite(proposal, schema(), "", errs)
        return errs


# ------------------------------------------------------------------ règles métier de sécurité
def _touches_protected(target, policies):
    f = (target or {}).get("file") or ""
    if not f:
        return False
    fp = f.replace("\\", "/")
    for prot in policies.get("protected_paths_never_touch", []):
        pp = prot.replace("\\", "/")
        if fp == pp or fp.startswith(pp):
            return True
    return False


def validate(proposal, policies=None):
    """Retourne (ok: bool, errors: list[str]). Modifie proposal en place pour durcir certains champs."""
    policies = policies or S.load_policies()
    errors = list(schema_errors(proposal))

    # Chemin de cible sûr
    tfile = (proposal.get("target") or {}).get("file")
    if tfile and not S.is_safe_relpath(tfile):
        errors.append("target.file non sûr (absolu/`..`/backslash) : %s" % tfile)

    # Master / chemin protégé => validation obligatoire, jamais auto-validable
    if _touches_protected(proposal.get("target"), policies):
        if proposal.get("validation_required") is not True:
            errors.append("cible protégée (master/app/ia) mais validation_required != true")

    # Réglementaire => jamais 'reviewed', toujours validation humaine
    reg = proposal.get("regulatory_status", "none")
    if reg in ("changement_potentiellement_reglementaire", "validation_humaine_requise"):
        if proposal.get("status") == "reviewed":
            errors.append("changement réglementaire marqué 'reviewed' : interdit (validation humaine requise)")
        if proposal.get("validation_required") is not True:
            errors.append("changement réglementaire sans validation_required=true")

    # extraction-llm : la confiance ne doit jamais dépasser 0.95 (v2.4). Une valeur supérieure trahit une
    # proposition produite par une ANCIENNE version du code (bug « ancien code réexécuté ») => rejetée.
    if proposal.get("agent_id") == "extraction-llm":
        conf = proposal.get("confidence")
        if isinstance(conf, (int, float)) and not isinstance(conf, bool) and conf > 0.95:
            errors.append("extraction-llm : confidence %.2f > 0.95 (proposition d'ancienne version, rejetée)" % conf)

    # Source obligatoire pour les types factuels
    ptype = (proposal.get("task") or {}).get("type")
    if ptype in ("extraction", "concept", "relation"):
        src = proposal.get("source") or {}
        has_excerpt = bool((src.get("excerpt") or "").strip())
        has_locator = bool(src.get("document") or src.get("url"))
        if not (has_excerpt and has_locator):
            errors.append("proposition '%s' sans source résolvable (extrait + document/url requis)" % ptype)
        url = src.get("url")
        if url and not S.url_allowed(url, policies):
            errors.append("source.url au schéma non autorisé : %s" % url)

    # Taille bornée
    max_bytes = policies.get("limits", {}).get("max_output_bytes_per_proposal", 65536)
    if len(json.dumps(proposal, ensure_ascii=False).encode("utf-8")) > max_bytes:
        errors.append("proposition trop volumineuse (> %d octets)" % max_bytes)

    return (len(errors) == 0, errors)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", help="chemin d'une proposition .json")
    args = ap.parse_args()
    prop = S.load_json(args.file)
    ok, errs = validate(prop)
    if ok:
        print("[proposal] OK : %s" % args.file)
        return 0
    print("[proposal] INVALIDE : %s" % args.file)
    for e in errs:
        print("  - %s" % e)
    return 1


if __name__ == "__main__":
    sys.exit(main())
