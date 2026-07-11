#!/usr/bin/env python3
"""Tests de la phase 3 : couverture SÉMANTIQUE (par catégorie) + taux + profondeur L1-L4 + explicabilité.

Déterministe, 0 token. Vérifie : présence par catégorie, taux (preuve/non-relié/incertitude/
contradiction), comptes de profondeur, et surtout que la plateforme EXPLIQUE pourquoi un axe est faible
et quel travail l'améliorerait.
"""
import os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
import knowledge_graph as KG
import coverage_model as CM


def _g():
    return KG.KnowledgeGraph("g.json", now=lambda: "2026-07-11T00:00:00Z")


EXPECTED = ["garantie", "exclusion", "definition", "declencheur"]


class TestSemanticCoverage(unittest.TestCase):
    def test_category_presence(self):
        g = _g()
        g.upsert_entity("axa-contrat", "C1", "garantie", "Capital")
        g.upsert_entity("axa-contrat", "C1", "exclusion", "Guerre")
        pres = CM.category_presence(g, "C1", "axa-contrat", EXPECTED)
        self.assertTrue(pres["garantie"]); self.assertTrue(pres["exclusion"])
        self.assertFalse(pres["definition"]); self.assertFalse(pres["declencheur"])

    def test_quality_rates(self):
        g = _g()
        g.add_evidence("axa-contrat", "C1", "n.pdf", 5, "cit", "a")
        e1, _ = g.upsert_entity("axa-contrat", "C1", "garantie", "A",
                                evidence_ids=[], confidence=0.9)
        e2, _ = g.upsert_entity("axa-contrat", "C1", "exclusion", "B", confidence=0.3)  # faible confiance
        r = CM.quality_rates(g, "C1", "axa-contrat")
        self.assertEqual(r["n_entities"], 2)
        self.assertEqual(r["unrelated"], 1.0)          # aucune relation
        self.assertGreater(r["uncertainty"], 0.0)      # une entité < 0.5

    def test_depth_counts(self):
        g = _g()
        g.add_evidence("axa-contrat", "C1", "n.pdf", 5, "cit", "a")
        a, _ = g.upsert_entity("axa-contrat", "C1", "garantie", "A")
        b, _ = g.upsert_entity("axa-contrat", "C1", "exclusion", "B")
        g.add_relation("excludes", a["id"], b["id"])
        g.upsert_understanding(a["id"], "role", "explication")
        dc = CM.depth_counts(g, "C1", "axa-contrat")
        self.assertEqual(dc["L1"], 1); self.assertEqual(dc["L2"], 2)
        self.assertGreaterEqual(dc["L3"], 1); self.assertEqual(dc["L4"], 1)


class TestExplainability(unittest.TestCase):
    def test_explain_weak_axes_and_missing_categories(self):
        g = _g()
        g.add_evidence("axa-contrat", "C1", "n.pdf", 5, "cit", "a")
        g.upsert_entity("axa-contrat", "C1", "garantie", "Capital")   # isolée, sans explication
        rep = CM.explain(g, "C1", "axa-contrat", EXPECTED)
        axes = {e["axis"] for e in rep["explanations"]}
        self.assertIn("relations", axes)               # isolée -> relier
        self.assertIn("understanding", axes)           # non expliquée -> expliquer
        self.assertIn("semantic", axes)                # catégories manquantes -> extraire
        # chaque explication porte un travail recommandé
        for e in rep["explanations"]:
            self.assertIn("recommended_task", e)
            self.assertIn("why", e)
        self.assertLess(rep["semantic_coverage"], 1.0)

    def test_full_subject_has_no_weak_axis(self):
        g = _g()
        g.add_evidence("axa-contrat", "C1", "n.pdf", 5, "cit", "a")
        cats = {}
        for sub in EXPECTED:
            e, _ = g.upsert_entity("axa-contrat", "C1", sub, "L-" + sub, evidence_ids=[], confidence=0.8)
            cats[sub] = e
        # relie et explique chaque entité + un ancrage environnement
        ids = [cats[s]["id"] for s in EXPECTED]
        for i in range(len(ids)):
            g.add_relation("comparable_to", ids[i], ids[(i + 1) % len(ids)])
            g.upsert_understanding(ids[i], "role", "expl")
        env, _ = g.upsert_entity("reglementation", "C1", "concept_reglementaire", "Invalidite")
        g.add_relation("governed_by", ids[0], env["id"])
        rep = CM.explain(g, "C1", "axa-contrat", EXPECTED)
        self.assertEqual(rep["semantic_coverage"], 1.0)
        self.assertEqual(rep["weak_axes"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
