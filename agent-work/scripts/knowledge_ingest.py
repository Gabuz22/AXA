#!/usr/bin/env python3
"""Ingestion DÉTERMINISTE — alimente le graphe de connaissances depuis un domaine. Zéro token.

Deux sources, projetées dans les couches du graphe (idempotent, dédup par le graphe) :
  1) la connaissance DÉJÀ structurée du domaine (adapter.structured_entities) → entités L2, + preuve L1
     quand l'item est sourcé (document + page). Amorce le graphe avec ce que la base sait déjà.
  2) les PROPOSITIONS des agents producteurs (extraction-llm : pending + reviewed) → preuve L1 (citation
     vérifiée sur la page) + entité L2 rattachée. C'est ce que les agents ont découvert d'ABSENT.

Ne modifie aucun agent ni aucune proposition : lit leurs sorties et les projette. Une entité sans preuve
(item non sourcé) reste en L2 « dérivée » à faible confiance → génère naturellement une tâche 'sourcer'
côté couverture. Rejouable : relancer l'ingestion ne crée aucun doublon (identités canoniques du graphe).
"""
import glob
import os
import safety_checks as S
from agents import base
import knowledge_graph as KG

EXTRACTION_DIRS = ("agent-work/extraction/pending", "agent-work/extraction/reviewed")


def _load_json(path, default=None):
    return S.load_json(path, default=default)


def _extraction_proposals():
    out = []
    for d in EXTRACTION_DIRS:
        for f in glob.glob(base.repo_path(os.path.join(d, "*.json"))):
            try:
                p = S.load_json(f)
            except Exception:
                continue
            if p.get("agent_id") == "extraction-llm":
                out.append(p)
    return out


def ingest(adapter, graph, policies=None, with_proposals=True):
    """Projette un domaine dans le graphe. Retourne des statistiques. Ne consomme aucun token."""
    domain = adapter.domain_id
    st = {"entities_structured": 0, "evidence_structured": 0, "evidence_proposals": 0,
          "entities_proposals": 0, "subjects": set()}

    # 1) connaissance structurée : L2 (+ L1 si sourcée)
    for e in adapter.structured_entities():
        subject = e["subject"]
        st["subjects"].add(subject)
        evidence_ids = []
        src = e.get("source")
        if src and src.get("document") and src.get("page") is not None:
            ev = graph.add_evidence(domain, subject, src["document"], src["page"],
                                    e["label"], agent="ingest-structured",
                                    confidence=min(0.9, float(e.get("confidence", 0.6))))
            evidence_ids = [ev["id"]]
            st["evidence_structured"] += 1
        _n, new = graph.upsert_entity(domain, subject, e["subtype"], e["label"],
                                      content=e.get("content", {}), evidence_ids=evidence_ids,
                                      confidence=float(e.get("confidence", 0.6)), agent="ingest-structured")
        st["entities_structured"] += int(new)

    # 2) propositions d'extraction : L1 (preuve) + L2 (fait découvert)
    if with_proposals:
        for p in _extraction_proposals():
            src = p.get("source") or {}
            payload = (p.get("proposed_change") or {}).get("payload") or {}
            target = p.get("target") or {}
            subject = adapter.subject_of(target.get("contract"))
            document = src.get("document")
            page = src.get("page")
            citation = src.get("excerpt") or payload.get("citation_exacte")
            if not (document and citation):
                continue
            conf = float(p.get("confidence") or 0.6)
            ev = graph.add_evidence(domain, subject, document, page, citation,
                                    agent="extraction-llm", confidence=conf)
            st["evidence_proposals"] += 1
            cat = payload.get("categorie") or target.get("section") or "fait"
            label = (payload.get("texte") or citation)[:120]
            _n, new = graph.upsert_entity(domain, subject, cat, label,
                                          content={"texte": payload.get("texte"), "diff": payload.get("diff"),
                                                   "why_missing": payload.get("why_missing")},
                                          evidence_ids=[ev["id"]], confidence=conf, agent="extraction-llm")
            st["entities_proposals"] += int(new)
            st["subjects"].add(subject)

    graph.save()
    st["subjects"] = sorted(x for x in st["subjects"] if x)
    st["graph"] = graph.stats()
    return st


def main():
    import argparse
    import domain_adapter
    ap = argparse.ArgumentParser(description="Ingestion déterministe d'un domaine dans le graphe de connaissances.")
    ap.add_argument("--domain", default="axa-contrat")
    ap.add_argument("--no-proposals", action="store_true", help="n'ingère que la connaissance structurée")
    ap.add_argument("--dry-run", action="store_true", help="ne sauvegarde pas le graphe")
    args = ap.parse_args()

    adapter = domain_adapter.get(args.domain)
    path = base.repo_path("agent-work/knowledge/graph.json")
    write = None if args.dry_run else S.write_json
    graph = KG.KnowledgeGraph(path, load_json=_load_json, write_json=write)
    st = ingest(adapter, graph, with_proposals=not args.no_proposals)
    import json
    print("INGEST %s -> %s" % (args.domain, json.dumps({k: v for k, v in st.items() if k != "subjects"}, ensure_ascii=False)))
    print("Sujets: %s" % ", ".join(st["subjects"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
