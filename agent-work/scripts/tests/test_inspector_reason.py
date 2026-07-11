#!/usr/bin/env python3
"""Tests des phases 4-5 : raisonnement mono-contrat + multi-contrats. Déterministe, 0 token."""
import os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
import knowledge_graph as KG
import inspector_case as IC
import inspector_mono as IM
import inspector_multi as IX


def _graph():
    g = KG.KnowledgeGraph("g.json", now=lambda: "2026-07-11T00:00:00Z")
    for lab, kw in [("Rente invalidite par accident (principale)", ["invalidite", "accident", "rente"]),
                    ("Capital deces", ["deces", "capital"])]:
        g.upsert_entity("axa-contrat", "Avizen", "garantie", lab, content={"keywords": kw})
    g.upsert_entity("axa-contrat", "Avizen", "exclusion", "Guerre exclue")
    g.upsert_entity("axa-contrat", "Avizen", "condition", "Taux invalidite >= 11%")
    # Avizen Pro : proche (substituable)
    g.upsert_entity("axa-contrat", "AvizenPro", "garantie", "Rente invalidite par accident", content={"keywords": ["invalidite", "accident", "rente"]})
    g.upsert_entity("axa-contrat", "AvizenPro", "exclusion", "Guerre exclue")
    # Excelium : épargne (non comparable en garanties)
    g.upsert_entity("axa-contrat", "Excelium", "garantie", "Epargne valorisee", content={"keywords": ["epargne", "capital"]})
    return g


class TestMono(unittest.TestCase):
    def test_reasoning_sheet_structure(self):
        g = _graph()
        s = IM.reasoning_sheet(g, "Avizen", "axa-contrat", ["garantie", "exclusion"])
        self.assertIn("architecture_garanties", s)
        self.assertIn("Rente invalidite par accident (principale)", s["architecture_garanties"]["principales"])
        self.assertIn("Guerre exclue", s["exclusions"])
        self.assertIn("Taux invalidite >= 11%", s["conditions"])
        self.assertEqual(s["finalite"], "à approfondir (LLM)")   # pas de L4 -> signalé

    def test_apply_case_stays_conditional(self):
        g = _graph()
        case = IC.new_case(besoins_exprimes=["se proteger en cas d'invalidite"],
                           fields={"age": IC.new_datum(40, "confirme")})
        r = IM.apply_case(g, "Avizen", case, "axa-contrat")
        self.assertIn("Rente invalidite par accident (principale)", r["clauses_potentiellement_pertinentes"])
        self.assertTrue(r["exclusions_a_verifier"])
        self.assertTrue(r["donnees_manquantes"])            # cas incomplet
        self.assertLess(r["confiance"], 1.0)
        self.assertTrue(r["validation_humaine_requise"])
        self.assertIn("conditionnelle", r["conclusion_provisoire"])

    def test_apply_case_no_match(self):
        g = _graph()
        case = IC.new_case(besoins_exprimes=["placer une epargne"])
        r = IM.apply_case(g, "Avizen", case, "axa-contrat")
        self.assertEqual(r["clauses_potentiellement_pertinentes"], [])
        self.assertIn("ne paraît pas répondre", r["conclusion_provisoire"])


class TestMulti(unittest.TestCase):
    def test_substituable_vs_non_comparable(self):
        g = _graph()
        rep = IX.compare(g, ["Avizen", "AvizenPro", "Excelium"], "axa-contrat", ["garantie", "exclusion"])
        pairs = {(p["a"], p["b"]): p["relation"] for p in rep["pairs"]}
        self.assertIn(pairs[("Avizen", "AvizenPro")], ("substituables", "doublon_probable", "partiellement_comparables"))
        # Excelium ne partage pas de garanties invalidité -> pas substituable
        self.assertNotIn(pairs[("Avizen", "Excelium")], ("substituables", "doublon_probable"))

    def test_non_comparable_when_no_shared_mechanism(self):
        g = KG.KnowledgeGraph("g2.json", now=lambda: "d")
        g.upsert_entity("axa-contrat", "A", "garantie", "X")
        g.upsert_entity("axa-contrat", "B", "option", "Y")   # aucun sous-type partagé
        rep = IX.classify_pair(g, "A", "B", "axa-contrat")
        self.assertEqual(rep["relation"], "non_comparables")

    def test_coverage_gaps(self):
        g = _graph()
        rep = IX.compare(g, ["Avizen", "Excelium"], "axa-contrat", ["exclusion", "condition"])
        gaps = {x["mecanisme"] for x in rep["coverage_gaps"]}
        self.assertIn("exclusion", gaps)   # présent Avizen, absent Excelium


if __name__ == "__main__":
    unittest.main(verbosity=2)
