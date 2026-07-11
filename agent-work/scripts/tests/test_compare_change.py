#!/usr/bin/env python3
"""Tests des phases 8 (comparaison/contradictions) et 7 (détection de changements). Déterministe, 0 token."""
import os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
import knowledge_graph as KG
import knowledge_compare as KC
import change_detect as CD


def _g():
    return KG.KnowledgeGraph("g.json", now=lambda: "2026-07-11T00:00:00Z")


class TestComparison(unittest.TestCase):
    def test_asymmetric_coverage_is_difference_not_contradiction(self):
        g = _g()
        g.upsert_entity("axa-contrat", "A", "garantie", "Deces")
        g.upsert_entity("axa-contrat", "A", "exclusion", "Guerre")
        g.upsert_entity("axa-contrat", "B", "garantie", "Deces")   # B n'a pas d'exclusion
        rep = KC.compare_contracts(g, ["A", "B"], "axa-contrat", ["garantie", "exclusion"])
        diff = [d for d in rep["differences"] if d["category"] == "exclusion"][0]
        self.assertEqual(diff["kind"], "couverture_asymetrique")
        self.assertIn("A", diff["present"]); self.assertIn("B", diff["absent"])

    def test_contradiction_candidate_detected_conservatively(self):
        g = _g()
        g.upsert_entity("axa-contrat", "A", "garantie", "Deces par accident garanti")
        g.upsert_entity("axa-contrat", "A", "exclusion", "Deces par accident exclu en cas de guerre")
        cand = KC.contradiction_candidates(g, "A", "axa-contrat")
        self.assertEqual(len(cand), 1)
        self.assertEqual(cand[0]["nature"], "candidat_contradiction")
        self.assertTrue(cand[0]["validation_required"])

    def test_plain_difference_not_flagged(self):
        n = KC.classify_tension("Capital deces", "garantie", "Rente education", "garantie")
        self.assertEqual(n, "difference_normale")


class TestChangeDetection(unittest.TestCase):
    def test_new_document(self):
        self.assertEqual(CD.classify_change(None, "f_abc"), "nouveau_document")

    def test_identical(self):
        self.assertEqual(CD.classify_change("f_abc", "f_abc"), "identique")

    def test_minor_vs_structural(self):
        z1 = [{"label": "garanties", "start": 1, "end": 3}]
        z2 = [{"label": "garanties", "start": 1, "end": 3}]
        self.assertEqual(CD.classify_change("f_a", "f_b", z1, z2), "modification_mineure")
        z3 = [{"label": "garanties", "start": 1, "end": 3}, {"label": "exclusions", "start": 4, "end": 5}]
        self.assertEqual(CD.classify_change("f_a", "f_b", z1, z3), "modification_structurante")

    def test_targeted_invalidation_and_tasks(self):
        z1 = [{"label": "garanties", "start": 1, "end": 3}]
        z2 = [{"label": "garanties", "start": 1, "end": 3}, {"label": "exclusions", "start": 4, "end": 6}]
        changed = CD.zones_to_invalidate(z1, z2)
        self.assertEqual(len(changed), 1)                # seule la nouvelle zone est à traiter
        tasks = CD.tasks_for_change("doc1", "modification_structurante", changed)
        types = {t["type"] for t in tasks}
        self.assertIn("reexaminer_zone", types)
        self.assertIn("marquer_obsolete", types)

    def test_identical_creates_no_task(self):
        self.assertEqual(CD.tasks_for_change("doc1", "identique", []), [])   # pas de retraitement inutile


if __name__ == "__main__":
    unittest.main(verbosity=2)
