#!/usr/bin/env python3
"""Agent Tests — DÉTERMINISTE par défaut (aucun LLM requis).

Relance le harness de routage existant (via build_ia.py), mesure précision/rappel/périmètre/source/
statut/faux positifs, compare au run précédent et produit un incident si une métrique baisse. Il exécute
la banque de tests déjà présente (ia/tests.json) et n'invente PAS de nouveaux tests sans modèle.
Un chemin LLM (génération de nouveaux tests) n'est activé qu'avec un fournisseur (ou --mock).
"""
import os, re, json, subprocess
import safety_checks as S
from agents import base

HISTORY = "agent-work/tests/metrics_history.json"
METRIC_KEYS = ["contrats_precision", "contrats_recall", "perimetre", "source", "statut", "faux_positifs", "n_tests"]


def _run(cmd, timeout=300):
    r = subprocess.run(cmd, cwd=S.REPO_ROOT, capture_output=True, timeout=timeout)
    return r.returncode, (r.stdout or b"").decode("utf-8", "replace"), (r.stderr or b"").decode("utf-8", "replace")


def _parse_metrics(out):
    m = re.search(r"routage\s*—\s*(\d+)\s*tests\s*:\s*contrats\s*P=(\d+)%\s*R=(\d+)%\s*\|\s*"
                  r"p[ée]rim[èe]tre\s*(\d+)%\s*\|\s*source\s*off\.\s*(\d+)%\s*\|\s*statut\s*(\d+)%\s*\|\s*"
                  r"faux positifs contrats\s*:\s*(\d+)", out, re.S)
    if not m:
        return None
    return {"n_tests": int(m.group(1)), "contrats_precision": int(m.group(2)), "contrats_recall": int(m.group(3)),
            "perimetre": int(m.group(4)), "source": int(m.group(5)), "statut": int(m.group(6)), "faux_positifs": int(m.group(7))}


def _example_tests(ctx):
    c = S.load_json(base.repo_path("ia/contrats.json"), default={})
    names = [x.get("nom") for x in c.get("contrats", []) if x.get("nom")]
    a = names[0] if names else "MasterLife"
    spec = {"question": "le deces accidentel n'est-il pas exclu par %s ?" % a, "famille": "negation",
            "contrats_obligatoires": [a], "statut_conclusion_attendu": "verification_notice_requise"}
    return [base.new_proposal(ctx, task_type="adversarial-test", target={"file": "ia/tests.json", "section": "negation"},
            source={"type": "derived", "document": "ia/contrats.json", "excerpt": spec["question"]},
            change={"operation": "test", "payload": spec},
            reasoning="Exemple de nouveau test (mock). La generation reelle de nouveaux tests exige un LLM configure.",
            confidence=0.75, validation_required=True, origin="example_fixture")]


def run(ctx):
    ctx.self_wrote = True
    rc, out, err = _run(["python", "scripts/build_ia.py"])
    _run(["git", "checkout", "--", "ia"])  # ne jamais modifier les sorties publiées
    metrics = _parse_metrics(out)
    n_bank = len(S.load_json(base.repo_path("ia/tests.json"), default={}).get("tests", [])
                 or S.load_json(base.repo_path("ia/tests.json"), default={}).get("items", []))

    hist = S.load_json(base.repo_path(HISTORY), default={"runs": []})
    prev = hist["runs"][-1]["metrics"] if hist.get("runs") else None

    proposals, regressions = [], []
    if metrics and prev:
        for k in ["contrats_precision", "contrats_recall", "perimetre", "source", "statut"]:
            if metrics.get(k, 0) < prev.get(k, 0):
                regressions.append("%s: %d%% -> %d%%" % (k, prev[k], metrics[k]))
        if metrics.get("faux_positifs", 0) > prev.get("faux_positifs", 0):
            regressions.append("faux_positifs: %d -> %d" % (prev["faux_positifs"], metrics["faux_positifs"]))

    if regressions:
        p = base.new_proposal(
            ctx, task_type="routing-metrics", target={"file": "ia/qualite-routage.html", "section": "regression"},
            source={"type": "repo", "document": "scripts/build_ia.py (harness)", "excerpt": "; ".join(regressions)},
            change={"operation": "report", "payload": {"regressions": regressions, "current": metrics, "previous": prev}},
            reasoning="Régression détectée sur les métriques de routage : %s. Moteur non modifié." % "; ".join(regressions),
            confidence=0.99, validation_required=True, origin="deterministic",
            risks=["régression qualité ; investigation humaine requise"])
        proposals.append(p)
        if not ctx.dry_run:
            S.write_json(base.repo_path(os.path.join("agent-work/tests/pending", p["proposal_id"] + ".json")), p)

    # Historique de métriques (persisté hors dry-run).
    if metrics and not ctx.dry_run:
        hist.setdefault("runs", []).append({"at": S.now_iso(), "run_id": ctx.run_id, "metrics": metrics})
        hist["runs"] = hist["runs"][-50:]
        S.write_json(base.repo_path(HISTORY), hist)
        S.write_json(base.repo_path("agent-work/tests/last_metrics.json"),
                     {"generated_at": S.now_iso(), "metrics": metrics, "bank_size": n_bank})

    # Chemin LLM (optionnel) : nouveaux tests seulement si fournisseur/mock.
    if ctx.mock:
        proposals += _example_tests(ctx)

    ctx.summary = {
        "Harness exécuté": "oui" if rc == 0 else "échec",
        "Banque de tests (ia/tests.json)": n_bank,
        "Métriques": (", ".join("%s=%s" % (k, metrics[k]) for k in ("n_tests", "contrats_precision", "statut", "faux_positifs")) if metrics else "non lisibles"),
        "Régressions détectées": len(regressions),
        "Nouveaux tests générés (LLM)": (len(proposals) - (1 if regressions else 0)) if ctx.mock else 0,
    }
    note = "tests: métriques=%s régressions=%d" % ("ok" if metrics else "?", len(regressions))
    return proposals, [note]
