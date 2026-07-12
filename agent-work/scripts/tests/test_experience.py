#!/usr/bin/env python3
"""Tests de la BIBLIOTHÈQUE D'EXPÉRIENCE (mission V5 — l'entraînement de l'inspecteur). 0 token."""
import os, sys, unittest

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
    m = CE.load_metier(REPO)
    if not m or "_experience" not in m:
        raise unittest.SkipTest("experience_library absente")
    return g, m


class TestExperience(unittest.TestCase):
    def test_solo_demotes_death(self):
        g, m = _ctx()
        c = IC.new_case(fields={"age": IC.new_datum(26, "confirme"),
                                "situation_familiale": IC.new_datum("celibataire", "declare")},
                        besoins_exprimes=["me proteger en cas d accident ou d arret de travail",
                                          "proteger la famille en cas de deces"])
        avis = IA.advise(c, g, m)
        self.assertIn("solo", avis["profil"]["flags"])
        # le décès (pourtant demandé) est rétrogradé en fin de liste : leçon exp_003
        self.assertEqual(avis["risques_priorises"][-1] in ("deces_protection_famille", "education_enfants"), True)
        self.assertNotEqual(avis["risques_priorises"][0], "deces_protection_famille")

    def test_lessons_surface_for_matching_profile(self):
        g, m = _ctx()
        med = IC.new_case(fields={"statut_professionnel": IC.new_datum("medecin liberal, travailleur non salarie", "declare")})
        avis = IA.advise(med, g, m)
        lecons = " ".join(l["lecon"] for l in avis["retours_experience"]["lecons"])
        self.assertIn("CARENCE", lecons)                     # leçon du dossier médecin
        self.assertTrue(all(l["origine"] == "simulation_assistee_par_claude"
                            for l in avis["retours_experience"]["lecons"]))

    def test_lessons_do_not_leak_to_wrong_profile(self):
        g, m = _ctx()
        solo = IC.new_case(fields={"situation_familiale": IC.new_datum("celibataire", "declare")})
        avis = IA.advise(solo, g, m)
        lecons = " ".join(l["lecon"] for l in avis["retours_experience"]["lecons"])
        self.assertNotIn("RECOMPOSÉE", lecons)               # leçon couple+enfants absente pour un solo

    def test_library_schema_generic(self):
        _g, m = _ctx()
        lib = m["_experience"]
        for d in lib["dossiers"]:
            self.assertIn("situation", d)
            self.assertIn("lecons", d)
            for le in d["lecons"]:
                self.assertIn("si", le)
                self.assertIn("lecon", le)
                self.assertIn(le.get("type"), ("piege", "question_a_poser", "strategie", "arbitrage", "risque_cache"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
