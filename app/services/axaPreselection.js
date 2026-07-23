// axaPreselection — scoring de présélection contractuelle (migré du cockpit legacy, 2026-07-23).
//
// ORIGINE : `axa_recherche_personnalisee_v2.8.js` (page autonome du cockpit Gabriel Virtuel).
// Le barème de référence `ia/axa_scoring_recherche_personnalisee.json` était DÉJÀ dans ce dépôt,
// mais aucun code ne le lisait : le produit conseiller proposait des « contrats à examiner » sans
// aucun filtre d'âge, sans adéquation budget et sans mesure de la qualité documentaire.
//
// CE QUI EST REPRIS À L'IDENTIQUE (barème contractuel, jamais réinventé) :
//   • pondération 0,25 éligibilité · 0,30 besoins couverts · 0,20 importance des besoins
//     · 0,15 budget · 0,10 confiance documentaire ;
//   • scores d'éligibilité (95 / 65 / 40 / 0) et de budget (100 / 80 / 20 / 55) ;
//   • couverture d'un besoin : ≥ 3 faits = 100, ≥ 1 = 60, sinon 0 ;
//   • confiance = 35 + 65 × (faits tracés « complete » / total), pénalités −10 par inconnue ;
//   • seuil d'affichage 45 et top 5 ;
//   • GARDE-FOU : la rémunération conseiller n'entre JAMAIS dans le calcul.
//
// CE QUI A ÉTÉ CORRIGÉ, ET POURQUOI (mesuré sur les 9 contrats réels, pas supposé) :
//   ① Source des données. Le cockpit lisait `AXA_CONTRATS_UNIFIE_IA.json` (4,6 Mo). On lit ici les
//      sources légères déjà chargées par le produit : résumé humain (317 faits, avec traçabilité
//      et confiance) + fiches conseiller (conditions de souscription sourcées page par page).
//   ② Limites d'âge. Le vocabulaire du cockpit ratait « plus de 18 ans » et « < 70 ans », et
//      surtout il prenait « modification des garanties jusqu'aux 75 ans » (clause de MODIFICATION)
//      pour une limite d'ADHÉSION — un client de 78 ans aurait été exclu à tort d'Avizen Pro.
//      Ici : lecture des seules conditions de souscription, et un contexte d'entrée en contrat
//      (souscription / adhésion / signature) est exigé pour les limites ouvertes.
//   ③ Exclusion ferme. Seule une PLAGE explicite (« entre 40 et 75 ans inclus à la signature »)
//      justifie une exclusion. Une limite ouverte donne « incertaine » : mesuré, « < 70 ans » chez
//      Excelium ne borne qu'une OPTION, pas le contrat. Et un contrat exclu n'est jamais retiré en
//      silence : il ressort dans `ecartes` avec sa citation et sa page de notice.
//   ④ Prix mensuel. Le cockpit prenait le minimum de tous les montants « €/mois » trouvés : chez
//      Excelium cela donnait 0,04 €/mois (un tarif POUR 250 € de capital sous risque, pas une
//      cotisation). Les taux unitaires et les montants < 5 € sont donc écartés, et l'estimation
//      retenue est toujours affichée avec la phrase d'où elle vient.
//   ⑤ Heuristique profession. Le cockpit dégradait l'éligibilité si un mot du statut apparaissait
//      dans une exclusion. Mesure sur ce corpus : « Sans activité » se déclenchait sur
//      « activités et sports à risque » (7 faux positifs sur 7). Retirée, remplacée par une
//      question explicite au conseiller.
//
// Le module ne fait AUCUN rendu et ne stocke rien : il reçoit des critères, il rend des scores
// sourcés. Le conseiller décide ; la notice PDF fait foi.
import * as kb from "./axaKnowledge.js";

const CATS = ["garanties_principales", "exclusions_importantes", "options", "cotisations_prix",
  "delais_franchises", "fiscalite", "points_de_vigilance"];
// Faits « positifs » : une exclusion ou un point de vigilance ne prouve pas qu'un besoin est couvert.
const CATS_POSITIVES = CATS.filter(k => k !== "exclusions_importantes" && k !== "points_de_vigilance");

