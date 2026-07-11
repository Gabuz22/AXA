#!/usr/bin/env python3
"""Agent knowledge-builder — CAPACITÉ LLM d'approfondissement (couches L3 relations, L4 compréhension).

Puise dans le backlog déterministe (tâches 'relier' / 'expliquer' produites par knowledge-curator) et
approfondit le graphe : relations typées entre entités connues, explications ancrées dans les preuves.
Ne consomme des tokens que là où c'est UTILE :
  • rien à faire si le sujet est déjà relié / expliqué (garde déterministe, 0 appel) ;
  • budget de run (ctx.budget) + cost-ledger hebdomadaire par domaine (portier) ;
  • fail-open : sans fournisseur/quota, l'agent s'arrête proprement (no_work), rien n'est cassé.

N'invente aucune entité (les relations ne lient que des entités existantes). Écrit uniquement dans le
graphe (agent-work/knowledge/). Le routage multi-fournisseurs est réutilisé via base.llm_json.
"""
import safety_checks as S
from agents import base
import knowledge_graph as KG
import knowledge_tasks as KT
import knowledge_build as KB
import knowledge_ops as KO

AGENT_CODE_VERSION = "2.8.0"

GRAPH = "agent-work/knowledge/graph.json"
LEDGER = "agent-work/knowledge/cost_ledger.json"
MAX_SUBJECTS_RELATIONS = 2          # sujets 'relier' par run (borne le coût)
MAX_SUBJECTS_UNDERSTANDING = 2      # sujets 'expliquer' par run
WEEKLY_CALL_CAP = 60                # plafond d'appels LLM par domaine et par semaine


def run(ctx):
    ctx.self_wrote = True
    backlog = KT.load_backlog(S.load_json)
    todo_rel = KT.pending(backlog, types=("relier",))
    todo_exp = KT.pending(backlog, types=("expliquer",))
    if not (todo_rel or todo_exp):
        ctx.summary = {"Backlog 'relier'/'expliquer'": 0}
        return [], ["knowledge-builder: aucune tâche d'approfondissement en attente"]
    if ctx.router is None and not ctx.mock:
        ctx.summary = {"À approfondir": len(todo_rel) + len(todo_exp), "LLM": "aucun fournisseur"}
        return [], ["knowledge-builder: aucun fournisseur LLM — arrêt propre (0 approfondissement)"]

    write = None if ctx.dry_run else S.write_json
    graph = KG.KnowledgeGraph(base.repo_path(GRAPH), load_json=S.load_json, write_json=write)
    ledger = KO.CostLedger(base.repo_path(LEDGER), load_json=S.load_json, write_json=write)

    def llm_call(prompt):
        return base.llm_json(ctx, prompt, max_tokens=600)

    added_rel = added_exp = 0
    done_subjects = []

    for t in todo_rel[:MAX_SUBJECTS_RELATIONS]:
        dom = t.get("domain")
        if not ctx.budget.can_spend() or not ledger.can_spend(dom, WEEKLY_CALL_CAP):
            break
        r = KB.build_relations(graph, dom, t.get("subject"), llm_call)
        added_rel += r.get("added", 0)
        if ctx.provider_used:
            ledger.record(dom, llm_calls=1)
        done_subjects.append(("relier", t.get("subject"), r))

    for t in todo_exp[:MAX_SUBJECTS_UNDERSTANDING]:
        dom = t.get("domain")
        if not ctx.budget.can_spend() or not ledger.can_spend(dom, WEEKLY_CALL_CAP):
            break
        r = KB.build_understanding(graph, dom, t.get("subject"), llm_call)
        added_exp += r.get("added", 0)
        if ctx.provider_used:
            ledger.record(dom, llm_calls=1)
        done_subjects.append(("expliquer", t.get("subject"), r))

    if not ctx.dry_run:
        graph.save()
        ledger.save()

    ctx.summary = {
        "Sujets traités": len(done_subjects),
        "Relations ajoutées (L3)": added_rel,
        "Explications ajoutées (L4)": added_exp,
        "Graphe (L1/L2/L3/L4)": "%d/%d/%d/%d" % (graph.stats()["evidence"], graph.stats()["normalized"],
                                                 graph.stats()["relations"], graph.stats()["understanding"]),
        "Fournisseur": ctx.provider_used or "aucun",
    }
    notes = ["knowledge-builder: +%d relation(s), +%d explication(s) sur %d sujet(s)"
             % (added_rel, added_exp, len(done_subjects))]
    if ctx.provider_used is None:
        notes.append("cause LLM: %s" % (getattr(ctx, "last_llm_cause", None) or "aucun fournisseur"))
    return [], notes
