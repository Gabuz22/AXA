#!/usr/bin/env python3
"""Moteur GÉNÉRIQUE d'exploration de corpus — « Qu'est-ce que la base de connaissance ne sait pas encore ? »

Indépendant de tout domaine (AXA n'en est que la 1re application). Aucune dépendance réseau/LLM :
la nuance LLM est *injectable* (llm_fn), sinon l'analyse reste déterministe. Aucune I/O produit :
seule la CoverageMap lit/écrit son propre fichier d'état.

Principe : cartographier un document → le découper en zones logiques → comparer chaque zone à la
connaissance existante → classer sa couverture → produire des tâches typées. Une carte de couverture
persistante (hash par zone) évite de retraiter une zone inchangée : le système lit de moins en moins.

Réutilisable pour : notices d'assurance, corpus juridique, doc technique, toute base documentaire.
"""
import hashlib
import re
import unicodedata

# Niveaux de couverture d'une zone (du moins connu au plus sûr / au problème).
LEVELS = ("non_couverte", "partielle", "obsolete", "contradictoire", "couverte", "non_pertinente")
# Sévérité pour l'ordonnancement « le moins connu d'abord » (plus grand = à explorer en priorité).
_SEVERITY = {"non_couverte": 5, "contradictoire": 4, "obsolete": 4, "partielle": 3,
             "non_pertinente": 1, "couverte": 0}


def _strip_accents(t):
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def norm(t):
    """Normalisation robuste pour comparaison lexicale : minuscules, sans accents, espaces compactés."""
    return re.sub(r"\s+", " ", _strip_accents((t or "").lower())).strip()


def content_hash(text):
    """Empreinte stable d'un contenu (détecte toute modification). Sur le texte NORMALISÉ des espaces
    uniquement (une re-extraction PDF ne change pas le hash pour un contenu identique)."""
    canon = re.sub(r"\s+", " ", (text or "")).strip()
    return "h_" + hashlib.sha256(canon.encode("utf-8")).hexdigest()[:20]


# ------------------------------------------------------------------ cartographie & zonage
def cartography(pages, label_rules, default_label="contenu"):
    """pages: {no:int -> texte}. label_rules: [(label, [mots-cles])] ordonné. Retourne {no -> label}.
    Heuristique simple assumée : le label dont les mots-clés apparaissent le plus. Aucune prétention
    d'exactitude — on cherche une PREMIÈRE structure."""
    out = {}
    for no, text in pages.items():
        low = norm(text)
        best, score = default_label, 0
        for label, kws in label_rules:
            s = sum(low.count(norm(k)) for k in kws)
            if s > score:
                best, score = label, s
        out[int(no)] = best if score > 0 else default_label
    return out


def segment_zones(carto):
    """Fusionne les pages consécutives de même label en zones logiques. Retourne une liste ordonnée
    [{label, start, end, pages:[...]}]."""
    zones = []
    for no in sorted(carto):
        label = carto[no]
        if zones and zones[-1]["label"] == label and no == zones[-1]["end"] + 1:
            zones[-1]["end"] = no
        else:
            zones.append({"label": label, "start": no, "end": no})
    for z in zones:
        z["pages"] = list(range(z["start"], z["end"] + 1))
    return zones


def zone_key(doc_id, zone):
    return "%s#%s:%d-%d" % (doc_id, zone["label"], zone["start"], zone["end"])


def zone_text(pages, zone):
    return "\n".join((pages.get(p) or pages.get(str(p)) or "") for p in zone["pages"])


def zone_signature(pages, zone):
    return content_hash(zone_text(pages, zone))


# ------------------------------------------------------------------ extraction de termes saillants
_DEF_PATTERNS = [
    re.compile(r"[«\"]\s*([A-ZÀ-Ý][^«»\"]{2,40})\s*[»\"]"),                 # « Terme »
    re.compile(r"(?m)^\s*([A-ZÀ-Ý][\wÀ-ÿ' -]{2,40})\s*:"),                  # Terme : ...
    re.compile(r"on entend par\s+[«\"]?([\wÀ-ÿ' -]{3,40})", re.I),           # on entend par X
]


