#!/usr/bin/env python3
"""Build de la zone dérivée /ia/inspecteur/ — expose l'environnement de raisonnement « Inspecteur » aux IA.

DÉTERMINISTE, 0 token, 0 réseau. Reconstruit à partir des MASTERS (via l'adaptateur AXA + ingestion
déterministe du graphe en mémoire), puis écrit une projection compacte et lisible par une IA dans
`ia/inspecteur/`. Ne modifie AUCUN master ni aucune page /ia existante (zone dérivée additive) ; ajoute
un pointeur additif dans ai-manifest.json pour la découvrabilité.

Contenu : fiches mono-contrat, comparaison multi (substituables/complémentaires/doublons/trous), matrices,
outils IA (tools.json), guide de méthode (GUIDE_IA.md), index. Les couches L3-internes/L4 (interprétation)
apparaissent si présentes dans le graphe (produites par knowledge-builder LLM) ; sinon « à approfondir ».
"""
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(REPO, "agent-work", "scripts"))

import safety_checks as S
import knowledge_graph as KG
import knowledge_ingest as KI
import environment_ingest as EI
import domain_adapter
import inspector_mono as IM
import inspector_multi as IX
import inspector_projection as IP

OUT = os.path.join(REPO, "ia", "inspecteur")
DOMAIN = "axa-contrat"
VERSION = "1.0.0"


def _slug(s):
    return (KG._norm(s).replace(" ", "_").replace("'", "") or "sujet")


def _write_json(rel, obj):
    p = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _write_text(rel, text):
    p = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


def build_graph():
    adapter = domain_adapter.get(DOMAIN)
    graph = KG.KnowledgeGraph(path=None, load_json=S.load_json, write_json=None)   # en mémoire
    KI.ingest(adapter, graph)
    EI.ingest_environment(adapter, graph)
    return adapter, graph


GUIDE = """# Gabriel AXA — Vue IA « Inspecteur fonction support »

Vous (IA) disposez ici d'un ENVIRONNEMENT DE RAISONNEMENT dérivé du graphe de connaissances AXA
(lecture seule, sourcé). Objectif : vous rapprocher du rôle d'un Inspecteur fonction support, SANS jamais
remplacer une validation humaine ni engager AXA.

## Règles absolues
1. N'inventez jamais une clause, une garantie, un montant, une règle fiscale.
2. Citez toujours la preuve (document, page) présente dans les fiches.
3. Séparez : fait du cas / hypothèse / inconnue / clause contractuelle / règle externe / interprétation.
4. Ne mélangez jamais les contrats : chaque preuve appartient à UN contrat.
5. Cas incomplet → conclusion CONDITIONNELLE : listez les informations manquantes et les questions à poser.
6. Règle externe (fiscalité/réglementation) : vérifiez la FRAÎCHEUR ; ne la présentez jamais comme une clause.
7. Élément sensible (exclusions, montants, éligibilité) → signalez qu'une vérification humaine/officielle est requise.

## Méthode de raisonnement (12 étapes)
1. Identifier la question (mono-contrat / multi-contrats / cas client).
2. Identifier le(s) contrat(s) concerné(s) — voir `contrats/index.json`.
3. Récupérer les preuves — section `preuves` de chaque fiche.
4. Identifier les définitions applicables — `matrices.json` → `concept_definitions` (par contrat).
5. Reconstruire le mécanisme — fiche : architecture, déclencheurs, conditions.
6. Vérifier conditions ET exclusions — fiche : `conditions`, `exclusions`.
7. Identifier les données manquantes (si cas client).
8. Consulter l'environnement externe si nécessaire — fiche : `environnement` (source + fraîcheur).
9. Construire les options (scénarios) — voir `tools.json` → `construire_solutions`.
10. Comparer les options — `tools.json` → `comparer_solutions` (jamais de « meilleur » absolu).
11. Expliciter les hypothèses.
12. Signaler les validations nécessaires.

## Fichiers
- `contrats/<slug>.json` : fiche de raisonnement mono-contrat (finalité, garanties, conditions, exclusions,
  environnement, incertitudes, preuves).
- `comparison.json` : comparaison multi-contrats (paires classées substituables/complémentaires/doublon/
  non_comparables + trous de couverture). Preuves conservées par contrat.
- `matrices.json` : mécanisme→contrats, contrat→garanties/conditions/exclusions, concept→définitions par contrat.
- `tools.json` : outils/protocoles utilisables (entrée/sortie/contraintes).
- `index.json` : inventaire + empreinte de reconstruction.

## Limites
La charpente est déterministe (structure, comparaison, garde-fous). La PRÉCISION sémantique (écarter un
candidat, chiffrer un arbitrage, expliciter une confusion) vous revient, à partir des preuves fournies.
Certaines explications (L4) peuvent être marquées « à approfondir » si non encore produites.
"""


