// humanView — moteur de nettoyage d'AFFICHAGE (vue humaine). Les JSON ne sont jamais modifiés :
// seule la présentation change. La vue IA/technique garde accès à tout (voir dataView).

// Valeurs considérées comme « rien à afficher » pour un humain.
export function isEmpty(v) {
  if (v == null) return true;
  if (typeof v === "string") {
    const s = v.trim().toLowerCase();
    return s === "" || s === "null" || s === "none" || s === "undefined" || s === "nan" || s === "non renseigné" || s === "non renseigne";
  }
  if (Array.isArray(v)) return v.length === 0 || v.every(isEmpty);
  if (typeof v === "object") return Object.keys(v).length === 0 || Object.values(v).every(isEmpty);
  return false; // 0 et false sont des valeurs signifiantes
}

// Champs techniques d'une ENTRÉE : jamais rendus en vue humaine (restent en vue IA).
const TECH_FIELDS = new Set([
  "stable_id", "source_id", "detail_id", "merged_entry_id", "id", "uuid",
  "source_documents", "source_variants", "sources_liees", "champs_originaux_fusionnes",
  "fichier", "chemin", "path", "_meta", "_source", "checksum",
]);
const TECH_FIELD_RX = /(_id|_ids|_path|_paths|_ref|_refs)$|^_|^champs_originaux/;
export function isTechField(key) { return TECH_FIELDS.has(key) || TECH_FIELD_RX.test(key); }

// Sections techniques de HAUT NIVEAU d'une couche : masquées en vue humaine.
const TECH_SECTIONS = new Set([
  "circulation_information", "hierarchie_systeme", "historique_mises_a_jour", "maillage_ia",
  "restructuration_niveau_1", "zones_tampons", "index_rapide", "calibration_coremodel", "meta",
]);
const TECH_SECTION_RX = /^(_|index_)/;
export function isTechSection(key) { return TECH_SECTIONS.has(key) || TECH_SECTION_RX.test(key); }

// Champs affichés en badges (grappes de mots-clés).
export const BADGE_FIELDS = ["tags", "themes", "emotions", "patterns", "contextes", "categories", "symboles"];
// Champs de texte principal, par ordre de priorité.
export const BODY_FIELDS = ["texte_principal", "contenu", "texte", "texte_complet", "description", "resume"];
// Champs de métadonnées de la ligne d'en-tête.
export const META_FIELDS = ["date", "heure", "etat", "importance", "intensite"];

const LABELS = {
  texte_principal: "Texte", resume: "Résumé", analyse: "Analyse", commentaires_IA: "Commentaire IA",
  niveau_confiance: "Confiance", etat: "État", reves: "Rêves", entries: "Entrées",
  patterns_globaux_provisoires: "Patterns globaux", declencheurs: "Déclencheurs",
  mecanismes_globaux: "Mécanismes globaux", freins: "Freins", boucles: "Boucles",
  contradictions: "Contradictions", etats: "États", moteurs: "Moteurs",
  patterns_decisionnels: "Patterns décisionnels", regles_implicites: "Règles implicites",
  structure_profonde: "Structure profonde", personnes_citees: "Personnes citées",
  methodes_spontanees: "Méthodes spontanées", sequences_recurrentes: "Séquences récurrentes",
  methodologie: "Méthodologie", ecriture: "Écriture", projet_ecriture: "Projet écriture",
  usages_de_l_IA: "Usages de l'IA", categorie_relationnelle: "Catégorie",
};
export function label(key) {
  if (LABELS[key]) return LABELS[key];
  return String(key).replace(/_/g, " ").replace(/^./, c => c.toUpperCase());
}

