#!/usr/bin/env python3
"""Ancrage d'ENVIRONNEMENT — déterministe, 0 token, 0 réseau.

Projette le référentiel de NAVIGATION vers les autorités publiques (sources-officielles.json) dans le
graphe, en COUCHES SÉPARÉES : les autorités et les concepts réglementaires/fiscaux vivent dans des
domaines distincts ('reglementation', 'fiscalite') — JAMAIS mélangés aux clauses contractuelles. Ils sont
reliés aux clauses par des arêtes `governed_by` (une garantie « est gouvernée par » un concept évolutif).

Ne contient AUCUN contenu réglementaire (le référentiel n'en a pas) : uniquement des POINTEURS datés
(url, autorité), avec une fraîcheur (TTL) → une entrée périmée génère naturellement une tâche 'rafraichir'
que l'agent official-sources (réseau) traitera plus tard. Rejouable, idempotent (identités du graphe).
"""
import knowledge_graph as KG

TTL_DAYS_ENV = 365                     # les pointeurs réglementaires/fiscaux se revérifient annuellement


def _norm(t):
    return KG._norm(t)


def _entity_keywords(node):
    kws = set()
    for k in (node.get("content", {}) or {}).get("keywords", []) or []:
        kws.add(_norm(k))
    for w in _norm(node.get("label")).split():
        if len(w) > 3:
            kws.add(w)
    return kws


def ingest_environment(adapter, graph):
    """Ajoute les nœuds d'environnement (autorités + concepts évolutifs) et les relie aux clauses de
    contrat concernées. Retourne des statistiques. Ne consomme aucun token, n'accède à aucun réseau."""
    env = adapter.environment_sources()
    st = {"authorities": 0, "concepts": 0, "gov_concept_authority": 0, "gov_clause_concept": 0}

    # 1) autorités publiques (pointeurs datés) — domaine 'reglementation'
    auth_id = {}
    for a in env.get("authorities", []):
        node, _new = graph.upsert_entity(
            "reglementation", "__environnement__", "autorite", a["nom"],
            content={"url": a.get("url"), "type": a.get("type"), "role": a.get("role")},
            confidence=0.6, agent="environment-ingest", ttl_days=TTL_DAYS_ENV, as_of=a.get("as_of"))
        auth_id[a["id"]] = node["id"]
        st["authorities"] += 1

    # 2) concepts évolutifs (droit/fiscalité) — domaine séparé, reliés à leurs autorités
    concepts = []
    for c in env.get("concepts", []):
        cnode, _new = graph.upsert_entity(
            c["domain"], "__environnement__", "concept_reglementaire", c["nom"],
            content={"key": c["key"], "keywords": c.get("keywords", [])},
            confidence=0.55, agent="environment-ingest", ttl_days=TTL_DAYS_ENV, as_of=c.get("as_of"))
        st["concepts"] += 1
        for akey in c.get("authorities", []):
            if akey in auth_id:
                _e, new = graph.add_relation("governed_by", cnode["id"], auth_id[akey],
                                             agent="environment-ingest", confidence=0.6)
                st["gov_concept_authority"] += int(new)
        concepts.append((cnode, set(_norm(k) for k in c.get("keywords", []))))

    # 3) ancrage des clauses : une entité de contrat dont les mots-clés recoupent un concept -> governed_by
    for ent in graph.nodes(layer=2, domain="axa-contrat"):
        ekws = _entity_keywords(ent)
        if not ekws:
            continue
        for cnode, ckws in concepts:
            if ekws & ckws:
                _e, new = graph.add_relation("governed_by", ent["id"], cnode["id"],
                                             agent="environment-ingest", confidence=0.5)
                st["gov_clause_concept"] += int(new)

    graph.save()
    return st
