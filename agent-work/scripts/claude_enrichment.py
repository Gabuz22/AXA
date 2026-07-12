#!/usr/bin/env python3
"""Ingestion de la couche sémantique/métier produite par le raisonnement de Claude — TOUJOURS étiquetée.

Deux fichiers curés sous agent-work/enrichment/ (committés, revus via git, versionnés avec le code) :
  • claude_semantics.json : compréhension L4 par contrat (finalité, logique, confusions, situations) +
    relations L3 internes et inter-contrats. Ancrées dans les garanties/exclusions STRUCTURÉES des masters.
  • metier_inspecteur.json : matrice risques→contrats + événements de vie + questions à poser.

Règles de sûreté (identiques au provider claude-assisted) :
  - provenance = 'simulation_assistee_par_claude' sur CHAQUE nœud/arête → statut `simulated_claude`
    (knowledge_status) → jamais exposé comme vérité, toujours dans les blocs étiquetés + revue humaine ;
  - les relations ne lient que des entités EXISTANTES (résolution par libellé ; libellé introuvable = ignoré,
    compté en 'unresolved') ;
  - la compréhension contrat-niveau s'attache à une ENTITÉ ANCRE subtype='contrat' (même provenance) ;
  - déterministe, idempotent (identités canoniques du graphe), 0 token, 0 réseau.
"""
import os
import knowledge_graph as KG

ORIGIN = "simulation_assistee_par_claude"
SEMANTICS = "agent-work/enrichment/claude_semantics.json"
METIER = "agent-work/enrichment/metier_inspecteur.json"

ASPECTS = ("finalite", "logique_contractuelle", "confusions_frequentes",
           "situations_favorables", "situations_defavorables")


def _find_entity(graph, subject, domain, label):
    ln = KG._norm(label)
    for n in graph.nodes(layer=2, subject=subject, domain=domain):
        if KG._norm(n.get("label")) == ln:
            return n
    # tolérance : préfixe (les libellés longs peuvent être tronqués côté enrichment)
    for n in graph.nodes(layer=2, subject=subject, domain=domain):
        if KG._norm(n.get("label")).startswith(ln[:40]):
            return n
    return None


def _anchor(graph, subject, domain):
    """Entité ANCRE du contrat (porte la compréhension contrat-niveau). Provenance Claude => bloc étiqueté."""
    node, _new = graph.upsert_entity(domain, subject, "contrat", subject,
                                     content={"role": "ancre de comprehension contrat-niveau"},
                                     confidence=0.55, agent=ORIGIN)
    return node


def ingest_semantics(graph, data, domain=None):
    """Projette la couche sémantique dans le graphe. Retourne des stats (dont libellés non résolus)."""
    domain = domain or data.get("domain") or "axa-contrat"
    st = {"understanding": 0, "relations_internes": 0, "relations_inter": 0, "unresolved": []}
    for subject, aspects in (data.get("comprehension") or {}).items():
        anchor = _anchor(graph, subject, domain)
        for aspect in ASPECTS:
            text = aspects.get(aspect)
            if text:
                graph.upsert_understanding(anchor["id"], aspect, text, agent=ORIGIN, confidence=0.55)
                st["understanding"] += 1
    for r in data.get("relations_internes", []):
        src = _find_entity(graph, r["subject"], domain, r["src"])
        dst = _find_entity(graph, r["subject"], domain, r["dst"])
        if not (src and dst):
            st["unresolved"].append("%s: %s -> %s" % (r["subject"], r["src"][:40], r["dst"][:40]))
            continue
        _e, new = graph.add_relation(r["type"], src["id"], dst["id"], agent=ORIGIN,
                                     confidence=0.55, validation_required=True)
        st["relations_internes"] += int(new)
    for r in data.get("relations_inter_contrats", []):
        a = _anchor(graph, r["src_subject"], domain)
        b = _anchor(graph, r["dst_subject"], domain)
        _e, new = graph.add_relation(r["type"], a["id"], b["id"], agent=ORIGIN,
                                     confidence=0.55, validation_required=True)
        if new and r.get("explication"):
            graph.upsert_understanding(a["id"], "relation_%s_%s" % (r["type"], KG.ascii_slug(r["dst_subject"])[:24]),
                                       r["explication"], agent=ORIGIN, confidence=0.55)
        st["relations_inter"] += int(new)
    return st


def load_json_file(path):
    import json
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def ingest_from_repo(graph, repo_root, domain="axa-contrat"):
    """Charge et ingère les fichiers d'enrichissement s'ils existent (sinon no-op propre)."""
    data = load_json_file(os.path.join(repo_root, SEMANTICS))
    return ingest_semantics(graph, data, domain) if data else {"understanding": 0, "relations_internes": 0,
                                                               "relations_inter": 0, "unresolved": []}


EXPERIENCE = "agent-work/enrichment/experience_library.json"


def load_metier(repo_root):
    """Charge la matrice métier + la BIBLIOTHÈQUE D'EXPÉRIENCE (attachée sous _experience)."""
    m = load_json_file(os.path.join(repo_root, METIER))
    if m is not None:
        exp = load_json_file(os.path.join(repo_root, EXPERIENCE))
        if exp:
            m["_experience"] = exp
    return m
