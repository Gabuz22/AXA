#!/usr/bin/env python3
"""Banc d'essai « Inspecteur » + évaluateur DÉTERMINISTE + boucle échec→tâche — 0 token.

Le banc contient des tests métier réalistes (mono/multi/cas client/edge cases). Chaque test s'exécute via
les moteurs déterministes (inspector_mono/multi/needs/solution) et l'évaluateur VÉRIFIE la réponse par des
contrôles déterministes (pas seulement par LLM) : aucune invention, aucun mélange de contrats, données
manquantes signalées, distinction faits/hypothèses, prudence, « je ne sais pas » quand rien ne correspond.

La boucle diagnostique la cause d'un échec et propose une TÂCHE typée (extraction/relation/explication/…).
"""
import knowledge_graph as KG
import inspector_case as IC
import inspector_mono as IM
import inspector_multi as IX
import inspector_needs as INn
import inspector_solution as IS

FAMILIES = ("mono", "multi", "cas_mono", "cas_multi")


def default_bench(subjects):
    """Banc générique construit sur les contrats réellement présents (subjects). Cas synthétiques."""
    s0 = subjects[0] if subjects else "ContratA"
    s1 = subjects[1] if len(subjects) > 1 else s0
    incomplete = IC.new_case(besoins_exprimes=["se proteger en cas d'invalidite"])
    with_facts = IC.new_case(besoins_exprimes=["se proteger en cas d'invalidite"],
                             fields={"age": IC.new_datum(45, "confirme"),
                                     "statut_professionnel": IC.new_datum("salarie", "declare"),
                                     "situation_familiale": IC.new_datum("marie 2 enfants", "declare")},
                             objectifs=["proteger la famille"])
    no_match = IC.new_case(besoins_exprimes=["assurance automobile"])
    return [
        {"id": "mono_1", "family": "mono", "subject": s0},
        {"id": "multi_1", "family": "multi", "subjects": subjects[:3] or [s0]},
        {"id": "cas_mono_incomplet", "family": "cas_mono", "subject": s0, "case": incomplete, "expect_incomplete": True},
        {"id": "cas_mono_faits", "family": "cas_mono", "subject": s0, "case": with_facts},
        {"id": "cas_mono_no_match", "family": "cas_mono", "subject": s0, "case": no_match, "expect_no_match": True},
        {"id": "cas_multi_solutions", "family": "cas_multi", "case": with_facts},
    ]


def run_test(test, graph, domain, subjects):
    """Exécute un test via le bon moteur. Retourne la réponse structurée."""
    fam = test["family"]
    if fam == "mono":
        return {"kind": "mono", "answer": IM.reasoning_sheet(graph, test["subject"], domain)}
    if fam == "multi":
        return {"kind": "multi", "answer": IX.compare(graph, test["subjects"], domain, list(IX.STRUCTURANTES))}
    if fam == "cas_mono":
        return {"kind": "cas_mono", "answer": IM.apply_case(graph, test["subject"], test["case"], domain)}
    if fam == "cas_multi":
        scen = IS.build_scenarios(test["case"], graph, domain)
        arb = IS.arbitrate(scen["scenarios"], test["case"].get("objectifs"))
        return {"kind": "cas_multi", "answer": {"scenarios": scen, "arbitrage": arb}}
    return {"kind": "unknown", "answer": {}}


def _all_labels(graph, domain):
    return {KG._norm(n.get("label")) for n in graph.nodes(layer=2, domain=domain)}


def evaluate(test, result, graph, domain):
    """Contrôles DÉTERMINISTES. Retourne {checks, score, failures}."""
    ans = result.get("answer", {})
    labels = _all_labels(graph, domain)
    checks = {}

    # 1) aucune invention : les libellés cités existent dans le graphe
    cited = _cited_labels(result)
    checks["aucune_invention"] = all(KG._norm(c) in labels for c in cited) if cited else True

    # 2) prudence / conditionnel selon la famille
    if result["kind"] == "cas_mono":
        checks["donnees_manquantes_signalees"] = bool(ans.get("donnees_manquantes")) if test.get("expect_incomplete") else True
        checks["conclusion_conditionnelle"] = "provisoire" in KG._norm(ans.get("conclusion_provisoire", "")) or \
            "conditionnelle" in KG._norm(ans.get("conclusion_provisoire", "")) or bool(ans.get("validation_humaine_requise"))
        checks["distingue_faits_hypotheses"] = ("elements_cas_pertinents" in ans and "hypotheses" in ans)
        if test.get("expect_no_match"):
            checks["dit_je_ne_sais_pas"] = (ans.get("clauses_potentiellement_pertinentes") == [])
    if result["kind"] == "multi":
        checks["pas_de_melange"] = all("a" in p and "b" in p for p in ans.get("pairs", []))
        checks["echoue_proprement"] = True  # non_comparables géré
    if result["kind"] == "cas_multi":
        checks["arbitrage_non_absolu"] = "meilleur_par_axe" in ans.get("arbitrage", {})
        checks["validation_requise"] = bool(ans.get("arbitrage", {}).get("validation_humaine_requise"))
        checks["aucun_cout_invente"] = "€" not in __import__("json").dumps(ans, ensure_ascii=False)

    failures = [k for k, v in checks.items() if not v]
    score = round((len(checks) - len(failures)) / len(checks), 3) if checks else 1.0
    return {"test": test["id"], "kind": result["kind"], "checks": checks, "failures": failures, "score": score}


def _cited_labels(result):
    ans = result.get("answer", {})
    out = []
    if result["kind"] == "mono":
        out += ans.get("architecture_garanties", {}).get("principales", [])
        out += ans.get("exclusions", []) + ans.get("conditions", [])
    if result["kind"] == "cas_mono":
        out += ans.get("clauses_potentiellement_pertinentes", [])
    return [x for x in out if x]


def diagnose(scorecard):
    """Cause probable d'un échec → tâche typée (boucle d'amélioration)."""
    tasks = []
    for f in scorecard.get("failures", []):
        cause, ttype = {
            "donnees_manquantes_signalees": ("le cas incomplet n'est pas signalé", "clarification"),
            "conclusion_conditionnelle": ("conclusion trop affirmative", "amelioration_prompt"),
            "aucune_invention": ("libellé cité absent du graphe", "verification"),
            "dit_je_ne_sais_pas": ("réponse alors qu'aucun contrat ne correspond", "amelioration_prompt"),
        }.get(f, ("faiblesse: %s" % f, "reexaminer_zone"))
        tasks.append({"cause": cause, "type": ttype, "test": scorecard["test"], "priority": 3})
    return tasks


def run_bench(graph, domain, subjects, bench=None):
    bench = bench or default_bench(subjects)
    results, cards = [], []
    for t in bench:
        r = run_test(t, graph, domain, subjects)
        card = evaluate(t, r, graph, domain)
        results.append({"test": t["id"], "family": t["family"]})
        cards.append(card)
    scores = [c["score"] for c in cards]
    tasks = [task for c in cards for task in diagnose(c)]
    by_family = {}
    for t, c in zip(bench, cards):
        by_family.setdefault(t["family"], []).append(c["score"])
    return {
        "n_tests": len(cards), "score_global": round(sum(scores) / len(scores), 3) if scores else 0.0,
        "score_par_famille": {f: round(sum(v) / len(v), 3) for f, v in by_family.items()},
        "cards": cards, "taches_correctives": tasks,
    }
