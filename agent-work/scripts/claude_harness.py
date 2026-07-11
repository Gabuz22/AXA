#!/usr/bin/env python3
"""Harnais de test 'simulation_assistee_par_claude' — protocole MANUEL reproductible (Phase 14).

Claude joue le rôle des agents LLM, MAIS via les vrais outils du projet et les mêmes contrôles :
  1) `prepare` : le code prépare le contexte (zones/entités/prompt/schéma/contraintes) des vraies tâches
     'relier'/'expliquer' du backlog, et écrit les PROMPTS à répondre.
  2) Claude lit les prompts, raisonne, et écrit ses réponses (JSON) dans responses.json.
  3) `apply` : les réponses sont injectées EXACTEMENT comme une réponse fournisseur (mêmes fonctions
     knowledge_build, mêmes garde-fous : types de relation autorisés, pas d'entité inventée), ajoutées au
     graphe avec provenance='simulation_assistee_par_claude' et validation_required=True (revue humaine).

Ce mode n'est JAMAIS activé en production (provider claude-assisted-test inéligible sans clé). Les sorties
ne doivent jamais être confondues avec des résultats API autonomes : elles portent le marqueur explicite.
"""
import os, sys, json, hashlib, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import safety_checks as S
import knowledge_graph as KG
import knowledge_tasks as KT
import knowledge_build as KB

ORIGIN = "simulation_assistee_par_claude"
DIR = "agent-work/tests/claude_assisted"
STORE = os.path.join(DIR, "responses.json")
PROMPTS = os.path.join(DIR, "prompts.json")
GRAPH = "agent-work/knowledge/graph.json"


def _hash(user):
    return "h_" + hashlib.sha256(user.encode("utf-8")).hexdigest()[:20]


def _rp(p):
    return os.path.join(S.REPO_ROOT, p)


def _load(path, default):
    try:
        return S.load_json(_rp(path), default=default)
    except Exception:
        return default


def _recording_llm(collected):
    """llm_call qui ENREGISTRE le prompt (mode prepare) et renvoie None (rien n'est produit)."""
    def call(prompt):
        collected[_hash(prompt)] = prompt
        return None
    return call


def _replaying_llm(responses, used):
    """llm_call qui REJOUE la réponse pré-enregistrée par Claude (mode apply)."""
    def call(prompt):
        h = _hash(prompt)
        rec = responses.get(h)
        used.append(h)
        return rec if isinstance(rec, dict) else None
    return call


def _tasks(graph, domain, kinds, limit):
    backlog = KT.load_backlog(S.load_json, _rp(KT.BACKLOG))
    todo = KT.pending(backlog, types=kinds)
    return todo[:limit]


def prepare(domain, limit):
    graph = KG.KnowledgeGraph(_rp(GRAPH), load_json=S.load_json)
    collected = {}
    call = _recording_llm(collected)
    for t in _tasks(graph, domain, ("relier",), limit):
        KB.build_relations(graph, t["domain"], t["subject"], call)
    for t in _tasks(graph, domain, ("expliquer",), limit):
        KB.build_understanding(graph, t["domain"], t["subject"], call)
    os.makedirs(_rp(DIR), exist_ok=True)
    S.write_json(_rp(PROMPTS), {"origin": ORIGIN, "generated_at": S.now_iso(), "prompts": collected})
    # amorce le fichier de réponses s'il n'existe pas (Claude le remplira)
    if not os.path.isfile(_rp(STORE)):
        S.write_json(_rp(STORE), {"origin": ORIGIN, "responses": {}})
    print("PREPARE: %d prompt(s) à répondre écrits dans %s" % (len(collected), PROMPTS))
    for h in collected:
        print("  -", h)
    return collected


def apply(domain, limit):
    responses = (_load(STORE, {}) or {}).get("responses", {})
    graph = KG.KnowledgeGraph(_rp(GRAPH), load_json=S.load_json, write_json=S.write_json)
    import coverage_model as CM
    subj_seen, used = set(), []
    before = {}
    call = _replaying_llm(responses, used)
    added_rel = added_exp = 0
    for t in _tasks(graph, domain, ("relier",), limit):
        s = t["subject"]; subj_seen.add(s)
        before.setdefault(s, CM.depth_score(CM.coverage_vector(graph, s, domain)))
        r = KB.build_relations(graph, domain, s, call, agent=ORIGIN)
        added_rel += r.get("added", 0)
    for t in _tasks(graph, domain, ("expliquer",), limit):
        s = t["subject"]; subj_seen.add(s)
        before.setdefault(s, CM.depth_score(CM.coverage_vector(graph, s, domain)))
        r = KB.build_understanding(graph, domain, s, call, agent=ORIGIN)
        added_exp += r.get("added", 0)
    graph.save()
    print("APPLY [simulation_assistee_par_claude]: +%d relation(s) L3, +%d explication(s) L4" % (added_rel, added_exp))
    for s in sorted(subj_seen):
        after = CM.depth_score(CM.coverage_vector(graph, s, domain))
        print("  %-45s depth %.3f -> %.3f" % (s[:45], before.get(s, 0.0), after))
    # garde-fou : tout ce que Claude a produit porte le marqueur + reste à valider
    tagged = sum(1 for e in graph.data["edges"].values() if e.get("provenance_agent") == ORIGIN)
    print("  arêtes marquées '%s' (validation_required) : %d" % (ORIGIN, tagged))
    return added_rel, added_exp


def main():
    ap = argparse.ArgumentParser(description="Harnais simulation_assistee_par_claude (test manuel reproductible).")
    ap.add_argument("--mode", choices=["prepare", "apply"], required=True)
    ap.add_argument("--domain", default="axa-contrat")
    ap.add_argument("--limit", type=int, default=3)
    a = ap.parse_args()
    if a.mode == "prepare":
        prepare(a.domain, a.limit)
    else:
        apply(a.domain, a.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
