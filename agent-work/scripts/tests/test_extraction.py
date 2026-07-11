#!/usr/bin/env python3
"""Tests de la porte déterministe de l'agent Extraction documentaire LLM.

Démontre : proposition correcte acceptée · doublon rejeté · mauvaise page rejetée · citation absente
rejetée · citation introuvable rejetée · source absente rejetée · hors catégorie rejetée.
"""
import os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, SCRIPTS)

from agents import extraction_llm as EX
import validate_proposal as VP

PAGE_TEXTS = {5: "La garantie deces verse un capital de 10000 euros en cas de deces accidentel du souscripteur."}
CATS = EX.CATEGORIES


def item(**over):
    it = {"categorie": "garanties", "texte": "capital deces accidentel",
          "page": 5, "citation": "verse un capital de 10000 euros", "confidence": 0.8}
    it.update(over)
    return it


class TestExtractionGate(unittest.TestCase):
    def test_correct_accepted(self):
        ok, why = EX.check_extraction(item(), PAGE_TEXTS, CATS, set())
        self.assertTrue(ok, why)

    def test_duplicate_rejected(self):
        existing = {EX._norm("verse un capital de 10000 euros")}
        ok, why = EX.check_extraction(item(), PAGE_TEXTS, CATS, existing)
        self.assertFalse(ok); self.assertEqual(why, "doublon")

    def test_wrong_page_rejected(self):
        ok, why = EX.check_extraction(item(page=6), PAGE_TEXTS, CATS, set())
        self.assertFalse(ok); self.assertEqual(why, "page_invalide")

    def test_absent_citation_rejected(self):
        ok, why = EX.check_extraction(item(citation=""), PAGE_TEXTS, CATS, set())
        self.assertFalse(ok); self.assertEqual(why, "citation_absente")

    def test_hallucinated_citation_rejected(self):
        ok, why = EX.check_extraction(item(citation="rente invalidite a vie totale garantie"), PAGE_TEXTS, CATS, set())
        self.assertFalse(ok); self.assertEqual(why, "citation_introuvable_sur_page")

    def test_out_of_category_rejected(self):
        ok, why = EX.check_extraction(item(categorie="banane"), PAGE_TEXTS, CATS, set())
        self.assertFalse(ok); self.assertEqual(why, "categorie_hors_liste")

    def test_absent_source_rejected_by_schema(self):
        # Une proposition d'extraction sans source (ni excerpt ni document) est rejetée par le validateur.
        prop = {
            "proposal_id": "extraction_llm_x", "agent_id": "extraction-llm", "run_id": "r",
            "created_at": "2026-01-01T00:00:00Z", "status": "pending_review",
            "task": {"id": "t", "type": "extraction", "scope": ""},
            "target": {"contract": "avizen", "file": EX.MASTER_A, "section": "garanties"},
            "source": {"type": "pdf"},  # ni document ni excerpt
            "proposed_change": {"operation": "add", "payload": {}},
            "reasoning_summary": "x", "confidence": 0.8, "validation_required": True,
            "automatic_checks": {"schema_valid": True, "source_resolves": False, "duplicate_detected": False, "scope_allowed": True},
        }
        ok, errs = VP.validate(prop)
        self.assertFalse(ok)
        self.assertTrue(any("source" in e for e in errs))


class TestConfidenceAndLoad(unittest.TestCase):
    def test_confidence_never_one(self):
        c, reason = EX.realistic_confidence({"confidence": 1.0, "citation": "x" * 60})
        self.assertLessEqual(c, EX.CONF_CAP)
        self.assertLess(c, 1.0)
        self.assertIn("Confiance", reason)

    def test_confidence_penalty_proximity(self):
        c_far, _ = EX.realistic_confidence({"confidence": 0.9, "citation": "x" * 60})
        c_near, _ = EX.realistic_confidence({"confidence": 0.9, "citation": "x" * 60, "closest_existing": "deja la"})
        self.assertLess(c_near, c_far)

    def test_confidence_floor(self):
        c, _ = EX.realistic_confidence({"confidence": 0.1, "citation": "ab"})
        self.assertGreaterEqual(c, 0.30)

    def test_adaptive_zone_count(self):
        self.assertEqual(EX.adaptive_zone_count(0), 0)
        self.assertEqual(EX.adaptive_zone_count(3), 1)
        self.assertEqual(EX.adaptive_zone_count(10), 2)
        self.assertEqual(EX.adaptive_zone_count(25), 3)
        self.assertEqual(EX.adaptive_zone_count(50), 4)
        self.assertEqual(EX.adaptive_zone_count(200), 5)

    def test_enum_cleaning(self):
        self.assertEqual(EX._clean_enum("Critique", EX.IMPORTANCE), "critique")
        self.assertEqual(EX._clean_enum("inventé", EX.IMPORTANCE), "")   # jamais inventé
        self.assertEqual(EX._review_cost_for("critique"), "2 min")

    def test_target_path_deterministic(self):
        tp = EX._target_path("Avizen", "garanties")
        self.assertIn("Avizen", tp)
        self.assertIn("garanties", tp)


if __name__ == "__main__":
    unittest.main(verbosity=2)
