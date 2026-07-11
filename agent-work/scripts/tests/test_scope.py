#!/usr/bin/env python3
"""Non-régression du contrôle de périmètre (validate_scope) sur les noms de fichiers à caractères
spéciaux/non-ASCII (accents, parenthèses, tiret cadratin).

Bug d'origine : `git diff/ls-files --name-only` QUOTE et échappe (octal) ces noms ; validate_scope ne
déquotait pas → chemins pourtant sous agent-work/ refusés à tort → commit du cycle avorté (fail-closed) →
backlog jamais poussé sur agents/proposals → knowledge-builder « no_work / backlog 0 ». Correctif : `-z`.
"""
import os, sys, subprocess, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
import validate_scope as VSC
import safety_checks as S


def _git(root, *args):
    subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)


class TestScopeAccents(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        try:
            _git(self.tmp, "init", "-q")
            _git(self.tmp, "config", "user.email", "t@t")
            _git(self.tmp, "config", "user.name", "t")
        except Exception as e:
            self.skipTest("git indisponible: %s" % e)

    def test_accented_agentwork_file_parsed_and_allowed(self):
        # fichier non suivi avec accents + parenthèses + tiret cadratin, sous agent-work/
        rel = "agent-work/knowledge/inspector/contrats/essenciel_(assurance_obsèques)_—_per.json"
        p = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write("{}")
        got = VSC.changed_files(self.tmp)
        # le chemin est retourné DÉQUOTÉ (pas de guillemets ni d'échappement octal)
        self.assertIn(rel, got)
        self.assertFalse(any(x.startswith('"') for x in got), got)
        # et il est bien couvert par l'allowlist agent-work/
        self.assertTrue(S.path_in_allowlist(rel, ["agent-work/"]))

    def test_plain_file_still_detected(self):
        rel = "agent-work/knowledge/tasks.json"
        p = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write("{}")
        self.assertIn(rel, VSC.changed_files(self.tmp))

    def test_out_of_scope_still_rejected(self):
        # un fichier produit hors agent-work/ doit rester détecté (le -z ne relâche pas la sécurité)
        rel = "ia/ai-manifest.json"
        p = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write("{}")
        got = VSC.changed_files(self.tmp)
        self.assertIn(rel, got)
        self.assertFalse(S.path_in_allowlist(rel, ["agent-work/"]))   # correctement hors périmètre


if __name__ == "__main__":
    unittest.main(verbosity=2)
