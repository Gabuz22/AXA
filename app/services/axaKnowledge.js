// axaKnowledge — service de connaissances AXA piloté par MANIFESTE (V1.3, évolutif).
// Le module ne connaît que des RÔLES ("pdf_index", "formules"…) ; le manifeste
// data/AXA/workspace_manifest.json fait correspondre rôle → fichier. Nouvelle version
// d'un master = mise à jour du manifeste, zéro changement de code. Rôle absent ou
// fichier manquant = dégradation propre (null), jamais d'erreur bloquante.

const AXA_BASE = "../data/AXA/";
const MANIFEST_URL = AXA_BASE + "workspace_manifest.json";
const HISTORY_LS = "gv_axa_history_v1";

// Filet de sécurité si le manifeste disparaît : rôles essentiels connus.
const FALLBACK_MANIFEST = {
  sources: {
    index_global: { path: "ia/axa_index_global.json" },
    contrats_resume_humain: { path: "vue_humaine/axa_contrats_resume_humain.json" },
    comparatif: { path: "vue_humaine/tableau_comparatif.json" },
    contrats_index: { path: "contrats/contrats_index.json" },
    pdf_index: { path: "ia/axa_pdf_index.json" },
  },
  formulaires_pages: [],
};

let _manifest = null;
const _cache = new Map();

export async function manifest(force = false) {
  if (_manifest && !force) return _manifest;
  try {
    const r = await fetch(MANIFEST_URL, { cache: "no-store" });
    _manifest = r.ok ? await r.json() : FALLBACK_MANIFEST;
  } catch { _manifest = FALLBACK_MANIFEST; }
  return _manifest;
}

// Charge une source par rôle. format "markdown" → texte ; sinon JSON. null si indisponible.
export async function source(role) {
  if (_cache.has(role)) return _cache.get(role);
  const m = await manifest();
  const decl = m.sources?.[role];
  let out = null;
  if (decl?.path) {
    try {
      const r = await fetch(AXA_BASE + decl.path, { cache: "no-store" });
      if (r.ok) out = decl.format === "markdown" ? await r.text() : await r.json();
    } catch { out = null; }
  }
  _cache.set(role, out);
  return out;
}
export function clearCache() { _cache.clear(); _manifest = null; _axaIndex = null; _masterItems = null; _bItems = null; _canonNames = null; }
// URL d'un fichier source du manifeste (chemin relatif à data/AXA/) — pour téléchargement/ouverture.
export function fileUrl(path) { return AXA_BASE + String(path).replace(/^\/?/, ""); }
// Chemins du pdf_index relatifs à la racine du dépôt, avec règles de réécriture du manifeste
// (l'index peut référencer une arborescence historique — le manifeste fait la correspondance).
export function pdfUrl(path) {
  let p = String(path).replace(/^\/?/, "");
  for (const rw of _manifest?.pdf_path_rewrites || []) {
    if (rw.from && p.startsWith(rw.from)) { p = rw.to + p.slice(rw.from.length); break; }
  }
  return "../" + p;
}

