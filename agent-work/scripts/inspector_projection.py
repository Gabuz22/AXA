#!/usr/bin/env python3
"""Projection « INSPECTEUR » + outils pour les IA — déterministe, versionnée, lecture seule, 0 token.

Assemble depuis le graphe des vues DIRECTEMENT exploitables par une IA : fiches mono-contrat, comparaison
multi, matrices (mécanisme→contrats, contrat→garantie→conditions/exclusions, concept→définitions), et un
INDEX D'OUTILS (protocoles d'interrogation) + un guide IA. Isolé sous agent-work/knowledge/inspector/ —
ne touche JAMAIS les masters ni la Vue IA produit (une exposition produit exigerait une validation).
"""
import os
import hashlib
import knowledge_graph as KG
import inspector_mono as IM
import inspector_multi as IX

INSPECTOR_DIR = "agent-work/knowledge/inspector"
VERSION = "1.0.0"


def _norm(t):
    return KG._norm(t)


def matrix_mechanism_contracts(graph, subjects, domain):
    out = {}
    for s in subjects:
        for n in graph.nodes(layer=2, subject=s, domain=domain):
            out.setdefault(n.get("subtype") or "autre", set()).add(s)
    return {k: sorted(v) for k, v in out.items()}


def matrix_contract_mechanisms(graph, subjects, domain):
    """contrat → garanties + conditions + exclusions (niveau contrat, séparé par mécanisme)."""
    out = {}
    for s in subjects:
        d = {"garanties": [], "conditions": [], "exclusions": [], "plafonds": []}
        for n in graph.nodes(layer=2, subject=s, domain=domain):
            st = n.get("subtype")
            if st == "garantie":
                d["garanties"].append(n.get("label"))
            elif st in ("condition", "declencheur"):
                d["conditions"].append(n.get("label"))
            elif st == "exclusion":
                d["exclusions"].append(n.get("label"))
            elif st in ("plafond", "franchise", "delai"):
                d["plafonds"].append(n.get("label"))
        out[s] = d
    return out


def matrix_concept_definitions(graph, subjects, domain):
    """concept (libellé normalisé d'une définition) → définition SELON chaque contrat (jamais fusionnées)."""
    out = {}
    for s in subjects:
        for n in graph.nodes(layer=2, subject=s, domain=domain):
            if n.get("subtype") == "definition":
                key = _norm(n.get("label"))[:40]
                out.setdefault(key, {})[s] = n.get("label")
    return out


def ai_tools():
    """Index déclaratif des OUTILS/protocoles qu'une IA peut utiliser (mappés aux moteurs déterministes)."""
    return [
        {"nom": "analyser_contrat", "moteur": "inspector_mono.reasoning_sheet",
         "entree": {"subject": "str"}, "sortie": "fiche mono-contrat (finalité, garanties, exclusions, environnement, incertitudes)",
         "fichier": "contrats/<slug>.json"},
        {"nom": "comparer_contrats", "moteur": "inspector_multi.compare",
         "entree": {"subjects": "[str]"}, "sortie": "paires classées (substituables/complémentaires/…) + trous",
         "fichier": "comparison.json"},
        {"nom": "analyser_cas_client", "moteur": "inspector_mono.apply_case",
         "entree": {"subject": "str", "case": "objet cas (statuts requis)"}, "sortie": "conclusion PROVISOIRE conditionnelle + données manquantes"},
        {"nom": "decomposer_besoin", "moteur": "inspector_needs.decompose",
         "entree": {"case": "objet cas"}, "sortie": "arbre objectifs→besoins→contrats candidats→données nécessaires"},
        {"nom": "construire_solutions", "moteur": "inspector_solution.build_scenarios",
         "entree": {"case": "objet cas"}, "sortie": "scénarios (mono/multi/renforcé/existant) + besoins non couverts + doublons"},
        {"nom": "comparer_solutions", "moteur": "inspector_solution.arbitrate",
         "entree": {"scenarios": "[...]"}, "sortie": "meilleur par axe + compromis, jamais de 'meilleur' absolu"},
        {"nom": "avis_inspecteur", "moteur": "inspector_advice.advise",
         "entree": {"case": "objet cas (statuts requis)"},
         "sortie": "avis structuré : profil, risques PRIORISÉS (protéger avant d'épargner, dettes d'abord), audit de l'existant (couvert/trou/doublon), plan d'action ordonné avec pourquoi + questions + pièges fréquents, objections probables, réserves",
         "fichier": "cas-clients/avis_inspecteur.example.json",
         "validation": "HUMAINE (avis conditionnel, heuristiques étiquetées)"},
        {"nom": "identifier_informations_manquantes", "moteur": "inspector_case.completeness",
         "entree": {"case": "objet cas"}, "sortie": "champs manquants + score de complétude"},
        {"nom": "detecter_doublons_et_trous", "moteur": "inspector_multi.coverage_gaps",
         "entree": {"subjects": "[str]"}, "sortie": "trous de couverture par mécanisme"},
        {"nom": "matrices", "moteur": "inspector_projection",
         "entree": {}, "sortie": "mecanisme→contrats, contrat→garanties/conditions/exclusions, concept→définitions",
         "fichier": "matrices.json"},
    ]


