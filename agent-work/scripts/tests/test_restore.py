#!/usr/bin/env python3
"""Non-régression : la préparation du run restaure l'ÉTAT persistant depuis agents/proposals mais
exécute TOUJOURS le code de main. Prouve le correctif du bug « ancien code réexécuté »."""
import os, sys, shutil, subprocess, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, SCRIPTS)
import restore_state as R


class TestAllowlist(unittest.TestCase):
    def test_code_never_in_persistent(self):
        for bad in ("agent-work/scripts", "agent-work/config", "agent-work/schemas", "agent-work/README.md"):
            self.assertNotIn(bad, R.PERSISTENT, bad)
            self.assertTrue(any(bad == c or bad.startswith(c) for c in R.CODE_FROM_MAIN), bad)

    def test_state_in_persistent(self):
        for good in ("agent-work/extraction/pending", "agent-work/extraction/memory.json",
                     "agent-work/extraction/production_history.json", "agent-work/coordinator",
                     "agent-work/runs/manifests"):
            self.assertIn(good, R.PERSISTENT, good)


@unittest.skipUnless(shutil.which("git"), "git requis")
class TestRestoreSimulation(unittest.TestCase):
    def _git(self, *a):
        return subprocess.run(["git"] + list(a), cwd=self.d, capture_output=True, text=True)

    def _write(self, rel, content):
        p = os.path.join(self.d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self._git("init", "-q")
        self._git("config", "user.email", "t@t"); self._git("config", "user.name", "t")
        self._git("checkout", "-q", "-b", "main")
        # main : NOUVEAU code (marqueur v2.4.1) + dossiers d'état vides
        self._write("agent-work/scripts/agents/extraction_llm.py", 'AGENT_CODE_VERSION = "2.4.1"\n# NOUVEAU CODE\n')
        self._write("agent-work/config/agents.json", '{"v":"new"}\n')
        self._write("agent-work/extraction/pending/.gitkeep", "")
        self._git("add", "-A"); self._git("commit", "-qm", "main new code")
        # branche agents/proposals : ANCIEN code + état accumulé
        self._git("checkout", "-q", "-b", "agents/proposals")
        self._write("agent-work/scripts/agents/extraction_llm.py", 'AGENT_CODE_VERSION = "2.3.0"\n# VIEUX CODE\n')
        self._write("agent-work/config/agents.json", '{"v":"old"}\n')
        self._write("agent-work/extraction/memory.json", '{"old_state":true}\n')
        self._write("agent-work/extraction/pending/p1.json", '{"proposal":"accumulée"}\n')
        self._git("add", "-A"); self._git("commit", "-qm", "branch old code + state")
        # simule le workflow : on repart de main (code frais)
        self._git("checkout", "-q", "main")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_restore_keeps_main_code_but_restores_state(self):
        env = dict(os.environ, MAIN_REF="main", AGENT_BRANCH_REF="agents/proposals")
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "restore_state.py")],
                           cwd=self.d, env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        code = open(os.path.join(self.d, "agent-work/scripts/agents/extraction_llm.py"), encoding="utf-8").read()
        cfg = open(os.path.join(self.d, "agent-work/config/agents.json"), encoding="utf-8").read()
        # 3. le code exécuté reste celui de main
        self.assertIn('2.4.1', code); self.assertIn("NOUVEAU", code)
        self.assertIn('"new"', cfg)
        # 2. l'état (mémoire + propositions) est restauré depuis la branche
        self.assertTrue(os.path.isfile(os.path.join(self.d, "agent-work/extraction/memory.json")))
        self.assertIn("old_state", open(os.path.join(self.d, "agent-work/extraction/memory.json"), encoding="utf-8").read())
        self.assertTrue(os.path.isfile(os.path.join(self.d, "agent-work/extraction/pending/p1.json")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