/* ---------- Recherche globale (sources légères, générique par rôle) ---------- */
// Chaque extracteur transforme une source en éléments cherchables {type, label, text, contrat, ref}.
const SEARCH_EXTRACTORS = {
  contrats_resume_humain: d => (d?.contrats || []).flatMap(c => [
    { type: "contrat", label: c.nom, text: [c.nom, c.famille, c.resume_neutre].join(" "), contrat: c.nom, ref: "#/axa/contrat" },
    ...["garanties_principales", "exclusions_importantes", "options", "points_de_vigilance", "cotisations_prix", "fiscalite", "delais_franchises"].flatMap(k =>
      (c[k] || []).map(f => ({ type: k.replace(/_/g, " "), label: f.titre || "", text: [f.titre, f.resume_humain].filter(Boolean).join(" — "), contrat: c.nom, ref: "#/axa/contrat" }))),
  ]),
  formules: d => (d?.formules || []).map(f => ({ type: "formule", label: f.nom, text: [f.nom, f.usage, f.formule, f.description].filter(Boolean).join(" — "), contrat: f.contrat, ref: "#/axa/sources" })),
  pdf_index: d => (d?.pdfs || []).map(p => ({ type: "pdf", label: p.nom_fichier, text: [p.nom_contrat, p.type_document, p.nom_fichier].join(" "), contrat: p.nom_contrat, ref: "#/axa/pdf" })),
  contrats_index: d => (d?.contrats || []).map(c => ({ type: "contrat (JSON enrichi)", label: c.nom, text: [c.nom, c.famille, c.slug].join(" "), contrat: c.nom, ref: "#/axa/contrat" })),
  // Évolution ① : la couche dérivée de Pack A (définitions, conditions de souscription,
  // déclencheurs/plafonds/franchises) devient cherchable — jusqu'ici invisible pour la recherche.
  fiches_conseiller: d => (d?.contrats || []).flatMap(c => [
    ...(c.definitions || []).map(x => ({ type: "définition", label: x.terme, text: [x.terme, x.definition].filter(Boolean).join(" — "), contrat: c.nom, ref: "#/axa/contrat" })),
    ...(c.conditions_souscription || []).map(x => ({ type: "condition de souscription", label: c.nom, text: x.texte || "", contrat: c.nom, ref: "#/axa/contrat" })),
    ...(c.faits || []).filter(f => f.declencheurs.length || f.plafonds.length || f.franchises.length || f.description)
      .map(f => ({ type: f.categorie, label: f.titre, contrat: c.nom, ref: "#/axa/contrat",
        text: [f.titre, f.description, ...(f.declencheurs || []), ...(f.plafonds || []), ...(f.franchises || [])].filter(Boolean).join(" — ") })),
  ]),
};

// Extraction générique et bornée du master Pack A (branches de connaissance, pas les 5 Mo entiers).
const MASTER_BRANCHES = ["index_rapide", "arbres_decision", "sources_officielles_et_regles_publiques", "regles_transverses_et_garde_fous", "comparaisons"];
function walkMaster(d) {
  const out = []; let n = 0;
  const walk = (v, trail) => {
    if (n > 4000 || v == null) return;
    if (typeof v === "string") {
      if (v.length > 25) { out.push({ type: "master A · " + trail[0].replace(/_/g, " "), label: trail.slice(-1)[0].replace(/_/g, " "), text: v, contrat: "", ref: "#/axa/sources" }); n++; }
      return;
    }
    if (Array.isArray(v)) { v.forEach(x => walk(x, trail)); return; }
    if (typeof v === "object") for (const k of Object.keys(v)) walk(v[k], [...trail, k]);
  };
  for (const b of MASTER_BRANCHES) if (d?.[b]) walk(d[b], [b]);
  return out;
}
let _masterItems = null;

/* ---------- Pack B : RAISONNEMENT (aide à décider, JAMAIS une preuve) ----------
   Copilote (Phase 6) : Pack A = preuve contractuelle ; Pack B = raisonnement.
   On extrait, de façon bornée, les branches de raisonnement de Pack B (arbres de décision,
   règles transverses/garde-fous, modèles de réponse, raisonnements complexes, matrices) et on
   les classe par simple recouvrement de tokens (transparent — aucune donnée inventée, aucun LLM). */
