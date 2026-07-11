#!/usr/bin/env python3
"""Détection & classification de changements documentaires — déterministe, 0 token.

Distingue : nouveau document / fichier identique / nouvelle version (modification mineure vs structurante)
d'après le hash de fichier et l'évolution du ZONAGE (nombre/labels de zones). Permet une invalidation
CIBLÉE (ne retraiter que ce qui dépend du contenu modifié), sans jamais retraiter tout le corpus.

Complète corpus-explorer (qui suit déjà les zones par hash) : ici on QUALIFIE le changement pour décider
quoi invalider et quelles tâches créer.
"""

CHANGE_TYPES = ("nouveau_document", "identique", "modification_mineure", "modification_structurante")


def classify_change(prev_file_hash, new_file_hash, prev_zoning=None, new_zoning=None):
    """Qualifie le changement d'un document. Retourne un type de CHANGE_TYPES."""
    if not prev_file_hash:
        return "nouveau_document"
    if prev_file_hash == new_file_hash:
        return "identique"
    # hash différent -> version. Mineure ou structurante ? d'après le zonage.
    if prev_zoning and new_zoning:
        if len(prev_zoning) != len(new_zoning):
            return "modification_structurante"
        pl = [z.get("label") for z in prev_zoning]
        nl = [z.get("label") for z in new_zoning]
        if pl != nl:
            return "modification_structurante"
        # mêmes labels/nombre mais bornes de pages changées -> structurante légère
        pr = [(z.get("start"), z.get("end")) for z in prev_zoning]
        nr = [(z.get("start"), z.get("end")) for z in new_zoning]
        if pr != nr:
            return "modification_structurante"
    return "modification_mineure"


def zones_to_invalidate(prev_zoning, new_zoning):
    """Zones dont le contenu a changé (à ré-explorer) — comparaison par (label, bornes). Invalidation
    CIBLÉE : on ne touche pas aux zones inchangées."""
    prev = {(z.get("label"), z.get("start"), z.get("end")) for z in (prev_zoning or [])}
    changed = []
    for z in (new_zoning or []):
        key = (z.get("label"), z.get("start"), z.get("end"))
        if key not in prev:
            changed.append(z)
    return changed


def tasks_for_change(doc_id, change_type, changed_zones):
    """Tâches CIBLÉES selon la nature du changement. Un doc identique => aucune tâche (pas de retraitement)."""
    if change_type == "identique":
        return []
    if change_type == "nouveau_document":
        return [{"type": "explorer", "doc_id": doc_id, "reason": "nouveau document à cartographier", "priority": 4}]
    tasks = []
    for z in changed_zones:
        tasks.append({"type": "reexaminer_zone", "doc_id": doc_id,
                      "zone": "%s:%s-%s" % (z.get("label"), z.get("start"), z.get("end")),
                      "reason": "zone modifiée (%s)" % change_type, "priority": 3})
    if change_type == "modification_structurante":
        tasks.append({"type": "marquer_obsolete", "doc_id": doc_id,
                      "reason": "structure modifiée : connaissances dépendantes potentiellement obsolètes",
                      "priority": 4})
    return tasks
