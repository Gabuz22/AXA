#!/usr/bin/env python3
"""Tests du moteur d'AVIS D'INSPECTEUR (mission Fable, cycle « cerveau métier »). 0 token."""
import os, sys, json, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import inspector_case as IC
import inspector_advice as IA
import claude_enrichment as CE


def _ctx():
    try:
        import build_inspector_ia as B
        g = B.build_graph()[1]
    except Exception as e:
        raise unittest.SkipTest("masters indisponibles: %s" % e)
    metier = CE.load_metier(REPO)
    if not metier or "priorites_risques" not in metier:
        raise unittest.SkipTest("metier_inspecteur étendu absent")
    return g, metier


def _case(**kw):
    base = dict(fields={"age": IC.new_datum(42, "confirme"),
                        "statut_professionnel": IC.new_datum("travailleur non salarie", "declare"),
                        "situation_familiale": IC.new_datum("marie, 2 enfants", "declare"),
                        "emprunts": IC.new_datum("credit immobilier", "declare")},
                objectifs=["proteger la famille"])
    base.update(kw)
    return IC.new_case(**base)


class TestAdvice(unittest.TestCase):
    def test_debt_first_priorities(self):
        g, m = _ctx()
        avis = IA.advise(_case(), g, m)
        self.assertEqual(avis["risques_priorises"][0], "emprunt")          # les dettes d'abord
        self.assertIn("tns", avis["profil"]["flags"])
        self.assertIn("arret_travail_itt", avis["risques_priorises"][:4])  # TNS -> ITT prioritaire

    def test_existing_contract_covers_risk(self):
        g, m = _ctx()
        avis = IA.advise(_case(contrats_existants=["Excelium"]), g, m)
        a = avis["audit_existant"]["par_risque"]["deces_protection_famille"]
        self.assertEqual(a["statut"], "couvert_a_verifier")
        self.assertTrue(a["couvert_par"])
        self.assertNotIn("deces_protection_famille", avis["trous_de_couverture_potentiels"])

    def test_doublon_detected(self):
        g, m = _ctx()
        avis = IA.advise(_case(contrats_existants=["Avizen", "Avizen Pro"]), g, m)
        self.assertIn("deces_protection_famille", avis["doublons_potentiels"])

    def test_trou_detected_and_plan_has_why_questions_pieges(self):
        g, m = _ctx()
        avis = IA.advise(_case(), g, m)
        self.assertIn("emprunt", avis["trous_de_couverture_potentiels"])   # crédit sans emprunteur
        e1 = avis["plan_action"][0]
        self.assertTrue(e1["pourquoi"])
        self.assertTrue(e1["questions_a_poser"])
        self.assertTrue(e1["pieges_frequents"])                            # quotités, psy/dos...

    def test_conditional_and_no_invented_figures(self):
        g, m = _ctx()
        avis = IA.advise(_case(), g, m)
        self.assertTrue(avis["validation_humaine_requise"])
        self.assertEqual(avis["origin_heuristiques"], "simulation_assistee_par_claude")
        blob = json.dumps(avis, ensure_ascii=False)
        self.assertNotIn("€", blob)                                        # aucun montant inventé

    def test_hypotheses_never_drive_profile(self):
        g, m = _ctx()
        c = IC.new_case(fields={"statut_professionnel": IC.new_datum("travailleur non salarie", "hypothese")})
        avis = IA.advise(c, g, m)
        self.assertNotIn("tns", avis["profil"]["flags"])                   # hypothèse != fait


if __name__ == "__main__":
    unittest.main(verbosity=2)