def guide_ia():
    return (
        "# Guide IA — Gabriel AXA « Inspecteur »\n\n"
        "Vous disposez d'un ENVIRONNEMENT DE RAISONNEMENT (pas seulement d'une recherche). Règles :\n\n"
        "1. **Ne jamais inventer** une clause, une garantie, un montant, une règle fiscale.\n"
        "2. **Toujours citer** la preuve (document, page) fournie dans les fiches.\n"
        "3. **Séparer** : fait du cas / hypothèse / inconnue / clause contractuelle / règle externe / interprétation.\n"
        "4. **Ne pas mélanger** les contrats : chaque preuve appartient à un contrat.\n"
        "5. **Cas incomplet → conclusion CONDITIONNELLE** : lister les informations manquantes et les questions à poser.\n"
        "6. **Règle externe** (fiscalité/réglementation) : vérifier la FRAÎCHEUR ; ne jamais la présenter comme une clause.\n"
        "7. **Sensible** (exclusions, montants, éligibilité) → signaler qu'une vérification humaine/officielle est requise.\n\n"
        "## Parcours recommandés\n"
        "- Question mono-contrat → `contrats/<slug>.json` (fiche de raisonnement).\n"
        "- Question multi-contrats → `comparison.json` (paires classées, trous).\n"
        "- Cas client → décomposer le besoin, puis `analyser_cas_client` par contrat, puis `construire_solutions`.\n"
        "- Toujours finir par : informations manquantes, incertitudes, éléments à faire valider.\n\n"
        "Voir `tools.json` pour la liste des outils et `index.json` pour l'inventaire.\n"
    )


def graph_fingerprint(graph):
    keys = sorted(graph.data.get("nodes", {})) + sorted(graph.data.get("edges", {}))
    return "i_" + hashlib.sha256("|".join(keys).encode("utf-8")).hexdigest()[:16]


def write_inspector(graph, subjects, domain, adapter, write_json, write_text, now, base_dir=INSPECTOR_DIR, dry_run=False):
    """Écrit la projection Inspecteur (fiches + comparaison + matrices + outils + guide + index). Isolé."""
    if dry_run or write_json is None:
        return 0
    from agents import base
    expected = adapter.expected_categories() if hasattr(adapter, "expected_categories") else []
    n = 0
    for s in subjects:
        sheet = IM.reasoning_sheet(graph, s, domain, expected)
        fname = KG.ascii_slug(s) + ".json"
        write_json(base.repo_path(os.path.join(base_dir, "contrats", fname)), sheet)
        n += 1
    write_json(base.repo_path(os.path.join(base_dir, "comparison.json")), IX.compare(graph, subjects, domain, expected))
    write_json(base.repo_path(os.path.join(base_dir, "matrices.json")), {
        "mecanisme_contrats": matrix_mechanism_contracts(graph, subjects, domain),
        "contrat_mecanismes": matrix_contract_mechanisms(graph, subjects, domain),
        "concept_definitions": matrix_concept_definitions(graph, subjects, domain),
    })
    write_json(base.repo_path(os.path.join(base_dir, "tools.json")), {"version": VERSION, "tools": ai_tools()})
    write_json(base.repo_path(os.path.join(base_dir, "index.json")), {
        "projection": "inspector", "version": VERSION, "generated_at": now(), "domain": domain,
        "graph_fingerprint": graph_fingerprint(graph), "contrats": sorted(subjects),
        "fichiers": ["contrats/<slug>.json", "comparison.json", "matrices.json", "tools.json", "GUIDE_IA.md"]})
    if write_text is not None:
        write_text(base.repo_path(os.path.join(base_dir, "GUIDE_IA.md")), guide_ia())
    return n