def tools_detailed():
    """Outils enrichis (description, cas d'usage, entrée, sortie, contraintes, erreurs, exemple, preuve, validation)."""
    base = {t["nom"]: t for t in IP.ai_tools()}
    extra = {
        "analyser_contrat": {"cas_usage": "comprendre un contrat en profondeur", "preuve_attendue": "citations des fiches", "validation": "aucune (lecture)"},
        "comparer_contrats": {"cas_usage": "différences/complémentarités entre contrats", "preuve_attendue": "par contrat", "validation": "confirmer les paires 'substituables/doublon'"},
        "analyser_cas_client": {"cas_usage": "confronter un contrat à une situation", "preuve_attendue": "clauses citées", "validation": "HUMAINE si sensible/incomplet"},
        "construire_solutions": {"cas_usage": "proposer plusieurs scénarios conditionnels", "preuve_attendue": "par garantie", "validation": "HUMAINE"},
        "comparer_solutions": {"cas_usage": "arbitrer sans 'meilleur' absolu", "preuve_attendue": "—", "validation": "HUMAINE"},
        "verifier_source_externe": {"cas_usage": "vérifier la fraîcheur d'une règle externe", "preuve_attendue": "source officielle + date", "validation": "officielle si périmée"},
    }
    out = []
    for t in IP.ai_tools():
        d = dict(t)
        d.update(extra.get(t["nom"], {}))
        d.setdefault("erreurs_possibles", ["contrat introuvable", "cas incomplet", "aucun mécanisme partagé"])
        out.append(d)
    # outils supplémentaires (protocoles) demandés par la mission
    for nom, desc in (("distinguer_fait_hypothese_inconnu", "classer chaque donnée d'un cas par statut"),
                      ("distinguer_contractuel_externe_interpretatif", "étiqueter la source de chaque affirmation")):
        out.append({"nom": nom, "moteur": "inspector_case / projection", "description": desc,
                    "validation": "aucune", "preuve_attendue": "statut/couche explicite"})
    return out


def main():
    adapter, graph = build_graph()
    subjects = sorted({n.get("subject") for n in graph.nodes(layer=2, domain=DOMAIN) if n.get("subject")})
    expected = adapter.expected_categories() if hasattr(adapter, "expected_categories") else []

    contrat_index = []
    for s in subjects:
        sheet = IM.reasoning_sheet(graph, s, DOMAIN, expected)
        fn = _slug(s) + ".json"
        _write_json(os.path.join("contrats", fn), sheet)
        contrat_index.append({"contrat": s, "fichier": "contrats/%s" % fn,
                              "profondeur": sheet.get("profondeur"), "couverture_semantique": sheet.get("couverture_semantique")})
    _write_json("contrats/index.json", {"version": VERSION, "contrats": contrat_index})

    _write_json("comparison.json", IX.compare(graph, subjects, DOMAIN, expected))
    _write_json("matrices.json", {
        "mecanisme_contrats": IP.matrix_mechanism_contracts(graph, subjects, DOMAIN),
        "contrat_mecanismes": IP.matrix_contract_mechanisms(graph, subjects, DOMAIN),
        "concept_definitions": IP.matrix_concept_definitions(graph, subjects, DOMAIN),
    })
    _write_json("tools.json", {"version": VERSION, "tools": tools_detailed()})
    _write_text("GUIDE_IA.md", GUIDE)
    fp = IP.graph_fingerprint(graph)
    _write_json("index.json", {"projection": "inspecteur", "version": VERSION, "domain": DOMAIN,
                               "generated_at": S.now_iso(), "graph_fingerprint": fp,
                               "stats": graph.stats(), "contrats": subjects,
                               "fichiers": ["GUIDE_IA.md", "contrats/index.json", "contrats/<slug>.json",
                                            "comparison.json", "matrices.json", "tools.json"],
                               "avertissement": "Zone DÉRIVÉE du graphe (lecture seule). Ni master, ni proposition. Preuves conservées ; interprétations séparées ; validation humaine pour toute sortie sensible."})
    _write_text("index.html", _index_html(subjects, fp))
    _update_manifest(fp, len(subjects))
    print("BUILD /ia/inspecteur : %d contrats, graphe %s, empreinte %s" % (len(subjects), graph.stats(), fp))
    return 0


def _index_html(subjects, fp):
    lis = "\n".join("<li><a href=\"contrats/%s.json\">%s</a></li>" % (_slug(s), s) for s in subjects)
    return ("<!doctype html><html lang=fr><meta charset=utf-8><title>Gabriel AXA — Inspecteur (Vue IA)</title>"
            "<h1>Gabriel AXA — environnement « Inspecteur » (Vue IA, lecture seule)</h1>"
            "<p>Zone dérivée du graphe de connaissances. Commencez par <a href=\"GUIDE_IA.md\">GUIDE_IA.md</a>.</p>"
            "<h2>Outils &amp; vues</h2><ul>"
            "<li><a href=\"tools.json\">tools.json</a> — outils/protocoles</li>"
            "<li><a href=\"comparison.json\">comparison.json</a> — comparaison multi-contrats</li>"
            "<li><a href=\"matrices.json\">matrices.json</a> — matrices</li>"
            "<li><a href=\"index.json\">index.json</a> — inventaire</li></ul>"
            "<h2>Fiches mono-contrat</h2><ul>%s</ul>"
            "<p><small>Empreinte de reconstruction : %s. Ni master ni proposition ; preuves conservées ; validation humaine requise pour le sensible.</small></p>"
            "</html>" % (lis, fp))


def _update_manifest(fp, n):
    """Pointeur ADDITIF dans ai-manifest.json (découvrabilité) — n'écrase rien d'autre."""
    p = os.path.join(REPO, "ia", "ai-manifest.json")
    try:
        m = json.load(open(p, encoding="utf-8"))
    except Exception:
        return
    m["inspecteur"] = {
        "description": "Environnement de raisonnement Inspecteur (dérivé du graphe, lecture seule).",
        "entree": "ia/inspecteur/GUIDE_IA.md", "index": "ia/inspecteur/index.json",
        "outils": "ia/inspecteur/tools.json", "contrats": n, "empreinte": fp,
    }
    with open(p, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    raise SystemExit(main())
