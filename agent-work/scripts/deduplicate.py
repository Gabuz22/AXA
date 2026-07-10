#!/usr/bin/env python3
"""Détection de doublons stricts entre propositions.

Empreinte déterministe = agent + type + cible + source (doc/page/url) + opération + payload normalisé.
Deux propositions ayant la même empreinte sont des doublons stricts. On ne déduplique jamais par
« proximité sémantique » — uniquement l'égalité normalisée, pour rester prudent et explicable.
"""
import os, json, glob
import safety_checks as S


def _norm(v):
    if isinstance(v, dict):
        return {k: _norm(v[k]) for k in sorted(v)}
    if isinstance(v, list):
        return [_norm(x) for x in v]
    if isinstance(v, str):
        return " ".join(v.split()).strip().lower()
    return v


def fingerprint(proposal):
    src = proposal.get("source") or {}
    tgt = proposal.get("target") or {}
    chg = proposal.get("proposed_change") or {}
    key = {
        "agent": proposal.get("agent_id"),
        "type": (proposal.get("task") or {}).get("type"),
        "contract": tgt.get("contract"),
        "file": tgt.get("file"),
        "section": tgt.get("section"),
        "doc": src.get("document"),
        "page": src.get("page"),
        "url": src.get("url"),
        "operation": chg.get("operation"),
        "payload": _norm(chg.get("payload") or {}),
        "excerpt": _norm(src.get("excerpt") or "")[:400],
    }
    return S.content_hash(json.dumps(_norm(key), ensure_ascii=False, sort_keys=True))


def existing_fingerprints(dirs):
    fps = {}
    for d in dirs:
        for fp_file in glob.glob(os.path.join(d, "*.json")):
            try:
                p = S.load_json(fp_file)
            except Exception:
                continue
            fps[fingerprint(p)] = fp_file
    return fps


def is_duplicate(proposal, dirs):
    return fingerprint(proposal) in existing_fingerprints(dirs)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: deduplicate.py <proposal.json> [dir ...]"); sys.exit(2)
    prop = S.load_json(sys.argv[1])
    dirs = sys.argv[2:] or [os.path.dirname(sys.argv[1])]
    dup = is_duplicate(prop, dirs)
    print("fingerprint=%s duplicate=%s" % (fingerprint(prop), dup))
    sys.exit(1 if dup else 0)
