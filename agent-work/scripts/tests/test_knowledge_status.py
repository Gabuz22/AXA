#!/usr/bin/env python3
"""Tests des statuts de validation + pont contrôlé (Phases 4-5). 0 token.

Vérifie : dérivation déterministe du statut selon provenance/fraîcheur/confiance ; le simulé Claude n'est
JAMAIS exposable comme vérité ; les blocs de la projection sont séparés et étiquetés.
"""
import os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
import knowledge_graph as KG
import knowledge_status as KS


def _g():
    return KG.KnowledgeGraph("g.json", now=lambda: "2026-07-12T00:00:00Z")


class TestStatuses(unittest.TestCase):
    def test_master_is_validated(self):
        g = _g()
        n, _ = g.upsert_entity("axa-contrat", "C1", "garantie", "Capital", agent="ingest-structured")
        self.assertEqual(KS.node_status(g, n), "validated")
        self.assertTrue(KS.is_exposable_as_truth("validated"))

    def test_simulated_never_truth(self):
        g = _g()
        n, _ = g.upsert_entity("axa-contrat", "C1", "garantie", "X", agent="simulation_assistee_par_claude")
        self.assertEqual(KS.node_status(g, n), "simulated_claude")
        self.assertFalse(KS.is_exposable_as_truth("simulated_claude"))

    def test_llm_is_pending(self):
        g = _g()
        n, _ = g.upsert_entity("axa-contrat", "C1", "garantie", "Y", agent="knowledge-builder")
        self.assertEqual(KS.node_status(g, n), "pending_review")
        self.assertFalse(KS.is_exposable_as_truth("pending_review"))

    def test_stale(self):
        g = _g()
        n = g.add_evidence("axa-contrat", "C1", "n.pdf", 1, "cit", "environment-ingest",
                           as_of="2020-01-01T00:00:00Z", ttl_days=30)
        n["freshness"]["checked_at"] = "2020-01-01T00:00:00Z"
        self.assertEqual(KS.node_status(g, n, now="2026-07-12T00:00:00Z"), "stale")

    def test_edge_simulated_and_derived(self):
        g = _g()
        a, _ = g.upsert_entity("axa-contrat", "C1", "garantie", "A")
        b, _ = g.upsert_entity("axa-contrat", "C1", "exclusion", "B")
        e1, _ = g.add_relation("excludes", a["id"], b["id"], agent="simulation_assistee_par_claude")
        self.assertEqual(KS.edge_status(g, e1), "simulated_claude")
        c, _ = g.upsert_entity("reglementation", "C1", "concept_reglementaire", "Inv")
        e2, _ = g.add_relation("governed_by", a["id"], c["id"], agent="environment-ingest")
        self.assertEqual(KS.edge_status(g, e2), "derived_deterministic")


class TestPartition(unittest.TestCase):
    def test_blocks_separated_and_labeled(self):
        g = _g()
        g.upsert_entity("axa-contrat", "C1", "garantie", "Master gar", agent="ingest-structured")
        g.upsert_entity("axa-contrat", "C1", "garantie", "Sim gar", agent="simulation_assistee_par_claude")
        p = KS.partition(g, "C1", "axa-contrat")
        vlabels = {x["label"] for x in p["blocks"]["validated_knowledge"]}
        slabels = {x["label"] for x in p["blocks"]["simulated_claude"]}
        self.assertIn("Master gar", vlabels)
        self.assertIn("Sim gar", slabels)
        self.assertNotIn("Sim gar", vlabels)              # jamais mélangé au validé
        self.assertTrue(p["blocks"]["human_review_required"])   # le simulé remonte en revue


if __name__ == "__main__":
    unittest.main(verbosity=2)
