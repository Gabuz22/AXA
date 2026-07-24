// /api/preselection — Cloudflare Pages Function.
//
// POURQUOI CE FICHIER EXISTE : la Vue IA (data/AXA/ia/*) est un ensemble de pages STATIQUES —
// GitHub Pages ne peut qu'en servir la lecture. Une IA qui lit le barème de présélection
// (pondérations 0,25/0,30/0,20/0,15/0,10…) doit alors RÉ-APPLIQUER elle-même la formule, en
// probabiliste : elle peut mal pondérer, mal croiser l'âge et la plage d'adhésion. Cet endpoint
// EXÉCUTE réellement le moteur — l'IA récupère un résultat déjà calculé, garanti exact, au lieu
// d'en produire une approximation.
//
// C'est un PORT FIDÈLE de app/services/axaPreselection.js (même barème, mêmes 5 correctifs
// documentés dans ce fichier, aucune logique réinventée) — adapté pour lire les données du MÊME
// déploiement via env.ASSETS (aucun appel réseau externe, aucune dépendance à GitHub Pages).
//
// GARDE-FOUS NON NÉGOCIABLES :
//   • Lecture seule. Cette fonction n'écrit JAMAIS — ni dans les données, ni dans les mères.
//   • Aucune donnée nominative acceptée en paramètre (rejetée explicitement, voir validateInput).
//   • Chaque résultat reste sourcé (notice + page) — l'exécution ne remplace pas la citation.
//   • La rémunération conseiller n'entre jamais dans le calcul (hérité du barème).
//   • Si une donnée source manque, on répond une erreur explicite — jamais une valeur inventée.

const VERSION_FALLBACK = "dev";

const CATS = ["garanties_principales", "exclusions_importantes", "options", "cotisations_prix",
  "delais_franchises", "fiscalite", "points_de_vigilance"];
const CATS_POSITIVES = CATS.filter(k => k !== "exclusions_importantes" && k !== "points_de_vigilance");