def salient_terms(text, extra_lexicon=None, limit=40):
    """Termes potentiellement PORTEURS de sens dans une zone (générique) : termes définis (« X », X :,
    'on entend par X'), suites en Capitales, + un lexique de domaine injecté. Sert à repérer ce qui
    pourrait être NOUVEAU (absent de la connaissance)."""
    terms = set()
    for pat in _DEF_PATTERNS:
        for m in pat.findall(text or ""):
            t = m.strip(" .;,")
            if 2 < len(t) <= 40:
                terms.add(t)
    for m in re.findall(r"\b([A-ZÀ-Ý][a-zà-ÿ]+(?:\s+[A-ZÀ-Ý][a-zà-ÿ]+){0,3})\b", text or ""):
        if len(m) > 3:
            terms.add(m.strip())
    for w in (extra_lexicon or []):
        if norm(w) in norm(text or ""):
            terms.add(w)
    # priorise les plus longs (plus spécifiques), borne la sortie
    return sorted(terms, key=lambda s: (-len(s), s))[:limit]


# ------------------------------------------------------------------ évaluation de couverture
def assess_zone(ztext, known_terms, expected_terms=None, domain_lexicon=None, llm_fn=None):
    """Compare une zone à la connaissance existante. Déterministe par défaut ; raffiné si llm_fn fourni.

    known_terms    : vocabulaire DÉJÀ connu (ce que la base sait) — pour mesurer le recouvrement.
    expected_terms : termes qu'on s'attendrait à trouver pour ce type de zone (détection d'absence ciblée).
    domain_lexicon : lexique de domaine (aide à repérer les termes saillants).
    Retour : {level, confidence, knowledge_covered[], knowledge_absent[], knowledge_suspect[]}."""
    low = norm(ztext)
    substantial = len(low) >= 120
    known_norm = {norm(k): k for k in (known_terms or []) if norm(k)}
    covered = [known_norm[k] for k in known_norm if k in low]
    salient = salient_terms(ztext, domain_lexicon)
    # « absent » = saillant dans la zone mais inconnu de la base -> ce que la base ne connaît pas encore.
    absent = [t for t in salient if norm(t) not in known_norm]
    missing_expected = [t for t in (expected_terms or []) if norm(t) not in low]
    suspect = []

    if not substantial:
        level, conf = "non_pertinente", 0.4
    elif not covered and absent:
        level, conf = "non_couverte", 0.55
    elif covered and (absent or missing_expected):
        level, conf = "partielle", 0.6
    elif covered:
        level, conf = "couverte", 0.7
    else:
        level, conf = "non_pertinente", 0.45

    result = {"level": level, "confidence": conf,
              "knowledge_covered": covered[:30], "knowledge_absent": absent[:30],
              "knowledge_suspect": suspect}

    if llm_fn is not None:
        refined = llm_fn(ztext, result)          # peut renvoyer {level, confidence, absent[], suspect[]}
        if isinstance(refined, dict):
            if refined.get("level") in LEVELS:
                result["level"] = refined["level"]
            if isinstance(refined.get("confidence"), (int, float)):
                result["confidence"] = round(min(0.95, max(0.3, float(refined["confidence"]))), 3)
            for k_src, k_dst in (("absent", "knowledge_absent"), ("suspect", "knowledge_suspect"),
                                 ("covered", "knowledge_covered")):
                v = refined.get(k_src)
                if isinstance(v, list):
                    merged = list(dict.fromkeys(list(result[k_dst]) + [str(x)[:80] for x in v]))
                    result[k_dst] = merged[:30]
    return result


