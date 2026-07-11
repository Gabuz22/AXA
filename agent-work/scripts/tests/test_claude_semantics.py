#!/usr/bin/env python3
"""Tests de la couche sémantique/métier raisonnée par Claude (mission Inspecteur Fable).

Vérifie : ingestion idempotente et résolution des libellés (sur les VRAIS masters), étiquetage strict
(origine simulation_assistee_par_claude, statut simulated_claude, jamais dans validated_knowledge),
fiche enrichie (finalité/confusions/articulations étiquetées), et PRÉCISION du matching par matrice de
risques (mots-clés en frontières de mots, sous-ensemble de mots requis).
"""
import os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import knowledge_graph as KG
import claude_enrichment as CE
import inspector_case as IC
import inspector_needs as INn


def _real_graph():
    try:
        import build_inspector_ia as B
        return B.build_graph()[1]
    except Exception as e:
        raise unittest.SkipTest("masters indisponibles: %s" % e)


class TestIngestion(unittest.TestCase):
    def test_idempotent_and_all_labels_resolved(self):
        g = _real_graph()
        st = CE.ingest_from_repo(g, REPO)          # rerun sur graphe déjà enrichi
        self.assertEqual(st["relations_internes"] + st["relations_inter"], 0)   # idempotent
        self.assertEqual(st["unresolved"], [])     # tous les libellés existent dans les masters

    def test_everything_labeled_never_validated(self):
        g = _real_graph()
        import knowledge_status as KS
        for n in g.data["nodes"].values():
            if n.get("provenance_agent") == CE.ORIGIN:
                self.assertEqual(KS.node_status(g, n), "simulated_claude")
                self.assertFalse(KS.is_exposable_as_truth(KS.node_status(g, n)))
        for e in g.data["edges"].values():
            if e.get("provenance_agent") == CE.ORIGIN and e.get("type") != "explains":
                self.assertTrue(e.get("validation_required"))

    def test_fiche_enriched_and_safe(self):
        g = _real_graph()
        import inspector_mono as IM
        s = IM.reasoning_sheet(g, "Masterlife CREDIT", "axa-contrat")
        self.assertIsInstance(s["finalite"], dict)
        self.assertEqual(s["finalite"]["origine"], CE.ORIGIN)
        self.assertTrue(s["finalite"]["validation_required"])
        self.assertTrue(s["articulations"])
        self.assertTrue(all(a["statut"] == "simulated_claude" for a in s["articulations"]))
        # aucun élément simulé dans le bloc validé
        v = {x["label"] for x in s["validation"]["blocks"]["validated_knowledge"]}
        sim = {x.get("label") for x in s["validation"]["blocks"]["simulated_claude"] if "label" in x}
        self.assertFalse(v & sim)


class TestRiskMatrixPrecision(unittest.TestCase):
    def setUp(self):
        self.metier = CE.load_metier(REPO)
        if not self.metier:
            self.skipTest("metier_inspecteur.json absent")

    def test_word_boundary_no_substring(self):
        # « anticiper » ne doit PAS matcher le mot-clé « per » (frontières de mots)
        hits = INn.match_risks("anticiper la dependance", self.metier)
        self.assertEqual([r for r, _ in hits], ["dependance"])

    def test_multiword_requires_all_words(self):
        # « travail » seul ne suffit pas pour « arret de travail »
        hits = INn.match_risks("le travail de la vigne", self.metier)
        self.assertNotIn("arret_travail_itt", [r for r, _ in hits])
        hits2 = INn.match_risks("arret de travail prolonge", self.metier)
        self.assertIn("arret_travail_itt", [r for r, _ in hits2])

    def test_precision_on_real_graph(self):
        g = _real_graph()
        t = INn.decompose(IC.new_case(besoins_exprimes=["preparer la retraite"]), g, "axa-contrat", metier=self.metier)
        b = t["besoins"][0]
        self.assertEqual(b["risques_identifies"], ["retraite_revenu"])
        self.assertEqual(len(b["contrats_possibles"]), 2)          # PER + assurance vie (pas 8 comme en lexical)
        self.assertTrue(b["questions_a_poser"])                    # questions d'inspecteur fournies


if __name__ == "__main__":
    unittest.main(verbosity=2)