const norm = s => String(s ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const cleNom = n => String(n || "").replace(/\(.*?\)/g, "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]/g, "");
const clamp = (v, min = 0, max = 100) => Math.min(max, Math.max(min, v));
const arrondi = v => Math.round(v * 10) / 10;

// Barème de secours : si le JSON disparaît, le scoring reste cohérent au lieu de tomber en panne.
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

let _bareme = null;
export async function bareme() {
  if (_bareme) return _bareme;
  const b = await kb.source("scoring_preselection");
  _bareme = b && b.weights ? b : BAREME_SECOURS;
  return _bareme;
}

/* ---------- Éligibilité : limites d'âge lues dans les conditions de souscription ---------- */
// Une plage (« entre 40 et 75 ans ») est une condition d'entrée sans ambiguïté.
const R_PLAGE = /(?:de|entre)\s+(\d{1,2})\s+(?:a|et)\s+(\d{1,2})\s+ans/g;
// Les limites ouvertes n'ont de valeur QUE dans une phrase qui parle d'entrer dans le contrat.
const R_MAX = /(?:moins de|avant|au plus|jusqu'?a(?:ux)?|maximum de|<)\s*(\d{1,2})\s*ans/g;
const R_MIN = /(?:plus de|a partir de|au moins|minimum de|des l'age de|>)\s*(\d{1,2})\s*ans/g;
const CTX_ENTREE = /souscri|adhesion|adherent|adherer|signature|entree|conditions cumulatives|age (?:minimum|maximum|limite)|etre age/;

const phrases = t => String(t).split(/[.;]/).map(p => p.trim()).filter(Boolean);
const tousLes = (re, s) => [...s.matchAll(new RegExp(re.source, "g"))];

function evaluerEligibilite(fiche, criteres, bar) {
  const raisons = [];
  const preuves = [];
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
          if (!ok) {
            exclusionFerme = true;
            raisons.push(`Âge ${age} hors de la plage d'adhésion documentée (${plages.map(m => `${m[1]}–${m[2]} ans`).join(", ")}).`);
          } else raisons.push(`Âge ${age} dans la plage d'adhésion documentée (${plages.map(m => `${m[1]}–${m[2]} ans`).join(", ")}).`);
          continue;
        }
        if (!CTX_ENTREE.test(p)) continue;   // ② clause de durée/cessation : pas une condition d'entrée
        const maxs = tousLes(R_MAX, p).map(m => Number(m[1])).filter(v => v >= 16);
        const mins = tousLes(R_MIN, p).map(m => Number(m[1])).filter(v => v >= 0 && v <= 90);
        if (!maxs.length && !mins.length) continue;
        indice = true;
        preuves.push({ phrase: p, doc: src.document_source, page: src.page, section: src.section });
        const max = maxs.length ? Math.max(...maxs) : null;
        const min = mins.length ? Math.min(...mins) : null;
        if ((max !== null && age > max) || (min !== null && age < min)) {
          reserve = true;   // ③ limite ouverte : réserve, jamais exclusion
          raisons.push(`Âge ${age} au-delà d'une limite documentée (${max !== null ? "max " + max : "min " + min} ans) — à confirmer : cette limite peut ne viser qu'une garantie ou une option.`);
        } else raisons.push(`Aucune incompatibilité d'âge dans la limite documentée (${max !== null ? "max " + max : "min " + min} ans).`);
      }
    }
  }
  if (exclusionFerme) return { statut: "exclue", score: bar.eligibilite.exclue, raisons, preuves, exclusionFerme: true };
  if (reserve) return { statut: "incertaine", score: bar.eligibilite.incertaine, raisons, preuves, exclusionFerme: false };
  if (indice) return { statut: "probable", score: bar.eligibilite.probable, raisons, preuves, exclusionFerme: false };
  raisons.push(age === null || age === undefined
    ? "Âge non renseigné : conditions d'adhésion non vérifiables ici."
    : "Aucune limite d'âge d'adhésion structurée dans les sources : à vérifier au contrat.");
  return { statut: "à vérifier", score: bar.eligibilite.a_verifier, raisons, preuves, exclusionFerme: false };
}

/* ---------- Budget : ordre de grandeur, jamais un tarif contractuel ---------- */
const R_PRIX = /(\d+(?:[.,]\d{1,2})?)\s*(?:€|euros?)\s*(?:\/\s*mois|par\s+mois|mensuel)/g;
// ④ Une phrase qui exprime un tarif PAR unité de capital n'est pas une cotisation.
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
  return cands.reduce((a, b) => (b.valeur < a.valeur ? b : a));   // point d'entrée le plus bas
}