// Nettoie une ENTRÉE pour la vue humaine : titre lisible, corps dédupliqué, badges, détails restants.
// Retourne { title, meta, body, extra:[{key,label,text}], badges:[{field,values}] } — uniquement du non-vide.
export function cleanEntry(e) {
  const title = firstNonEmpty([e.titre, e.title]) || excerpt(firstNonEmpty(BODY_FIELDS.map(f => e[f])), 70) || "(entrée)";
  const META_LABELS = { importance: "importance ", intensite: "intensité " };
  const meta = META_FIELDS.map(f => isEmpty(e[f]) ? null : (META_LABELS[f] || "") + e[f]).filter(Boolean).join(" · ");

  const body = firstNonEmpty(BODY_FIELDS.map(f => e[f]));
  const seen = new Set([normText(title), normText(body)]);

  // Champs texte secondaires (resume, analyse, commentaires_IA…), dédupliqués entre eux et vs le corps.
  const extra = [];
  for (const key of ["resume", "analyse", "commentaires_IA", "niveau_confiance"]) {
    const v = e[key];
    if (isEmpty(v) || typeof v !== "string") continue;
    const n = normText(v);
    if (seen.has(n)) continue; // doublon d'affichage (ex. resume === analyse)
    seen.add(n);
    extra.push({ key, label: label(key), text: v });
  }

  const badges = [];
  const seenBadges = new Set();
  for (const f of BADGE_FIELDS) {
    const vals = (Array.isArray(e[f]) ? e[f] : []).filter(v => !isEmpty(v)).map(String)
      .filter(v => { const n = normText(v); if (seenBadges.has(n)) return false; seenBadges.add(n); return true; });
    if (vals.length) badges.push({ field: f, values: vals });
  }
  return { title, meta, body: isEmpty(body) ? "" : String(body), extra, badges };
}

// Champs d'une entrée non couverts par la carte (pour la vue détail humaine), techniques exclus.
export function remainingFields(e) {
  const covered = new Set(["titre", "title", "type", ...META_FIELDS, ...BODY_FIELDS, ...BADGE_FIELDS,
    "resume", "analyse", "commentaires_IA", "niveau_confiance"]);
  return Object.keys(e)
    .filter(k => !covered.has(k) && !isTechField(k) && !isEmpty(e[k]))
    .map(k => ({ key: k, label: label(k), value: e[k] }));
}

// Sections de haut niveau d'une couche, filtrées pour la vue humaine.
export function humanSections(data) {
  return Object.keys(data)
    .filter(k => !isTechSection(k) && !isEmpty(data[k]))
    .map(k => ({ key: k, label: label(k), value: data[k] }));
}

// Copie profonde « nettoyée » d'une valeur (pour rendu structuré humain) : retire vides + techniques.
export function cleanValue(v, depth = 0) {
  if (Array.isArray(v)) {
    const a = v.map(x => cleanValue(x, depth + 1)).filter(x => !isEmpty(x));
    return a;
  }
  if (v && typeof v === "object") {
    const o = {};
    for (const k of Object.keys(v)) {
      if (isTechField(k)) continue;
      const c = cleanValue(v[k], depth + 1);
      if (!isEmpty(c)) o[k] = c;
    }
    return o;
  }
  return v;
}

// Détecte la liste d'entrées d'une couche (entries, reves, ou 1er tableau d'objets datés).
export function detectEntries(data) {
  if (Array.isArray(data)) return { key: null, list: data };
  if (Array.isArray(data.entries)) return { key: "entries", list: data.entries };
  if (Array.isArray(data.reves)) return { key: "reves", list: data.reves };
  for (const k of Object.keys(data)) {
    const v = data[k];
    if (!isTechSection(k) && Array.isArray(v) && v.length > 2 && v.every(x => x && typeof x === "object") &&
        ("date" in v[0] || "type" in v[0] || "titre" in v[0])) return { key: k, list: v };
  }
  return null;
}

function firstNonEmpty(arr) { for (const v of arr) if (!isEmpty(v) && typeof v !== "object") return v; return null; }
function normText(v) { return String(v == null ? "" : v).trim().toLowerCase().replace(/\s+/g, " "); }
export function excerpt(v, n = 70) {
  if (isEmpty(v)) return "";
  const s = String(v).trim().replace(/\s+/g, " ");
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}
