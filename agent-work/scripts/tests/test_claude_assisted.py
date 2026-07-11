#!/usr/bin/env python3
"""Tests de la phase 14 : provider 'claude-assisted-test' (simulation_assistee_par_claude).

Vérifie : le provider REJOUE une réponse enregistrée (indexée par hash de prompt) ; il ÉCHOUE proprement
si aucune réponse n'est enregistrée ; il est INÉLIGIBLE sans la clé AXA_CLAUDE_ASSISTED (donc jamais en
production). Aucun réseau.
"""
import os, sys, json, hashlib, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
from providers import adapters
import provider_router as PR
import safety_checks as S


def _h(user):
    return "h_" + hashlib.sha256(user.encode("utf-8")).hexdigest()[:20]


class TestClaudeAssistedProvider(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.join(tempfile.mkdtemp(), "responses.json")
        os.environ["AXA_CLAUDE_RESPONSES"] = self.tmp

    def tearDown(self):
        os.environ.pop("AXA_CLAUDE_RESPONSES", None)

    def test_replays_recorded_response(self):
        prompt = "Explique la garantie X."
        with open(self.tmp, "w", encoding="utf-8") as f:
            json.dump({"responses": {_h(prompt): {"aspect": "role", "explanation": "ok"}}}, f)
        messages = [{"role": "system", "content": "..."}, {"role": "user", "content": prompt}]
        text, tin, tout = adapters.claude_assisted_chat({}, "k", None, messages, 500, 30)
        self.assertIn("explanation", text)
        self.assertIn("ok", text)
        self.assertGreater(tin, 0)

    def test_raises_when_absent(self):
        with open(self.tmp, "w", encoding="utf-8") as f:
            json.dump({"responses": {}}, f)
        messages = [{"role": "user", "content": "prompt sans réponse"}]
        with self.assertRaises(adapters.ProviderError):
            adapters.claude_assisted_chat({}, "k", None, messages, 500, 30)

    def test_registered_in_styles(self):
        self.assertIn("claude_assisted", adapters.STYLES)


class TestNeverInProduction(unittest.TestCase):
    def test_ineligible_without_key(self):
        os.environ.pop("AXA_CLAUDE_ASSISTED", None)
        cfg = S.load_providers_config()
        if "claude-assisted-test" not in cfg.get("providers", {}):
            self.skipTest("provider claude-assisted-test absent de la config")
        r = PR.ProviderRouter(cfg, S.load_policies())
        rep = {x["provider"]: x for x in r.autodetect()}["claude-assisted-test"]
        self.assertFalse(rep["eligible"])            # jamais éligible sans la clé -> jamais en production

    def test_eligible_only_with_key(self):
        cfg = S.load_providers_config()
        if "claude-assisted-test" not in cfg.get("providers", {}):
            self.skipTest("provider absent")
        os.environ["AXA_CLAUDE_ASSISTED"] = "1"
        try:
            r = PR.ProviderRouter(cfg, S.load_policies())
            rep = {x["provider"]: x for x in r.autodetect()}["claude-assisted-test"]
            self.assertTrue(rep["eligible"])         # éligible seulement dans le harnais (clé posée)
        finally:
            os.environ.pop("AXA_CLAUDE_ASSISTED", None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
