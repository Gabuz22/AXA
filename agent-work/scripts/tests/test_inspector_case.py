#!/usr/bin/env python3
"""Tests des phases 2-3 : modèle de cas client + décomposition du besoin. Déterministe, 0 token."""
import os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
import knowledge_graph as KG
import inspector_case as IC
import inspector_needs as IN


class TestCaseModel(unittest.TestCase):
    def test_status_required_and_facts_exclude_hypotheses(self):
        c = IC.new_case(fields={
            "age": IC.new_datum(45, "confirme"),
            "revenus": IC.new_datum(50000, "hypothese"),
            "profession": IC.new_datum("artisan", "declare"),
        }, objectifs=["proteger revenus"])
        ok, errs = IC.validate_case(c)
        self.assertTrue(ok, errs)
        f = IC.facts(c)
        self.assertIn("age", f); self.assertIn("profession", f)
        self.assertNotIn("revenus", f)                 # hypothèse -> jamais un fait
        self.assertIn("revenus", IC.assumptions(c))

    def test_invalid_status_rejected(self):
        c = IC.new_case()
        c["fields"]["x"] = {"value": 1, "status": "certain"}   # statut inconnu
        ok, errs = IC.validate_case(c)
        self.assertFalse(ok)

    def test_new_datum_rejects_bad_status(self):
        with self.assertRaises(ValueError):
            IC.new_datum(1, "vrai")

    def test_completeness(self):
        c = IC.new_case(fields={"age": IC.new_datum(40, "confirme")}, objectifs=["x"])
        comp = IC.completeness(c)
        self.assertLess(comp["score"], 1.0)
        self.assertIn("statut_professionnel", comp["missing"])


class TestNeedDecomposition(unittest.TestCase):
    def _graph(self):
        g = KG.KnowledgeGraph("g.json", now=lambda: "2026-07-11T00:00:00Z")
        g.upsert_entity("axa-contrat", "Avizen", "garantie", "Rente invalidite par accident",
                        content={"keywords": ["invalidite", "accident", "rente"]})
        g.upsert_entity("axa-contrat", "Avizen", "exclusion", "Guerre exclue")
        g.upsert_entity("axa-contrat", "Avizen", "condition", "Taux invalidite >= 11%")
        g.upsert_entity("axa-contrat", "Excelium", "garantie", "Epargne valorisee",
                        content={"keywords": ["epargne", "capital", "valorisation"]})
        return g

    def test_maps_need_to_contracts_and_data(self):
        g = self._graph()
        case = IC.new_case(besoins_exprimes=["se proteger en cas d'invalidite"],
                           fields={"age": IC.new_datum(40, "confirme")})
        tree = IN.decompose(case, g, "axa-contrat")
        self.assertTrue(tree["case_valid"])
        b = tree["besoins"][0]
        self.assertIn("Avizen", b["contrats_possibles"])     # besoin invalidité -> Avizen
        self.assertNotIn("Excelium", b["contrats_possibles"]) # épargne non pertinent
        # données à vérifier = conditions/exclusions du contrat candidat
        self.assertTrue(any(d["type"] in ("condition", "exclusion") for d in b["donnees_necessaires"]["Avizen"]))

    def test_separates_expressed_and_deduced(self):
        g = self._graph()
        case = IC.new_case(besoins_exprimes=["invalidite"], besoins_deduits=["epargne"])
        tree = IN.decompose(case, g, "axa-contrat")
        origins = {b["besoin"]: b["origine"] for b in tree["besoins"]}
        self.assertEqual(origins["invalidite"], "exprime")
        self.assertEqual(origins["epargne"], "deduit")

    def test_incomplete_case_flags_missing_and_stays_conditional(self):
        g = self._graph()
        case = IC.new_case(besoins_exprimes=["invalidite"])
        tree = IN.decompose(case, g, "axa-contrat")
        self.assertTrue(tree["informations_manquantes"])     # cas incomplet
        self.assertIn("conditionnelle", tree["avertissement"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
