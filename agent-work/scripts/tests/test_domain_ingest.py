#!/usr/bin/env python3
"""Tests de la phase 1 : DomainAdapter + ingestion déterministe vers le graphe.

Démontre : projection de la connaissance structurée en L2 (+ L1 quand sourcée), projection des
propositions d'extraction en L1+L2, alignement des sujets (slug<->nom), idempotence (rerun sans doublon),
zéro dépendance réseau/LLM. Un test de fumée charge le VRAI adaptateur AXA.
"""
import os, sys, json, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
import knowledge_graph as KG
import knowledge_ingest as KI


def _mem_graph():
    store = {}
    def wj(p, d, **k): store[p] = json.loads(json.dumps(d))
    def lj(p, default=None): return json.loads(json.dumps(store[p])) if p in store else default
    return KG.KnowledgeGraph("g.json", load_json=lj, write_json=wj, now=lambda: "2026-07-11T00:00:00Z")


class FakeAdapter:
    domain_id = "test-dom"
    environment_domains = ("env",)
    def structured_entities(self):
        return [
            {"subject": "C1", "subtype": "garantie", "label": "Capital deces",
             "content": {"resume": "x"}, "source": {"document": "n.pdf", "page": 5, "section": "2.1"},
             "confidence": 0.9},
            {"subject": "C1", "subtype": "exclusion", "label": "Guerre",
             "content": {}, "source": None, "confidence": 0.5},          # non sourcée -> L2 seule
        ]
    def subject_of(self, ref):
        return "C1" if ref else ref


class TestStructuredIngest(unittest.TestCase):
    def test_structured_creates_l2_and_l1_when_sourced(self):
        g = _mem_graph()
        st = KI.ingest(FakeAdapter(), g, with_proposals=False)
        self.assertEqual(st["entities_structured"], 2)
        self.assertEqual(st["evidence_structured"], 1)          # seule l'entité sourcée crée une preuve
        self.assertEqual(g.stats()["normalized"], 2)
        self.assertEqual(g.stats()["evidence"], 1)

    def test_ingest_is_idempotent(self):
        g = _mem_graph()
        KI.ingest(FakeAdapter(), g, with_proposals=False)
        before = g.stats()
        KI.ingest(FakeAdapter(), g, with_proposals=False)          # rerun
        self.assertEqual(g.stats(), before)                        # aucun doublon

    def test_unsourced_entity_has_no_evidence(self):
        g = _mem_graph()
        KI.ingest(FakeAdapter(), g, with_proposals=False)
        excl = [n for n in g.nodes(layer=2) if n["subtype"] == "exclusion"][0]
        self.assertEqual(excl["sources"], [])                      # dérivée, sans preuve -> à sourcer


class TestProposalIngest(unittest.TestCase):
    def test_extraction_proposal_projected_to_l1_l2_aligned_subject(self):
        g = _mem_graph()
        # amorce structurée (sujet = nom "C1")
        KI.ingest(FakeAdapter(), g, with_proposals=False)
        # une proposition d'extraction (sujet = slug "c1") doit se rattacher au MÊME sujet "C1"
        prop = {"agent_id": "extraction-llm", "confidence": 0.8,
                "target": {"contract": "c1", "section": "garanties"},
                "source": {"document": "n.pdf", "page": 8, "excerpt": "La rente est versee mensuellement."},
                "proposed_change": {"payload": {"categorie": "garanties", "texte": "Rente mensuelle",
                                                "citation_exacte": "La rente est versee mensuellement."}}}
        orig = KI._extraction_proposals
        KI._extraction_proposals = lambda: [prop]
        try:
            st = KI.ingest(FakeAdapter(), g, with_proposals=True)
        finally:
            KI._extraction_proposals = orig
        self.assertEqual(st["evidence_proposals"], 1)
        self.assertEqual(st["entities_proposals"], 1)
        # le fait découvert est rattaché au sujet canonique C1 (pas un sujet "c1" distinct)
        subjects = {n["subject"] for n in g.nodes(layer=2)}
        self.assertEqual(subjects, {"C1"})
        rente = [n for n in g.nodes(layer=2) if n["label"] == "Rente mensuelle"][0]
        self.assertTrue(rente["sources"])                          # entité issue d'extraction : sourcée


class TestRealAXAAdapter(unittest.TestCase):
    def test_axa_adapter_loads_real_structured_knowledge(self):
        try:
            import domain_adapter
            a = domain_adapter.get("axa-contrat")
        except Exception as e:
            self.skipTest("adaptateur AXA indisponible: %s" % e)
        ents = a.structured_entities()
        if not ents:
            self.skipTest("connaissance structurée AXA absente dans cet environnement")
        self.assertGreater(len(ents), 20)                          # contrats.json est riche
        self.assertTrue(all("subject" in e and "subtype" in e and "label" in e for e in ents))
        self.assertIn("axa-contrat", domain_adapter.available())


if __name__ == "__main__":
    unittest.main(verbosity=2)
