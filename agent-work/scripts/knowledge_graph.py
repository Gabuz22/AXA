#!/usr/bin/env python3
"""Graphe de connaissances GÉNÉRIQUE en couches — substrat unique de la plateforme d'apprentissage.

Ce module ne connaît AUCUN domaine (AXA, fiscalité, médical…) : il fournit une structure de connaissance
réutilisable pour tout corpus. C'est la « source de vérité » vers laquelle convergent progressivement les
mémoires éparses (coverage_map, mémoire d'extraction, backlog).

Quatre COUCHES (le sens, pas le PDF) :
  L1 evidence      — preuve brute sourcée : (document, page, citation, hash). Append-only, jamais réécrite.
  L2 normalized    — fait/entité canonique (une garantie, une exclusion, un concept), dédupliqué, typé.
  L3 relation      — arête typée entre entités (depends_on, excludes, triggers, …). Peut traverser domaines.
  L4 understanding — synthèse/explication rattachée à une entité, recalculable, traçable vers L1/L3.

Invariants de robustesse pluriannuelle :
  • chaque nœud/arête porte : domaine, sources (provenance), confiance, fraîcheur (as_of + ttl), hash, dates ;
  • les domaines sont SÉPARÉS (une clause contractuelle et une règle fiscale ne se mélangent jamais) mais
    des arêtes PEUVENT les relier (une garantie `governed_by` un article de code) ;
  • l'évidence (L1) est immuable : une correction crée un nouveau nœud et `supersede` l'ancien ;
  • déduplication déterministe par clé canonique → idempotence des reruns, zéro doublon.

I/O injectée (load_json/write_json) → testable hors-ligne, sans dépendance produit.
"""
import hashlib
import json as _json
import datetime as _dt

LAYERS = {1: "evidence", 2: "normalized", 3: "relation", 4: "understanding"}

# Relations de la couche 3 (extensibles ; un domaine peut en ajouter via son adaptateur).
RELATION_TYPES = frozenset({
    "depends_on", "excludes", "complements", "triggers", "requires", "limits",
    "replaces", "comparable_to", "governed_by", "explains", "refines", "contradicts",
})

NODE_STATUS = frozenset({"active", "superseded", "contested"})


def _now_iso():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canon(obj):
    return _json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_hash(obj):
    return "k_" + hashlib.sha256(_canon(obj).encode("utf-8")).hexdigest()[:20]


def _norm(t):
    return " ".join((t or "").lower().split())


def evidence_id(domain, document, page, citation):
    """Id STABLE d'une preuve : même (domaine, document, page, citation) => même nœud (dédup, immutable)."""
    return content_hash({"L": 1, "d": domain, "doc": document, "p": page, "c": _norm(citation)})


def entity_id(domain, subject, subtype, label):
    """Id STABLE d'une entité normalisée : indépendant du contenu (le contenu peut être enrichi sans
    changer l'identité de l'entité)."""
    return content_hash({"L": 2, "d": domain, "s": _norm(subject), "t": subtype, "l": _norm(label)})


def relation_id(rtype, src, dst):
    return content_hash({"L": 3, "r": rtype, "src": src, "dst": dst})


def understanding_id(target_id, aspect):
    return content_hash({"L": 4, "tgt": target_id, "a": aspect})