function evaluerBudget(faits, criteres, bar) {
  const est = estimerPrixMensuel(faits);
  const budget = criteres.budget_mensuel;
  const marge = criteres.marge_pourcentage ?? bar.budget?.marge_pourcentage_defaut ?? 10;
  const plafond = budget === null || budget === undefined ? null : budget * (1 + marge / 100);
  const neutre = bar.budget_scores.tarif_a_verifier;
  // Le cockpit disait « tarif à vérifier » dans les deux cas. On distingue la cause : ce n'est pas
  // la même chose qu'une notice ne chiffre rien et que le conseiller n'ait pas saisi de budget —
  // seule la première est un défaut de DOCUMENTATION (et pénalise donc la confiance).
  if (!est) return { statut: "tarif non chiffré dans la notice", score: neutre, estimation: null, plafond, cause: "sans_tarif" };
  if (plafond === null) return { statut: "budget non renseigné", score: neutre, estimation: est, plafond, cause: "sans_budget" };
  if (est.valeur <= budget) return { statut: "dans le budget", score: bar.budget_scores.dans_budget, estimation: est, plafond, cause: null };
  if (est.valeur <= plafond) return { statut: `dans la marge +${marge} %`, score: bar.budget_scores.dans_marge, estimation: est, plafond, cause: null };
  return { statut: "au-dessus du budget", score: bar.budget_scores.hors_budget, estimation: est, plafond, cause: null };
}

/* ---------- Besoins : couverture pondérée par l'importance ---------- */
function evaluerBesoins(faits, besoins, bar, nomContrat) {
  const textes = faits.filter(f => CATS_POSITIVES.includes(f._cat))
    .map(f => norm([f.titre, f.resume_humain, f.impact_client, ...(f.mots_cles || [])].filter(Boolean).join(" ")));
  const detail = [];
  let cumulPondere = 0, cumulImportance = 0;
  for (const b of besoins) {
    // Double entonnoir au niveau du COUPLE (contrat, besoin) : la matrice métier dit si ce contrat
    // adresse ce besoin ; les mots-clés disent seulement si les sources le DOCUMENTENT. Sans cette
    // condition, un contrat dépendance marquait 100 sur « retraite » parce que le mot « rente »
    // apparaît dans ses garanties — et passait devant les vrais contrats retraite.
    const lie = !Array.isArray(b.contrats) || b.contrats.some(n => cleNom(n) === cleNom(nomContrat));
    // Vocabulaire double : les mots-clés canoniques du barème + ceux de la matrice métier du produit.
    const cles = [...new Set([...(bar.need_keywords[b.besoin_canonique] || []), ...(b.mots_cles || [])].map(norm))].filter(Boolean);
    const n = lie && cles.length ? textes.filter(t => cles.some(c => t.includes(c))).length : 0;
    const score = n >= 3 ? 100 : n >= 1 ? 60 : 0;
    detail.push({ id: b.id, libelle: b.libelle, score, importance: b.importance, faits: n, rattache: lie });
    cumulImportance += b.importance;
    cumulPondere += score * b.importance;
  }
  const moyenne = detail.length ? detail.reduce((s, d) => s + d.score, 0) / detail.length : 50;
  const pondere = cumulImportance ? cumulPondere / cumulImportance : 50;
  return {
    scoreCouverture: moyenne, scoreImportance: pondere, detail,
    couverts: detail.filter(d => d.score >= 80).map(d => d.libelle),
    partiels: detail.filter(d => d.score > 0 && d.score < 80).map(d => d.libelle),
    absents: detail.filter(d => !d.score).map(d => d.libelle),
    // La matrice rattache le besoin à ce contrat, mais aucune source ne le documente : à vérifier.
    annonces: detail.filter(d => d.rattache && !d.score).map(d => d.libelle),
    nombre: detail.length,
  };
}

/* ---------- Confiance documentaire ---------- */
function evaluerConfiance(faits, elig, budget, bar) {
  if (!faits.length) return 20;
  const traces = faits.filter(f => (f.source || {}).statut_tracabilite === "complete").length;
  let s = 35 + 65 * (traces / faits.length);
  if (elig.statut === "à vérifier") s -= bar.confidence?.eligibilite_inconnue_penalite ?? 10;
  if (budget.cause === "sans_tarif") s -= bar.confidence?.tarif_inconnu_penalite ?? 10;
  return clamp(s);
}

/* ---------- Entrée publique ----------
   criteres = { age, budget_mensuel, marge_pourcentage, besoins:[{id, libelle, importance,
                besoin_canonique, mots_cles, contrats}], existants:[nom] }
   → { classes, ecartes, sousLeSeuil, seuil, max, bareme } — rien n'est masqué en silence. */