const B_BRANCHES = {
  arbres_decision: "arbre de décision",
  raisonnements_complexes: "raisonnement",
  regles_transverses_et_garde_fous: "règle transverse / garde-fou",
  modeles_reponse_par_question: "modèle de réponse",
  matrices_croisement_avance: "matrice de croisement",
};
function walkB(d) {
  const out = []; let n = 0;
  const walk = (v, trail) => {
    if (n > 3000 || v == null) return;
    if (typeof v === "string") {
      if (v.length > 30) { out.push({ branch: trail[0], label: trail.slice(-1)[0].replace(/_/g, " "), path: trail.join(" › "), text: v }); n++; }
      return;
    }
    if (Array.isArray(v)) { v.forEach(x => walk(x, trail)); return; }
    if (typeof v === "object") for (const k of Object.keys(v)) walk(v[k], [...trail, k]);
  };
  for (const b of Object.keys(B_BRANCHES)) if (d?.[b]) walk(d[b], [b]);
  return out;
}
let _bItems = null;
// reasoningB(query) → items Pack B pertinents [{branch, branchLabel, label, path, text, score}].
export async function reasoningB(query) {
  const raw = String(query || "").trim();
  if (raw.length < 2) return [];
  if (!_bItems) {
    const b = await source("master_pack_b");
    _bItems = b ? walkB(b) : [];
    for (const it of _bItems) it._toks = new Set(tok(it.label + " " + it.text));
  }
  const base = [...new Set(tok(raw))];
  if (!base.length) return [];
  const terms = expand(base);
  const scored = [];
  for (const it of _bItems) {
    let hit = 0, baseHit = 0;
    for (const t of terms) if (it._toks.has(t)) hit++;
    if (!hit) continue;
    for (const t of base) if (it._toks.has(t)) baseHit++;
    scored.push({ branch: it.branch, branchLabel: B_BRANCHES[it.branch], label: it.label, path: it.path, text: it.text, score: hit + 2 * baseHit });
  }
  scored.sort((a, b2) => b2.score - a.score);
  return scored.slice(0, 8);
}

/* ---------- Recherche AXA v2 : tokenisée BM25 + synonymes + filtres (2026-07-07) ----------
   Réutilise la logique BM25 du RAG (k1=1.5, b=0.75, stopwords, boost de couverture) appliquée
   aux items des extracteurs + master Pack A. Tolérante (mots, accents, pluriels simples),
   triée par pertinence. Repli substring conservé si l'index n'est pas prêt. */

// Dictionnaire de synonymes métier — transparent et maintenable. Chaque terme d'une ligne
// est étendu aux autres à la recherche (bidirectionnel). Aucune donnée inventée : simple rappel.
export const SYNONYMES = [
  ["carence", "delai", "delais", "franchise", "attente"],
  ["accident", "accidentel", "accidentelle"],
  ["deces", "capital deces", "mortalite"],
  ["invalidite", "ipt", "ipp", "ptia", "incapacite"],
  ["rachat", "valeur de rachat", "rachetable"],
  ["adhesion", "souscription", "souscrire", "adherer"],
  ["plafond", "limite", "montant maximum", "maximum", "plafonnement"],
  ["cotisation", "prime", "tarif", "prix"],
  ["beneficiaire", "clause beneficiaire"],
  ["exclusion", "exclu", "non couvert", "ne couvre pas"],
  ["garantie", "couverture", "prise en charge"],
  ["fiscalite", "fiscal", "impot", "impots", "abattement"],
];
const STOP = new Set("au aux avec ce ces dans de des du elle en et eux il je la le les leur lui ma mais me meme mes moi mon ne nos notre nous on ou par pas pour qu que qui sa se ses son sur ta te tes toi ton tu un une vos votre vous est sont ete etre plus tres cette cet comme quand".split(" "));
const norm = s => String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
const tok = s => (norm(s).match(/[a-z0-9]{2,}/g) || []).filter(t => !STOP.has(t));
// Étend une liste de tokens avec les synonymes (tokenisés) des lignes qui matchent.
function expand(terms) {
  const set = new Set(terms);
  for (const line of SYNONYMES) {
    const lineToks = line.flatMap(tok);
    if (terms.some(t => lineToks.includes(t))) lineToks.forEach(t => set.add(t));
  }
  return [...set];
}

// Nom canonique de contrat (dédup « Masterlife CREDIT » vs « MasterLife Credit ») :
// clé = nom normalisé sans espaces/accents/casse → forme de référence (resume_humain).
const nameKey = s => norm(s).replace(/[^a-z0-9]/g, "");
let _canonNames = null;
function canonContrat(name) {
  if (!name || !_canonNames) return name;
  return _canonNames.get(nameKey(name)) || name;
}

