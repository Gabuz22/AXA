#!/usr/bin/env python3
"""Capacités d'APPROFONDISSEMENT (couches L3 relations, L4 compréhension) — cœur testable, LLM injecté.

Ces fonctions transforment des entités déjà connues (L2) en connaissance PLUS PROFONDE : relations typées
entre elles (L3) et explications synthétiques ancrées dans les preuves (L4). L'appel LLM est INJECTÉ
(`llm_call`) : testable hors-ligne, et en production branché sur le routage multi-fournisseurs existant.

Garde-fous : n'invente jamais d'entité (les relations ne lient que des entités EXISTANTES) ; ne relie que
via des types autorisés ; garde déterministe « déjà fait » pour ne PAS rappeler l'LLM inutilement (coût).
"""
import knowledge_graph as KG


def _rel_prompt(subject, catalog):
    import json
    return (
        "Tu relies des éléments DÉJÀ connus d'un contrat, tu n'en inventes aucun. Sujet : « %s ».\n"
        "Éléments (indice, type, libellé) :\n%s\n"
        "Propose les relations PERTINENTES entre ces indices, UNIQUEMENT parmi : %s.\n"
        "Réponds en JSON strict : {\"relations\":[{\"src\":<indice>,\"dst\":<indice>,\"type\":\"<type>\","
        "\"confidence\":0..1}]}. Aucune relation inventée : si rien de sûr, liste vide."
        % (subject, json.dumps(catalog, ensure_ascii=False), ", ".join(sorted(KG.RELATION_TYPES)))
    )


def build_relations(graph, domain, subject, llm_call, max_entities=12, agent="knowledge-builder"):
    """Ajoute des relations L3 entre les entités d'un sujet. Retourne {added, skipped?}. 0 appel LLM si
    toutes les entités sont déjà reliées (garde déterministe anti-coût)."""
    ents = graph.nodes(layer=2, subject=subject, domain=domain)
    if not ents:
        return {"added": 0, "skipped": "no_entities"}
    if all(graph.edges_of(e["id"], direction="any") for e in ents):
        return {"added": 0, "skipped": "already_related"}     # rien à faire -> pas d'appel LLM
    ents = ents[:max_entities]
    catalog = [{"i": i, "type": e.get("subtype"), "label": (e.get("label") or "")[:80]} for i, e in enumerate(ents)]
    data = llm_call(_rel_prompt(subject, catalog))
    if not isinstance(data, dict):
        return {"added": 0, "skipped": "no_llm"}
    added = 0
    for r in (data.get("relations") or [])[:40]:
        try:
            si, di, rt = int(r["src"]), int(r["dst"]), str(r["type"])
        except (KeyError, ValueError, TypeError):
            continue
        if rt not in KG.RELATION_TYPES or si == di:
            continue
        if not (0 <= si < len(ents) and 0 <= di < len(ents)):
            continue
        conf = r.get("confidence", 0.5)
        conf = float(conf) if isinstance(conf, (int, float)) else 0.5
        graph.add_relation(rt, ents[si]["id"], ents[di]["id"], agent=agent, confidence=min(0.9, conf))
        added += 1
    return {"added": added}


def _explain_prompt(entity, evidences):
    return (
        "Explique brièvement, en t'appuyant UNIQUEMENT sur les preuves fournies, l'élément suivant d'un "
        "contrat d'assurance. Élément : « %s » (%s). Preuves :\n- %s\n"
        "Réponds en JSON strict : {\"aspect\":\"role\",\"explanation\":\"<2-3 phrases factuelles, sans "
        "invention>\",\"confidence\":0..1}. Si les preuves ne suffisent pas, explanation vide."
        % ((entity.get("label") or ""), entity.get("subtype"),
           "\n- ".join((e or "")[:200] for e in (evidences or [])[:4]) or "(aucune)")
    )


def build_understanding(graph, domain, subject, llm_call, max_entities=4, agent="knowledge-builder"):
    """Ajoute des explications L4 aux entités d'un sujet qui n'en ont pas. Budget borné par max_entities.
    Rien à faire (0 appel) si toutes les entités sont déjà expliquées."""
    todo = [e for e in graph.nodes(layer=2, subject=subject, domain=domain)
            if not graph.has_understanding(e["id"])]
    if not todo:
        return {"added": 0, "skipped": "all_explained"}
    evid_all = [n.get("content", {}).get("citation") for n in graph.nodes(layer=1, subject=subject, domain=domain)]
    added = 0
    for e in todo[:max_entities]:
        data = llm_call(_explain_prompt(e, evid_all))
        if isinstance(data, dict) and (data.get("explanation") or "").strip():
            conf = data.get("confidence", 0.5)
            conf = float(conf) if isinstance(conf, (int, float)) else 0.5
            graph.upsert_understanding(e["id"], data.get("aspect") or "role", data["explanation"][:800],
                                       agent=agent, confidence=min(0.9, conf))
            added += 1
    return {"added": added}