export async function preselection(criteres) {
  const bar = await bareme();
  const [rh, fic] = await Promise.all([kb.source("contrats_resume_humain"), kb.source("fiches_conseiller")]);
  const contrats = rh?.contrats || [];
  const fiches = new Map((fic?.contrats || []).map(c => [cleNom(c.nom), c]));
  const dejaEnPlace = new Set((criteres.existants || []).map(cleNom));

  const resultats = [];
  for (const c of contrats) {
    if (dejaEnPlace.has(cleNom(c.nom))) continue;   // déjà détenu : il n'est pas « à examiner »
    const faits = CATS.flatMap(k => (c[k] || []).map(f => ({ ...f, _cat: k })));
    const elig = evaluerEligibilite(fiches.get(cleNom(c.nom)), criteres, bar);
    const budget = evaluerBudget(faits, criteres, bar);
    const besoins = evaluerBesoins(faits, criteres.besoins || [], bar, c.nom);
    const confiance = evaluerConfiance(faits, elig, budget, bar);
    const w = bar.weights;
    const total = clamp(
      elig.score * w.eligibilite +
      besoins.scoreCouverture * w.besoins_couverts +
      besoins.scoreImportance * w.importance_besoins +
      budget.score * w.budget +
      confiance * w.confiance);
    // Double entonnoir : les mots-clés ORIENTENT (recouvrement de vocabulaire, large et faillible),
    // la matrice métier TRANCHE (rattachement besoin → contrat, curé à la main). Sans cela, un
    // contrat dépendance remontait 2e sur un cas « TNS avec crédit et enfants » par simple
    // recouvrement de vocabulaire (invalidité, incapacité) alors que la matrice ne le rattache à
    // aucun besoin actif. Les 9 contrats sont cités par la matrice : elle n'est jamais muette.
    const rattache = (criteres.besoins || []).some(b => (b.contrats || []).some(n => cleNom(n) === cleNom(c.nom)));
    const questions = [];
    if (criteres.age === null || criteres.age === undefined) questions.push("Quel est l'âge exact à la souscription ? (il conditionne l'adhésion)");
    if (budget.cause === "sans_tarif") questions.push("Quelle cotisation ressort du tarificateur ou du devis officiel ?");
    if (besoins.absents.length) questions.push(`Ces besoins ne ressortent pas des sources de ce contrat : ${besoins.absents.join(", ")} — sont-ils indispensables ?`);
    questions.push("La profession et les activités pratiquées entrent-elles dans une exclusion ? (à lire au contrat)");
    resultats.push({
      nom: c.nom, famille: c.famille || "à vérifier", cle: cleNom(c.nom),
      // Repris du cockpit : un contrat dont AUCUN besoin actif ne ressort des sources est hors sujet
      // (le cockpit le supprimait ; ici il descend dans « écartés », avec son motif).
      horsSujet: besoins.nombre > 0 && besoins.scoreCouverture === 0,
      nonRattache: besoins.nombre > 0 && !rattache,
      score: arrondi(total), eligibilite: elig, budget, besoins,
      confiance: arrondi(confiance), nbFaits: faits.length,
      vigilance: (c.points_de_vigilance || []).slice(0, 3).map(f => f.titre).filter(Boolean),
      questions,
    });
  }
  resultats.sort((a, b) => b.score - a.score);
  const seuil = bar.display?.score_minimum ?? 45;
  const max = bar.display?.max_results_default ?? 5;
  const retenus = resultats.filter(r => !r.eligibilite.exclusionFerme && !r.horsSujet && !r.nonRattache && r.score >= seuil);
  const classes = retenus.slice(0, max);
  const dansLaListe = new Set(classes);
  // Motif le plus décisif d'abord : le rattachement métier (curé à la main) prime sur le simple
  // recouvrement de vocabulaire, qui prime lui-même sur le score agrégé.
  const motif = r => r.eligibilite.exclusionFerme ? "âge hors de la plage d'adhésion documentée"
    : r.nonRattache ? "la matrice métier ne le rattache à aucun des besoins actifs"
    : r.horsSujet ? "aucun des besoins retenus ne ressort de ses sources"
    : r.score < seuil ? `score ${r.score} sous le seuil de ${seuil}`
    : `au-delà des ${max} premiers du classement`;
  return {
    classes,
    // Aucun contrat n'est masqué en silence : tout ce qui sort de la liste porte son motif.
    ecartes: resultats.filter(r => !dansLaListe.has(r)).map(r => ({ ...r, motif: motif(r) })),
    total: resultats.length,
    seuil, max, remunerationExclue: bar.meta?.remuneration_incluse_dans_scoring === false,
  };
}