let _axaIndex = null; // { items:[{...,_toks,_dl}], df:Map, N, avgdl }
async function buildIndex(includeMaster) {
  const rh = await source("contrats_resume_humain");
  _canonNames = new Map();
  for (const c of (rh?.contrats || [])) if (c.nom) _canonNames.set(nameKey(c.nom), c.nom); // forme de référence
  const items = [];
  for (const [role, extract] of Object.entries(SEARCH_EXTRACTORS)) {
    const d = await source(role);
    if (d) for (const it of extract(d)) items.push(it);
  }
  if (includeMaster) {
    if (!_masterItems) { const a = await source("master_pack_a"); _masterItems = a ? walkMaster(a) : []; }
    for (const it of _masterItems) items.push(it);
  }
  const df = new Map(); let total = 0;
  for (const it of items) {
    const toks = tok((it.label || "") + " " + (it.label || "") + " " + it.text); // label pèse double
    it._toks = toks; it._dl = toks.length; total += toks.length;
    for (const t of new Set(toks)) df.set(t, (df.get(t) || 0) + 1);
  }
  _axaIndex = { items, df, N: items.length, avgdl: items.length ? total / items.length : 1 };
  return _axaIndex;
}
export function clearSearchIndex() { _axaIndex = null; _masterItems = null; _bItems = null; }

// searchAll(query, { includeMaster, types }) — types : sous-ensemble de catégories à garder.
export async function searchAll(query, { includeMaster = true, types = null } = {}) {
  const raw = String(query || "").trim();
  if (raw.length < 2) return [];
  const idx = _axaIndex || await buildIndex(includeMaster);

  const baseTerms = [...new Set(tok(raw))];
  if (!baseTerms.length) return [];
  const terms = expand(baseTerms);
  const k1 = 1.5, b = 0.75;
  const scored = [];
  for (const it of idx.items) {
    if (types && types.length && !types.includes(it.type)) continue;
    const tf = new Map();
    for (const t of it._toks) if (terms.includes(t)) tf.set(t, (tf.get(t) || 0) + 1);
    if (!tf.size) continue;
    let score = 0, coveredBase = 0;
    for (const [t, f] of tf) {
      const n = idx.df.get(t) || 1;
      const idf = Math.log(1 + (idx.N - n + 0.5) / (n + 0.5));
      score += idf * (f * (k1 + 1)) / (f + k1 * (1 - b + b * it._dl / idx.avgdl));
      if (baseTerms.includes(t)) coveredBase++;
    }
    score *= 1 + 0.6 * (coveredBase / baseTerms.length);        // boost couverture (termes saisis)
    if (/^master /.test(it.type || "")) score *= 0.3;           // items master = raisonnement/sources, pas des faits contractuels → dévalués
    scored.push({ ...it, score, contrat: canonContrat(it.contrat) });
  }
  // Repli : si BM25 ne trouve rien, tenter la sous-chaîne exacte (comportement historique).
  if (!scored.length) {
    const q = norm(raw);
    for (const it of idx.items) {
      if (types && types.length && !types.includes(it.type)) continue;
      if (norm(it.text).includes(q) || norm(it.label).includes(q)) scored.push({ ...it, score: 1 });
    }
  }
  scored.sort((a, b2) => b2.score - a.score);
  recordSearch(query, scored.length);
  return scored.slice(0, 80);
}

// Types de résultats présents dans l'index (pour les filtres UI).
export async function searchTypes({ includeMaster = true } = {}) {
  const idx = _axaIndex || await buildIndex(includeMaster);
  const counts = {};
  for (const it of idx.items) counts[it.type] = (counts[it.type] || 0) + 1;
  return counts;
}

/* ---------- Historique des recherches ---------- */
export function history() { try { return JSON.parse(localStorage.getItem(HISTORY_LS))?.items || []; } catch { return []; } }
export function recordSearch(query, count) {
  const items = history().filter(h => h.q !== query).slice(0, 49);
  items.unshift({ q: query, n: count, at: new Date().toISOString() });
  try { localStorage.setItem(HISTORY_LS, JSON.stringify({ items })); } catch {}
}
export function clearHistory() { try { localStorage.removeItem(HISTORY_LS); } catch {} }