const norm = s => String(s ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const cleNom = n => String(n || "").replace(/\(.*?\)/g, "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]/g, "");
const clamp = (v, min = 0, max = 100) => Math.min(max, Math.max(min, v));
const arrondi = v => Math.round(v * 10) / 10;

const BAREME_SECOURS = {
  weights: { eligibilite: 0.25, besoins_couverts: 0.3, importance_besoins: 0.2, budget: 0.15, confiance: 0.1 },
  eligibilite: { probable: 95, a_verifier: 65, incertaine: 40, exclue: 0 },
  budget_scores: { dans_budget: 100, dans_marge: 80, hors_budget: 20, tarif_a_verifier: 55 },
  budget: { marge_pourcentage_defaut: 10 },
  display: { max_results_default: 5, score_minimum: 45 },
  confidence: { tarif_inconnu_penalite: 10, eligibilite_inconnue_penalite: 10 },
  need_keywords: {},
  meta: { remuneration_incluse_dans_scoring: false },
};

// Vocabulaire public des besoins acceptés en paramètre — identique à celui du produit conseiller
// (matrice métier), seul vocabulaire qui rattache un besoin à des contrats de façon curée (pas du
// simple recouvrement de mots-clés).
const RISQUE_BESOIN = {
  emprunt: "assurance_emprunteur", deces_protection_famille: "proteger_famille",
  arret_travail_itt: "arret_travail", invalidite: "invalidite", accident_vie_privee: null,
  education_enfants: "proteger_famille", dependance: null, obseques: "obseques_rapatriement",
  retraite_revenu: "retraite", epargne_transmission: "transmission",
};

const phrases = t => String(t).split(/[.;]/).map(p => p.trim()).filter(Boolean);
const tousLes = (re, s) => [...s.matchAll(new RegExp(re.source, "g"))];
const R_PLAGE = /(?:de|entre)\s+(\d{1,2})\s+(?:a|et)\s+(\d{1,2})\s+ans/g;
const R_MAX = /(?:moins de|avant|au plus|jusqu'?a(?:ux)?|maximum de|<)\s*(\d{1,2})\s*ans/g;
const R_MIN = /(?:plus de|a partir de|au moins|minimum de|des l'age de|>)\s*(\d{1,2})\s*ans/g;
const CTX_ENTREE = /souscri|adhesion|adherent|adherer|signature|entree|conditions cumulatives|age (?:minimum|maximum|limite)|etre age/;

function evaluerEligibilite(fiche, criteres, bar) {
  const raisons = []; const preuves = [];
  let exclusionFerme = false, indice = false, reserve = false;
  const age = criteres.age;
  if (age !== null && age !== undefined && fiche) {
    for (const cond of (fiche.conditions_souscription || [])) {
      const src = cond.source || {};
      for (const p of phrases(norm(cond.texte))) {
        if (!/\d{1,2}\s*ans/.test(p)) continue;
        const plages = tousLes(R_PLAGE, p);
        if (plages.length) {
          indice = true;
          const ok = plages.some(m => age >= Number(m[1]) && age <= Number(m[2]));
          preuves.push({ phrase: p, doc: src.document_source, page: src.page, section: src.section });
          if (!ok) { exclusionFerme = true; raisons.push(`Âge ${age} hors de la plage d'adhésion documentée (${plages.map(m => `${m[1]}–${m[2]} ans`).join(", ")}).`); }
          else raisons.push(`Âge ${age} dans la plage d'adhésion documentée (${plages.map(m => `${m[1]}–${m[2]} ans`).join(", ")}).`);
          continue;
        }
        if (!CTX_ENTREE.test(p)) continue;
        const maxs = tousLes(R_MAX, p).map(m => Number(m[1])).filter(v => v >= 16);
        const mins = tousLes(R_MIN, p).map(m => Number(m[1])).filter(v => v >= 0 && v <= 90);
        if (!maxs.length && !mins.length) continue;
        indice = true;
        preuves.push({ phrase: p, doc: src.document_source, page: src.page, section: src.section });
        const max = maxs.length ? Math.max(...maxs) : null;
        const min = mins.length ? Math.min(...mins) : null;
        if ((max !== null && age > max) || (min !== null && age < min)) {
          reserve = true;
          raisons.push(`Âge ${age} au-delà d'une limite documentée (${max !== null ? "max " + max : "min " + min} ans) — à confirmer : cette limite peut ne viser qu'une garantie ou une option.`);
        } else raisons.push(`Aucune incompatibilité d'âge dans la limite documentée (${max !== null ? "max " + max : "min " + min} ans).`);
      }
    }
  }
  if (exclusionFerme) return { statut: "exclue", score: bar.eligibilite.exclue, raisons, preuves, exclusionFerme: true };
  if (reserve) return { statut: "incertaine", score: bar.eligibilite.incertaine, raisons, preuves, exclusionFerme: false };
  if (indice) return { statut: "probable", score: bar.eligibilite.probable, raisons, preuves, exclusionFerme: false };
  raisons.push(age === null || age === undefined ? "Âge non renseigné : conditions d'adhésion non vérifiables ici." : "Aucune limite d'âge d'adhésion structurée dans les sources : à vérifier au contrat.");
  return { statut: "à vérifier", score: bar.eligibilite.a_verifier, raisons, preuves, exclusionFerme: false };
}

const R_PRIX = /(\d+(?:[.,]\d{1,2})?)\s*(?:€|euros?)\s*(?:\/\s*mois|par\s+mois|mensuel)/g;
const TAUX_UNITAIRE = /capital sous risque|par tranche|pour \d|par \d|%|pour 1 ?000|taux/;

function estimerPrixMensuel(faits) {
  const cands = [];
  for (const f of faits) {
    if (f.categorie !== "cotisation_prix" && f.categorie !== "cotisations_et_prix") continue;
    for (const p of phrases(norm(`${f.titre} — ${f.resume_humain}`))) {
      if (TAUX_UNITAIRE.test(p)) continue;
      for (const m of tousLes(R_PRIX, p)) {
        const v = Number(m[1].replace(",", "."));
        if (v >= 5 && v < 10000) cands.push({ valeur: v, phrase: p, source: f.source || {} });
      }
    }
  }
  if (!cands.length) return null;
  return cands.reduce((a, b) => (b.valeur < a.valeur ? b : a));
}

function evaluerBudget(faits, criteres, bar) {
  const est = estimerPrixMensuel(faits);
  const budget = criteres.budget_mensuel;
  const marge = criteres.marge_pourcentage ?? bar.budget?.marge_pourcentage_defaut ?? 10;
  const plafond = budget === null || budget === undefined ? null : budget * (1 + marge / 100);
  const neutre = bar.budget_scores.tarif_a_verifier;
  if (!est) return { statut: "tarif non chiffré dans la notice", score: neutre, estimation: null, plafond, cause: "sans_tarif" };
  if (plafond === null) return { statut: "budget non renseigné", score: neutre, estimation: est, plafond, cause: "sans_budget" };
  if (est.valeur <= budget) return { statut: "dans le budget", score: bar.budget_scores.dans_budget, estimation: est, plafond, cause: null };
  if (est.valeur <= plafond) return { statut: `dans la marge +${marge} %`, score: bar.budget_scores.dans_marge, estimation: est, plafond, cause: null };
  return { statut: "au-dessus du budget", score: bar.budget_scores.hors_budget, estimation: est, plafond, cause: null };
}

function evaluerBesoins(faits, besoins, bar, nomContrat) {
  const textes = faits.filter(f => CATS_POSITIVES.includes(f._cat))
    .map(f => norm([f.titre, f.resume_humain, f.impact_client, ...(f.mots_cles || [])].filter(Boolean).join(" ")));
  const detail = [];
  let cumulPondere = 0, cumulImportance = 0;
  for (const b of besoins) {
    const lie = !Array.isArray(b.contrats) || b.contrats.some(n => cleNom(n) === cleNom(nomContrat));
    const cles = [...new Set([...(bar.need_keywords[b.besoin_canonique] || []), ...(b.mots_cles || [])].map(norm))].filter(Boolean);
    const n = lie && cles.length ? textes.filter(t => cles.some(c => t.includes(c))).length : 0;
    const score = n >= 3 ? 100 : n >= 1 ? 60 : 0;
    detail.push({ id: b.id, libelle: b.libelle, score, importance: b.importance, faits: n, rattache: lie });
    cumulImportance += b.importance; cumulPondere += score * b.importance;
  }
  const moyenne = detail.length ? detail.reduce((s, d) => s + d.score, 0) / detail.length : 50;
  const pondere = cumulImportance ? cumulPondere / cumulImportance : 50;
  return {
    scoreCouverture: moyenne, scoreImportance: pondere, detail,
    couverts: detail.filter(d => d.score >= 80).map(d => d.libelle),
    partiels: detail.filter(d => d.score > 0 && d.score < 80).map(d => d.libelle),
    absents: detail.filter(d => !d.score).map(d => d.libelle),
    annonces: detail.filter(d => d.rattache && !d.score).map(d => d.libelle),
    nombre: detail.length,
  };
}

function evaluerConfiance(faits, elig, budget, bar) {
  if (!faits.length) return 20;
  const traces = faits.filter(f => (f.source || {}).statut_tracabilite === "complete").length;
  let s = 35 + 65 * (traces / faits.length);
  if (elig.statut === "à vérifier") s -= bar.confidence?.eligibilite_inconnue_penalite ?? 10;
  if (budget.cause === "sans_tarif") s -= bar.confidence?.tarif_inconnu_penalite ?? 10;
  return clamp(s);
}

function preselection(criteres, { bareme, contratsResume, fichesConseiller, matriceRisques }) {
  const bar = bareme;
  const contrats = contratsResume?.contrats || [];
  const fiches = new Map((fichesConseiller?.contrats || []).map(c => [cleNom(c.nom), c]));
  const dejaEnPlace = new Set((criteres.existants || []).map(cleNom));
  const RISQUES = matriceRisques?.risques || {};

  // Résout les ids de besoins publics (vocabulaire matrice métier) vers l'objet complet attendu par
  // evaluerBesoins — c'est ICI que le double entonnoir (mots-clés ∪ rattachement curé) se construit.
  const besoins = (criteres.besoins || []).map((b, i) => {
    const r = RISQUES[b.id];
    if (!r) return null;
    return {
      id: b.id, libelle: r.libelle || b.id,
      importance: Number.isFinite(b.importance) ? clamp(b.importance, 1, 100) : Math.max(30, 100 - 8 * i),
      besoin_canonique: RISQUE_BESOIN[b.id] ?? null,
      mots_cles: r.mots_cles || [], contrats: r.contrats || [],
    };
  }).filter(Boolean);

  const resultats = [];
  for (const c of contrats) {
    if (dejaEnPlace.has(cleNom(c.nom))) continue;
    const faits = CATS.flatMap(k => (c[k] || []).map(f => ({ ...f, _cat: k })));
    const elig = evaluerEligibilite(fiches.get(cleNom(c.nom)), criteres, bar);
    const budget = evaluerBudget(faits, criteres, bar);
    const bes = evaluerBesoins(faits, besoins, bar, c.nom);
    const confiance = evaluerConfiance(faits, elig, budget, bar);
    const w = bar.weights;
    const total = clamp(elig.score * w.eligibilite + bes.scoreCouverture * w.besoins_couverts +
      bes.scoreImportance * w.importance_besoins + budget.score * w.budget + confiance * w.confiance);
    const rattache = besoins.some(b => (b.contrats || []).some(n => cleNom(n) === cleNom(c.nom)));
    const questions = [];
    if (criteres.age === null || criteres.age === undefined) questions.push("Quel est l'âge exact à la souscription ? (il conditionne l'adhésion)");
    if (budget.cause === "sans_tarif") questions.push("Quelle cotisation ressort du tarificateur ou du devis officiel ?");
    if (bes.absents.length) questions.push(`Ces besoins ne ressortent pas des sources de ce contrat : ${bes.absents.join(", ")} — sont-ils indispensables ?`);
    questions.push("La profession et les activités pratiquées entrent-elles dans une exclusion ? (à lire au contrat)");
    resultats.push({
      nom: c.nom, famille: c.famille || "à vérifier", cle: cleNom(c.nom),
      horsSujet: bes.nombre > 0 && bes.scoreCouverture === 0,
      nonRattache: bes.nombre > 0 && !rattache,
      score: arrondi(total), eligibilite: elig, budget, besoins: bes,
      confiance: arrondi(confiance), nbFaits: faits.length,
      questions,
    });
  }
  resultats.sort((a, b) => b.score - a.score);
  const seuil = bar.display?.score_minimum ?? 45;
  const max = bar.display?.max_results_default ?? 5;
  const retenus = resultats.filter(r => !r.eligibilite.exclusionFerme && !r.horsSujet && !r.nonRattache && r.score >= seuil);
  const classes = retenus.slice(0, max);
  const dansLaListe = new Set(classes);
  const motif = r => r.eligibilite.exclusionFerme ? "âge hors de la plage d'adhésion documentée"
    : r.nonRattache ? "la matrice métier ne le rattache à aucun des besoins actifs"
    : r.horsSujet ? "aucun des besoins retenus ne ressort de ses sources"
    : r.score < seuil ? `score ${r.score} sous le seuil de ${seuil}`
    : `au-delà des ${max} premiers du classement`;
  return {
    classes,
    ecartes: resultats.filter(r => !dansLaListe.has(r)).map(r => ({ ...r, motif: motif(r) })),
    total: resultats.length, seuil, max,
    remunerationExclue: bar.meta?.remuneration_incluse_dans_scoring === false,
    besoins_reconnus: besoins.map(b => b.id), besoins_ignores: (criteres.besoins || []).map(b => b.id).filter(id => !RISQUES[id]),
  };
}

/* ---------- Lecture des données du MÊME déploiement (aucun fetch cross-origin) ---------- */
async function lireJSON(env, request, chemin) {
  const url = new URL(chemin, request.url);
  const r = await env.ASSETS.fetch(new Request(url));
  if (!r.ok) throw new Error(`Source indisponible : ${chemin} (HTTP ${r.status})`);
  return r.json();
}

/* ---------- Entrée : aucune donnée nominative acceptée ---------- */
const CHAMPS_NOMINATIFS = /nom|prenom|email|mail|telephone|tel|adresse|iban|ssn|siret/i;
function validerParams(sp) {
  for (const cle of sp.keys()) {
    if (CHAMPS_NOMINATIFS.test(cle)) {
      return `Paramètre refusé : « ${cle} ». Cet endpoint n'accepte aucune donnée nominative (nom, coordonnées) — uniquement des critères de profil anonymes.`;
    }
  }
  return null;
}

function reponseJSON(obj, status = 200) {
  return new Response(JSON.stringify(obj, null, 1), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "no-store",
    },
  });
}

export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const sp = url.searchParams;

  const erreurParam = validerParams(sp);
  if (erreurParam) return reponseJSON({ erreur: erreurParam }, 400);

  const age = sp.has("age") ? Number(sp.get("age")) : null;
  const budget_mensuel = sp.has("budget") ? Number(sp.get("budget")) : null;
  const marge_pourcentage = sp.has("marge") ? Number(sp.get("marge")) : undefined;
  const existants = (sp.get("existants") || "").split(",").map(s => s.trim()).filter(Boolean);
  // besoins=id:importance,id:importance (importance omise = priorité déduite du rang, comme le produit)
  const besoins = (sp.get("besoins") || "").split(",").map(s => s.trim()).filter(Boolean).map((tok, i) => {
    const [id, imp] = tok.split(":");
    return { id: id.trim(), importance: imp !== undefined ? Number(imp) : undefined, rang: i };
  });

  if (age !== null && (!Number.isFinite(age) || age < 0 || age > 120)) return reponseJSON({ erreur: "Paramètre age invalide (0–120)." }, 400);
  if (!besoins.length) return reponseJSON({
    erreur: "Paramètre besoins manquant ou vide. Fournis au moins un id (voir besoins_disponibles).",
    besoins_disponibles: null,   // renseigné ci-dessous une fois la matrice chargée, pour une erreur utile
  }, 400);

  let bareme, contratsResume, fichesConseiller, matriceRisques, version, date;
  try {
    [bareme, contratsResume, fichesConseiller, matriceRisques] = await Promise.all([
      lireJSON(env, request, "/data/AXA/ia/axa_scoring_recherche_personnalisee.json").catch(() => BAREME_SECOURS),
      lireJSON(env, request, "/data/AXA/vue_humaine/axa_contrats_resume_humain.json"),
      lireJSON(env, request, "/data/AXA/derived/fiches_conseiller.json"),
      lireJSON(env, request, "/ia/inspecteur/metier/matrice_risques.json"),
    ]);
    try { const v = await lireJSON(env, request, "/version.json"); version = v.version; date = v.date; }
    catch { version = VERSION_FALLBACK; date = null; }
  } catch (e) {
    return reponseJSON({ erreur: "Données source indisponibles côté serveur.", detail: String(e.message || e) }, 503);
  }

  const idsInconnus = besoins.map(b => b.id).filter(id => !(matriceRisques.risques || {})[id]);
  if (idsInconnus.length === besoins.length) {
    return reponseJSON({
      erreur: `Aucun des besoins fournis n'est reconnu : ${idsInconnus.join(", ")}.`,
      besoins_disponibles: Object.keys(matriceRisques.risques || {}),
    }, 400);
  }

  const criteres = { age, budget_mensuel, marge_pourcentage, existants, besoins };
  const resultat = preselection(criteres, { bareme, contratsResume, fichesConseiller, matriceRisques });

  return reponseJSON({
    meta: {
      base_consultee: `Gabriel AXA v${version}${date ? " (" + date + ")" : ""}`,
      endpoint: "preselection", execution: "deterministe (moteur exécuté, pas approximé par une IA)",
      avertissement: "Aide au raisonnement, jamais une recommandation automatique. Le conseiller décide ; " +
                     "chaque résultat porte sa notice et sa page. La notice PDF fait foi. Rémunération conseiller exclue du calcul.",
    },
    criteres_recus: { age, budget_mensuel, existants, besoins: besoins.map(b => b.id) },
    ...resultat,
  });
}

// Toute autre méthode : endpoint en lecture seule, jamais d'écriture.
export async function onRequestPost() {
  return reponseJSON({ erreur: "Cet endpoint est en LECTURE SEULE (GET uniquement). Aucune écriture n'est possible ici." }, 405);
}