class KnowledgeGraph:
    def __init__(self, path, load_json=None, write_json=None, now=_now_iso):
        self.path = path
        self._write = write_json
        self._now = now
        data = None
        if load_json is not None:
            try:
                data = load_json(path, default=None)
            except Exception:
                data = None
        self.data = data or {"version": "1.0.0", "nodes": {}, "edges": {}, "updated_at": None}
        self.data.setdefault("nodes", {})
        self.data.setdefault("edges", {})

    # ------------------------------------------------------------------ L1 : preuve (append-only)
    def add_evidence(self, domain, subject, document, page, citation, agent,
                     as_of=None, confidence=0.9, ttl_days=None):
        nid = evidence_id(domain, document, page, citation)
        now = self._now()
        prev = self.data["nodes"].get(nid)
        if prev:
            prev["freshness"]["checked_at"] = now       # re-vue d'une preuve identique : on rafraîchit la vérif
            prev["times_seen"] = prev.get("times_seen", 1) + 1
            return prev
        node = {
            "id": nid, "layer": 1, "type": "evidence", "domain": domain, "subject": subject,
            "subtype": "citation", "label": (citation or "")[:120],
            "content": {"document": document, "page": page, "citation": citation},
            "sources": [{"document": document, "page": page, "citation": citation,
                         "as_of": as_of or now}],
            "confidence": round(float(confidence), 3),
            "freshness": {"as_of": as_of or now, "ttl_days": ttl_days, "checked_at": now},
            "content_hash": content_hash({"document": document, "page": page, "citation": _norm(citation)}),
            "status": "active", "provenance_agent": agent, "created_at": now, "updated_at": now,
            "times_seen": 1,
        }
        self.data["nodes"][nid] = node
        return node

    # ------------------------------------------------------------------ L2 : entité normalisée (dédupliquée)
    def upsert_entity(self, domain, subject, subtype, label, content=None, evidence_ids=None,
                      agent="", confidence=0.7, ttl_days=None, as_of=None):
        nid = entity_id(domain, subject, subtype, label)
        now = self._now()
        chash = content_hash(content or {})
        node = self.data["nodes"].get(nid)
        if node is None:
            node = {
                "id": nid, "layer": 2, "type": "entity", "domain": domain, "subject": subject,
                "subtype": subtype, "label": label, "content": content or {},
                "sources": [{"evidence": e} for e in (evidence_ids or [])],
                "confidence": round(float(confidence), 3),
                "freshness": {"as_of": as_of or now, "ttl_days": ttl_days, "checked_at": now},
                "content_hash": chash, "status": "active", "provenance_agent": agent,
                "created_at": now, "updated_at": now, "revision": 1,
            }
            self.data["nodes"][nid] = node
            return node, True
        # entité connue : enrichissement (le contenu peut évoluer sans changer l'identité)
        changed = node.get("content_hash") != chash
        if content:
            node["content"] = content
            node["content_hash"] = chash
        for e in (evidence_ids or []):
            if {"evidence": e} not in node["sources"]:
                node["sources"].append({"evidence": e})
        node["confidence"] = round(max(node.get("confidence", 0.0), float(confidence)), 3)
        node["freshness"]["checked_at"] = now
        if changed:
            node["updated_at"] = now
            node["revision"] = node.get("revision", 1) + 1
        return node, changed

    # ------------------------------------------------------------------ L3 : relation typée (arête)
    def add_relation(self, rtype, src, dst, agent="", confidence=0.6, evidence_ids=None):
        if rtype not in RELATION_TYPES:
            raise ValueError("relation inconnue: %s" % rtype)
        eid = relation_id(rtype, src, dst)
        now = self._now()
        prev = self.data["edges"].get(eid)
        if prev:
            prev["confidence"] = round(max(prev.get("confidence", 0.0), float(confidence)), 3)
            prev["updated_at"] = now
            return prev, False
        edge = {
            "id": eid, "layer": 3, "type": rtype, "src": src, "dst": dst,
            "sources": [{"evidence": e} for e in (evidence_ids or [])],
            "confidence": round(float(confidence), 3), "status": "active",
            "provenance_agent": agent, "created_at": now, "updated_at": now,
        }
        self.data["edges"][eid] = edge
        return edge, True

    # ------------------------------------------------------------------ L4 : compréhension (recalculable)
    def upsert_understanding(self, target_id, aspect, text, agent="", confidence=0.55,
                             evidence_ids=None, relation_ids=None):
        nid = understanding_id(target_id, aspect)
        now = self._now()
        chash = content_hash({"t": _norm(text)})
        node = self.data["nodes"].get(nid)
        payload = {"aspect": aspect, "text": text,
                   "derived_from": {"evidence": list(evidence_ids or []), "relations": list(relation_ids or [])}}
        if node is None:
            node = {
                "id": nid, "layer": 4, "type": "understanding", "domain": None,
                "subject": target_id, "subtype": aspect, "label": aspect,
                "content": payload, "sources": [{"target": target_id}],
                "confidence": round(float(confidence), 3),
                "freshness": {"as_of": now, "ttl_days": None, "checked_at": now},
                "content_hash": chash, "status": "active", "provenance_agent": agent,
                "created_at": now, "updated_at": now, "revision": 1,
            }
            self.data["nodes"][nid] = node
            # rattachement explicite entité -> explication
            self.add_relation("explains", nid, target_id, agent=agent, confidence=confidence)
            return node, True
        changed = node.get("content_hash") != chash
        node["content"] = payload
        node["content_hash"] = chash
        node["confidence"] = round(float(confidence), 3)
        node["freshness"]["checked_at"] = now
        if changed:
            node["updated_at"] = now
            node["revision"] = node.get("revision", 1) + 1
        return node, changed

    # ------------------------------------------------------------------ supersession (jamais de suppression L1)
    def supersede(self, node_id, by_id=None, agent=""):
        n = self.data["nodes"].get(node_id)
        if not n:
            return None
        n["status"] = "superseded"
        n["superseded_by"] = by_id
        n["updated_at"] = self._now()
        return n

    # ------------------------------------------------------------------ requêtes
    def get_node(self, nid):
        return self.data["nodes"].get(nid)

    def nodes(self, layer=None, domain=None, subject=None, status="active"):
        out = []
        for n in self.data["nodes"].values():
            if status and n.get("status") != status:
                continue
            if layer is not None and n.get("layer") != layer:
                continue
            if domain is not None and n.get("domain") != domain:
                continue
            if subject is not None and _norm(n.get("subject")) != _norm(subject):
                continue
            out.append(n)
        return out

    def edges_of(self, node_id, rtype=None, direction="out"):
        out = []
        for e in self.data["edges"].values():
            if e.get("status") != "active":
                continue
            if rtype and e.get("type") != rtype:
                continue
            if direction in ("out", "any") and e.get("src") == node_id:
                out.append(e)
            elif direction in ("in", "any") and e.get("dst") == node_id:
                out.append(e)
        return out

    def has_understanding(self, entity_id_):
        return any(e.get("type") == "explains" and e.get("dst") == entity_id_
                   for e in self.data["edges"].values() if e.get("status") == "active")

    def is_fresh(self, node, now=None):
        fr = (node or {}).get("freshness") or {}
        ttl = fr.get("ttl_days")
        if not ttl:
            return True                                  # sans TTL : réputé frais (données contractuelles stables)
        base = _parse(fr.get("checked_at") or fr.get("as_of"))
        if not base:
            return True
        ref = _parse(now) if now else _dt.datetime.now(_dt.timezone.utc)
        return (ref - base).days <= int(ttl)

    def stats(self):
        c = {1: 0, 2: 0, 3: 0, 4: 0}
        for n in self.data["nodes"].values():
            if n.get("status") == "active":
                c[n.get("layer", 0)] = c.get(n.get("layer", 0), 0) + 1
        return {"evidence": c[1], "normalized": c[2], "understanding": c[4],
                "relations": sum(1 for e in self.data["edges"].values() if e.get("status") == "active")}

    def save(self):
        if self._write is None:
            return
        self.data["updated_at"] = self._now()
        self._write(self.path, self.data)


def _parse(iso):
    try:
        return _dt.datetime.fromisoformat((iso or "").replace("Z", "+00:00"))
    except Exception:
        return None
