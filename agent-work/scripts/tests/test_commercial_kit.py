#!/usr/bin/env python3
"""Tests du KIT DE RENDEZ-VOUS (mission V4, axe assistant commercial). 0 token."""
import os, sys, json, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import inspector_case as IC
import claude_enrichment as CE


def _ctx():
    try:
        import build_inspector_ia as B
        g = B.build_graph()[1]
    except Exception as e:
        raise unittest.SkipTest("masters indisponibles: %s" % e)
    m = CE.load_metier(REPO)
    if not m or "priorites_risques" not in m:
        raise unittest.SkipTest("metier étendu absent")
    return g, m


def _case():
    return IC.new_case(fields={"age": IC.new_datum(42, "confirme"),
                               "statut_professionnel": IC.new_datum("travailleur non salarie", "declare"),
                               "situation_familiale": IC.new_datum("marie, 2 enfants", "declare"),
                               "emprunts": IC.new_datum("credit immobilier", "declare")},
                       objectifs=["proteger la famille"], contrats_existants=["Excelium"])


class TestKit(unittest.TestCase):
    def test_kit_complete_and_ordered(self):
        g, m = _ctx()
        import commercial_kit as CK
        kit = CK.build_kit(_case(), g, m)
        self.assertEqual(kit["preparation"]["contrats_a_presenter"][0], "Masterlife CREDIT")   # dettes d'abord
        self.assertGreaterEqual(len(kit["questions_decouverte"]), 5)
        self.assertGreaterEqual(len(kit["argumentaires"]), 2)
        self.assertEqual(len(kit["plan_entretien"]), 6)
        self.assertTrue(kit["validation_humaine_requise"])

    def test_argumentaires_grounded_and_labeled(self):
        g, m = _ctx()
        import commercial_kit as CK
        kit = CK.build_kit(_case(), g, m)
        a0 = kit["argumentaires"][0]
        self.assertTrue(a0["accroche_metier"])                              # finalité du graphe
        self.assertTrue(a0["pieges_a_ne_pas_oublier"])                      # pièges métier
        self.assertEqual(a0["origine_interpretations"], "simulation_assistee_par_claude")

    def test_no_invented_figures_and_mentions(self):
        g, m = _ctx()
        import commercial_kit as CK
        kit = CK.build_kit(_case(), g, m)
        blob = json.dumps(kit, ensure_ascii=False)
        self.assertNotIn("€", blob)                                         # aucun montant inventé
        self.assertIn("notices", kit["compte_rendu_type"]["mentions"])      # mention prudentielle

    def test_markdown_renders_for_human(self):
        g, m = _ctx()
        import commercial_kit as CK
        md = CK.to_markdown(CK.build_kit(_case(), g, m))
        for section in ("Fiche de préparation", "Plan d'entretien", "Questions de découverte",
                        "Argumentaires", "compte-rendu", "Réserves"):
            self.assertIn(section, md)
        self.assertIn("[À COMPLÉTER", md)                                   # placeholders explicites


if __name__ == "__main__":
    unittest.main(verbosity=2)