# ------------------------------------------------------------------ carte de couverture persistante
class CoverageMap:
    """État persistant : par corpus (doc_id) et par zone, ce qui est connu/absent/suspect + hash.
    Permet à un agent de savoir « je n'ai jamais analysé cette zone » sans tout relire. Résilient :
    chaque mise à jour peut être sauvegardée immédiatement (aucune perte si le cycle s'interrompt)."""

    def __init__(self, path, load_json=None, write_json=None):
        self.path = path
        self._write = write_json
        data = None
        if load_json is not None:
            try:                                 # tolère l'absence de fichier (1er passage) sans dépendre
                data = load_json(path, default=None)   # de la convention 'default' de l'appelant
            except Exception:
                data = None
        self.data = data or {"version": "1.0.0", "corpora": {}, "updated_at": None}
        self.data.setdefault("corpora", {})

    def _doc(self, doc_id):
        return self.data["corpora"].setdefault(doc_id, {"doc_hash": None, "zoning": None,
                                                         "zones": {}, "updated_at": None})

    # --- zonage mis en cache par hash de document (évite de re-parser un PDF inchangé) ---
    def cached_zoning(self, doc_id, doc_hash):
        d = self.data["corpora"].get(doc_id)
        if d and d.get("doc_hash") == doc_hash and d.get("zoning"):
            return d["zoning"]
        return None

    def cache_zoning(self, doc_id, doc_hash, zones):
        d = self._doc(doc_id)
        if d.get("doc_hash") != doc_hash:
            d["doc_hash"] = doc_hash
            d["zoning"] = zones
            # un document modifié rend suspectes les zones jadis couvertes dont on ignore encore le hash
        else:
            d["zoning"] = zones

    def zone_state(self, doc_id, zkey):
        return self.data["corpora"].get(doc_id, {}).get("zones", {}).get(zkey)

    def needs_exploration(self, doc_id, zkey, signature):
        """Vrai UNIQUEMENT si la zone n'a jamais été analysée, ou si son contenu a changé (hash différent).
        Une zone déjà analysée au contenu identique n'est JAMAIS retraitée (analyse déterministe = même
        résultat ; économie de quota). La re-analyse d'une zone non résolue passe par un changement de
        contenu (obsolescence) ou une future montée de version de connaissance."""
        st = self.zone_state(doc_id, zkey)
        if not st:
            return True
        return st.get("content_hash") != signature

    def update_zone(self, doc_id, zkey, pages, level, confidence, content_hash, last_agent,
                    covered, absent, suspect, date):
        d = self._doc(doc_id)
        prev = d["zones"].get(zkey)
        # une zone jadis COUVERTE dont le contenu a changé devient 'obsolete' (à re-vérifier).
        # (une zone qui PASSE de non-couverte à couverte n'est pas obsolète : c'est un progrès.)
        if prev and prev.get("level") == "couverte" and prev.get("content_hash") not in (None, content_hash):
            level = "obsolete"
        d["zones"][zkey] = {
            "date": date, "pages": pages, "level": level, "confidence": round(float(confidence), 3),
            "last_agent": last_agent, "content_hash": content_hash,
            "knowledge_covered": covered, "knowledge_absent": absent, "knowledge_suspect": suspect,
            "times_seen": (prev.get("times_seen", 0) + 1) if prev else 1,
        }
        d["updated_at"] = date
        self.data["updated_at"] = date
        return d["zones"][zkey]

    def coverage_ratio(self, doc_id):
        zones = self.data["corpora"].get(doc_id, {}).get("zones", {})
        if not zones:
            return 0.0
        good = sum(1 for z in zones.values() if z.get("level") in ("couverte", "non_pertinente"))
        return round(good / len(zones), 3)

    def global_ratio(self):
        allz = [z for d in self.data["corpora"].values() for z in d.get("zones", {}).values()]
        if not allz:
            return 0.0
        good = sum(1 for z in allz if z.get("level") in ("couverte", "non_pertinente"))
        return round(good / len(allz), 3)

    def save(self, updated_at=None):
        if self._write is None:
            return
        if updated_at:
            self.data["updated_at"] = updated_at
        self._write(self.path, self.data)


