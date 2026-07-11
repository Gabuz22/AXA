#!/usr/bin/env python3
"""Test de l'exposition /ia/inspecteur/ (build déterministe, reconstructible). 0 token, en mémoire.

Vérifie que la reconstruction depuis les masters est DÉTERMINISTE (mêmes stats + même empreinte à deux
exécutions) et que les fiches portent bien des preuves. N'écrit RIEN sur disque (build_graph en mémoire).
"""
import os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "scripts"))


class TestExposureBuild(unittest.TestCase):
    def setUp(self):
        try:
            import build_inspector_ia  # noqa
            self.B = build_inspector_ia
        except Exception as e:
            self.skipTest("build_inspector_ia indisponible: %s" % e)

    def test_build_graph_deterministic(self):
        _a1, g1 = self.B.build_graph()
        _a2, g2 = self.B.build_graph()
        self.assertEqual(g1.stats(), g2.stats())
        import inspector_projection as IP
        self.assertEqual(IP.graph_fingerprint(g1), IP.graph_fingerprint(g2))   # reconstructible

    def test_graph_has_layers(self):
        _a, g = self.B.build_graph()
        st = g.stats()
        self.assertGreater(st["evidence"], 0)      # L1 preuves
        self.assertGreater(st["normalized"], 0)    # L2
        self.assertGreater(st["relations"], 0)     # L3 environnement (governed_by)

    def test_reasoning_sheet_has_preuves(self):
        _a, g = self.B.build_graph()
        subs = sorted({n.get("subject") for n in g.nodes(layer=2, domain="axa-contrat") if n.get("subject")})
        if not subs:
            self.skipTest("aucun sujet (masters absents dans cet environnement)")
        import inspector_mono as IM
        sheet = IM.reasoning_sheet(g, subs[0], "axa-contrat")
        self.assertIn("preuves", sheet)
        # au moins un contrat doit avoir des preuves sourcées (document+page)
        any_proof = any(IM.reasoning_sheet(g, s, "axa-contrat")["preuves"] for s in subs[:3])
        self.assertTrue(any_proof)


if __name__ == "__main__":
    unittest.main(verbosity=2)
