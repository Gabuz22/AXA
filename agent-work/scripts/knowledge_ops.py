#!/usr/bin/env python3
"""Passes DÉTERMINISTES sur le graphe de connaissances — zéro token.

Ce sont les « agents » que la mission listait (Duplicate Finder, Contradiction Finder, Freshness Checker,
Cost Optimizer) ramenés à ce qu'ils sont réellement : des fonctions pures sur le graphe. Prudence :
elles SIGNALENT des candidats à vérifier, elles n'affirment jamais.
"""
import hashlib
import knowledge_graph as KG

# Mots signalant une portée « négative » (utile au repérage prudent de tensions garantie/exclusion).
_NEG = ("exclu", "sauf", "ne sont pas", "aucune", "hors", "ne couvre pas", "non garanti", "sans")


def _simplify(label):
    return "".join(ch for ch in KG._norm(label) if ch.isalnum())[:48]


def find_duplicates(graph, domain=None):
    """Entités L2 quasi-identiques (même domaine/sujet/sous-type, libellé simplifié identique). Retourne
    des paires (id_gardé, id_doublon). Déterministe, prudent (n'agit pas, signale)."""
    seen, dups = {}, []
    for n in graph.nodes(layer=2, domain=domain):
        key = (n.get("domain"), KG._norm(n.get("subject")), n.get("subtype"), _simplify(n.get("label")))
        if key in seen and seen[key] != n["id"]:
            dups.append((seen[key], n["id"]))
        else:
            seen.setdefault(key, n["id"])
    return dups


def find_stale(graph, now=None):
    """Nœuds actifs dont la fraîcheur a expiré (TTL dépassé). Sans TTL => jamais périmé (données stables)."""
    return [n["id"] for n in graph.data["nodes"].values()
            if n.get("status") == "active" and not graph.is_fresh(n, now)]


def find_contradiction_candidates(graph, subject, domain=None):
    """CANDIDATS de tension à vérifier (jamais une affirmation). Prudent : une garantie et une exclusion du
    même sujet partageant plusieurs mots significatifs, l'exclusion portant une négation → à arbitrer."""
    gars = [n for n in graph.nodes(layer=2, subject=subject, domain=domain) if n.get("subtype") == "garantie"]
    excs = [n for n in graph.nodes(layer=2, subject=subject, domain=domain) if n.get("subtype") == "exclusion"]
    out = []
    for g in gars:
        gw = _words(g.get("label"))
        for e in excs:
            etext = KG._norm(e.get("label"))
            if any(neg in etext for neg in _NEG) and len(gw & _words(e.get("label"))) >= 2:
                out.append((g["id"], e["id"]))
    return out


def _words(label):
    return {w for w in KG._norm(label).split() if len(w) > 3}


# ------------------------------------------------------------------ gouvernance des coûts
class CostLedger:
    """Comptabilité de coût par domaine et par semaine ISO. Déterministe. Sert de portier à l'LLM :
    on n'appelle un fournisseur que si le budget hebdomadaire du domaine n'est pas atteint."""

    def __init__(self, path, load_json=None, write_json=None, now_week=None):
        self.path = path
        self._write = write_json
        self._week = now_week or _iso_week
        data = None
        if load_json is not None:
            try:
                data = load_json(path, default=None)
            except Exception:
                data = None
        self.data = data or {"version": "1.0.0", "weeks": {}}
        self.data.setdefault("weeks", {})

    def _bucket(self, domain):
        wk = self._week()
        return self.data["weeks"].setdefault(wk, {}).setdefault(domain, {"llm_calls": 0, "tokens": 0})

    def record(self, domain, llm_calls=0, tokens=0):
        b = self._bucket(domain)
        b["llm_calls"] += int(llm_calls)
        b["tokens"] += int(tokens)
        return b

    def used(self, domain):
        return dict(self._bucket(domain))

    def can_spend(self, domain, weekly_call_cap):
        return self._bucket(domain)["llm_calls"] < int(weekly_call_cap)

    def save(self):
        if self._write is not None:
            self._write(self.path, self.data)


def _iso_week():
    import datetime
    y, w, _ = datetime.datetime.now(datetime.timezone.utc).isocalendar()
    return "%04d-W%02d" % (y, w)


def task_id(*parts):
    return "ko_" + hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:16]