# ------------------------------------------------------------------ sélection « le moins connu d'abord »
def rank_targets(coverage_map, catalog, max_targets):
    """catalog : [{doc_id, zone}] candidats (zones connues du zonage). Ordonne par : jamais vues d'abord,
    puis par sévérité de l'état, puis les plus anciennes. Exclut les zones 'couverte'/'non_pertinente'
    inchangées (rien à y gagner). Retourne au plus max_targets cibles."""
    scored = []
    for c in catalog:
        st = coverage_map.zone_state(c["doc_id"], zone_key(c["doc_id"], c["zone"]))
        if st and st.get("level") in ("couverte", "non_pertinente"):
            continue                                   # déjà couverte -> on n'y revient pas
        never = 0 if st else 1
        sev = _SEVERITY.get(st.get("level"), 5) if st else 6
        last = (st or {}).get("date") or ""
        scored.append(((never, sev, _neg_date(last)), c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:max_targets]]


def _neg_date(iso):
    # plus ancien d'abord : on inverse l'ordre lexicographique des dates ISO.
    return tuple(-ord(ch) for ch in iso[:19]) if iso else (1,)


# ------------------------------------------------------------------ génération de tâches typées
TASK_TYPES = ("definition", "condition", "declencheur", "comparaison", "verification",
              "contradiction", "complement", "relecture", "mise_a_jour")

# Correspondance label de zone -> type de tâche « catégorie » naturel.
_LABEL_TASK = {"definitions": "definition", "conditions": "condition", "declencheurs": "declencheur"}


def generate_tasks(doc_id, zone, assessment, agent_id):
    """Produit des tâches TYPÉES (pas seulement definition/condition) à partir de l'évaluation d'une zone.
    L'orchestrateur décidera lesquelles lancer. Ids stables (dédup naturelle)."""
    level = assessment["level"]
    zkey = zone_key(doc_id, zone)
    out = []

    def mk(ttype, reason, priority):
        tid = "cx_" + hashlib.sha256(("%s|%s|%s" % (doc_id, zkey, ttype)).encode("utf-8")).hexdigest()[:16]
        return {"task_id": tid, "type": ttype, "doc_id": doc_id, "zone": zkey,
                "label": zone["label"], "pages": [zone["start"], zone["end"]],
                "reason": reason[:240], "priority": priority, "origin_agent": agent_id}

    if level == "non_couverte":
        cat = _LABEL_TASK.get(zone["label"])
        if cat:
            out.append(mk(cat, "Zone %s non couverte : extraire les %s absents." % (zkey, zone["label"]), 4))
        out.append(mk("complement", "Contenu absent de la connaissance : %d terme(s) nouveau(x)."
                      % len(assessment.get("knowledge_absent", [])), 4))
    elif level == "partielle":
        out.append(mk("complement", "Zone partiellement couverte : compléter les éléments manquants.", 3))
        out.append(mk("verification", "Vérifier la cohérence des éléments déjà connus de cette zone.", 2))
    elif level == "obsolete":
        out.append(mk("mise_a_jour", "Le contenu de la zone a changé depuis la dernière analyse.", 4))
        out.append(mk("relecture", "Relire la zone modifiée pour mettre à jour la connaissance.", 3))
    elif level == "contradictoire":
        out.append(mk("contradiction", "Contradiction détectée entre la zone et la connaissance existante.", 5))
        out.append(mk("verification", "Arbitrer la contradiction (source documentaire faisant foi).", 4))

    # Comparaison inter-documents pertinente pour les zones structurantes.
    if level in ("non_couverte", "partielle") and zone["label"] in ("garanties", "exclusions", "conditions"):
        out.append(mk("comparaison", "Comparer cette zone aux mêmes zones des autres contrats (déséquilibre).", 2))
    return out
