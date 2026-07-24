// /api/diagnostic — Cloudflare Pages/Worker Function.
//
// Port FIDÈLE du moteur de diagnostic « cas client » du produit conseiller (besoins() dans
// app/modules/axa.js) : à partir d'un profil (statut, situation familiale, âge, événements de vie,
// besoins exprimés, contrats déjà en place), il PRIORISE les risques avec leur statut épistémique
// (déclaré > déduit > hypothèse), évalue la couverture (doublon / couvert / trou), liste les
// contrats à examiner pour les trous, et ce qui reste à clarifier.
//
// POURQUOI UN ENDPOINT : les 6 cas-types statiques (ia/cas-types) ne couvrent que 6 scénarios écrits
// à la main. Ce moteur gère N'IMPORTE QUELLE combinaison de profil, avec le même raisonnement
// prioritaire que le conseiller a dans l'app — garanti exact, au lieu d'être ré-approximé par une IA.
//
// GARDE-FOUS (identiques à /api/preselection) : lecture seule, aucune donnée nominative acceptée,
// aucune recommandation automatique (le conseiller décide), rien n'est masqué en silence.

const cleNom = n => String(n || "").replace(/\(.*?\)/g, "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]/g, "");
const shortR = (RISQUES, id) => String(RISQUES[id]?.libelle || id).split("—")[0].trim();

// Ordre socle des priorités (dettes d'abord, catastrophique avant probable, protéger avant épargner).
const ORDRE_SOCLE = ["emprunt", "deces_protection_famille", "arret_travail_itt", "invalidite",
  "accident_vie_privee", "education_enfants", "dependance", "obseques", "retraite_revenu", "epargne_transmission"];
const POURQUOI_RANG = {
  emprunt: "une dette longue court quoi qu'il arrive — la couvrir passe avant le reste",
  deces_protection_famille: "catastrophique pour les proches si rien n'est prévu",
  arret_travail_itt: "le risque le plus fréquent : le revenu s'arrête, pas les charges",
  invalidite: "rare mais définitif — à traiter avec l'arrêt de travail",
  accident_vie_privee: "fréquent, et hors du champ des couvertures professionnelles",
  education_enfants: "sécuriser le parcours des enfants si un parent disparaît",
  dependance: "fenêtre d'assurabilité : plus on attend, plus c'est cher ou refusé",
  obseques: "éviter de laisser la charge et l'organisation aux proches",
  retraite_revenu: "se construit tôt, mais après la protection du présent",
  epargne_transmission: "on épargne une fois le socle de protection en place",
};
const EVT_LABEL = {
  naissance: "naissance / enfant à venir", achat_immobilier: "achat immobilier / crédit",
  passage_independant: "passage en indépendant", mariage_pacs: "mariage / PACS",
  divorce: "divorce / séparation", approche_retraite: "retraite qui approche",
  deces_proche: "décès d'un proche", sport_a_risque: "sport / activité à risque",
};
const COLLECTIF_COUVRE = new Set(["deces_protection_famille", "arret_travail_itt", "invalidite"]);

// Normalisation des valeurs d'entrée (l'app utilise des libellés français ; l'API accepte des codes).
const STATUTS = { salarie: "salarie", tns: "tns", independant: "tns", fonctionnaire: "fonctionnaire", retraite: "retraite", sans_activite: "sans_activite" };
const FAMILLES = { celibataire: "celibataire", couple: "couple", enfants: "enfants", recomposee: "recomposee", famille_recomposee: "recomposee" };

function diagnostiquer(cas, { RISQUES, EVTS }) {
  const flags = new Set();
  if (cas.statut === "tns") flags.add("tns");
  if (cas.statut === "salarie") flags.add("salarie");
  if (cas.famille === "enfants" || cas.famille === "recomposee") flags.add("enfants");
  if (cas.famille === "recomposee") flags.add("famille_recomposee");
  if (cas.credit) flags.add("credit");
  const age = cas.age;
  if (age !== null && age >= 55) flags.add("senior");
  if (age !== null && age < 35) flags.add("jeune");
  if (cas.famille === "celibataire" && !flags.has("enfants")) flags.add("solo");

  const rank = { declare: 3, deduit: 2, hypothese: 1 };
  const actifs = new Map();
  const add = (id, st, via) => {
    if (!RISQUES[id]) return;
    const cur = actifs.get(id);
    if (!cur) actifs.set(id, { statut: st, via: via ? [via] : [] });
    else { if (rank[st] > rank[cur.statut]) cur.statut = st; if (via && !cur.via.includes(via)) cur.via.push(via); }
  };
  for (const b of cas.besoins) add(b, "declare", "exprimé par le client");
  for (const e of cas.evts) for (const rid of (EVTS[e]?.risques || [])) add(rid, "deduit", "événement : " + (EVT_LABEL[e] || e));
  if (flags.has("credit")) add("emprunt", "deduit", "crédit en cours");
  if (flags.has("tns")) { add("arret_travail_itt", "hypothese", "statut TNS"); add("invalidite", "hypothese", "statut TNS"); }
  if (flags.has("enfants")) { add("deces_protection_famille", "hypothese", "enfants à charge"); add("education_enfants", "hypothese", "enfants à charge"); }
  if (flags.has("senior")) { add("dependance", "hypothese", "âge ≥ 55"); add("obseques", "hypothese", "âge ≥ 55"); add("retraite_revenu", "hypothese", "âge ≥ 55"); }

  const score = id => {
    let s = ORDRE_SOCLE.indexOf(id); if (s < 0) s = 99;
    if (flags.has("credit") && id === "emprunt") s -= 6;
    if (flags.has("tns") && id === "arret_travail_itt") s -= 3;
    if (flags.has("enfants") && id === "education_enfants") s -= 2;
    if (flags.has("enfants") && id === "deces_protection_famille") s -= 1;
    if (flags.has("senior") && (id === "dependance" || id === "obseques")) s -= 3;
    if (flags.has("solo") && !cas.besoins.has(id) && (id === "deces_protection_famille" || id === "education_enfants")) s += 8;
    return s;
  };
  const ordre = [...actifs.keys()].sort((x, y) => score(x) - score(y));

  const exNoms = [...cas.existants];
  const couvrent = id => (RISQUES[id]?.contrats || []);
  const couvertsPar = id => exNoms.filter(n => couvrent(id).some(x => cleNom(x) === cleNom(n)));
  const candOf = id => couvrent(id).filter(n => !exNoms.some(x => cleNom(x) === cleNom(n)));

  const diagnostic = ordre.map((id, i) => {
    const a = actifs.get(id);
    const cvts = couvertsPar(id);
    const parCollectif = cas.collectif && COLLECTIF_COUVRE.has(id);
    let couverture;
    if (cvts.length >= 2) couverture = { etat: "doublon_possible", detail: `doublon possible : ${cvts.join(" + ")}`, contrats: cvts };
    else if (cvts.length === 1) couverture = { etat: "couvert_a_verifier", detail: `couvert par ${cvts[0]} — à vérifier au contrat`, contrats: cvts };
    else if (parCollectif) couverture = { etat: "peut_etre_collectif", detail: "peut-être couvert par le collectif — à vérifier", contrats: [] };
    else couverture = { etat: "trou_potentiel", detail: "non couvert — trou potentiel", contrats: [] };
    return {
      id, libelle: shortR(RISQUES, id), rang: i + 1, statut: a.statut,
      pourquoi_ce_rang: POURQUOI_RANG[id] || "", d_ou_ca_vient: a.via, couverture,
    };
  });

  const trous = ordre.filter(id => !couvertsPar(id).length && !(cas.collectif && COLLECTIF_COUVRE.has(id))).slice(0, 4);
  const contrats_a_examiner = [];
  const sans_candidat = [];
  for (const id of trous) {
    const cands = candOf(id);
    if (!cands.length) { sans_candidat.push({ id, libelle: shortR(RISQUES, id) }); continue; }
    contrats_a_examiner.push({ risque: id, libelle: shortR(RISQUES, id), contrats_candidats: cands, a_demander_dabord: (RISQUES[id].questions || [])[0] || null });
  }

  const a_clarifier = [];
  if (!cas.statut) a_clarifier.push("Statut professionnel : il change la priorité arrêt de travail (le TNS est mal couvert par le régime obligatoire).");
  if (!cas.famille) a_clarifier.push("Situation familiale : qui dépend de ce revenu ? (décès, éducation)");
  if (cas.age === null) a_clarifier.push("Âge : il conditionne l'assurabilité (dépendance, obsèques) et les limites de souscription.");
  if (cas.statut === "salarie" && !cas.collectif) a_clarifier.push("Couverture collective : un salarié en a souvent une — vérifier avant de doubler décès/ITT/invalidité.");
  if (!cas.existants.size) a_clarifier.push("Contrats existants : sans eux, impossible de voir doublons et trous réels.");

  return { diagnostic, contrats_a_examiner, sans_candidat, a_clarifier, flags: [...flags] };
}

/* ---------- Lecture des données du MÊME déploiement ---------- */
async function lireJSON(env, request, chemin) {
  const r = await env.ASSETS.fetch(new Request(new URL(chemin, request.url)));
  if (!r.ok) throw new Error(`Source indisponible : ${chemin} (HTTP ${r.status})`);
  return r.json();
}
const CHAMPS_NOMINATIFS = /nom|prenom|email|mail|telephone|tel|adresse|iban|ssn|siret/i;
function reponseJSON(obj, status = 200) {
  return new Response(JSON.stringify(obj, null, 1), {
    status, headers: { "Content-Type": "application/json; charset=utf-8", "Access-Control-Allow-Origin": "*", "Cache-Control": "no-store" },
  });
}

export async function onRequestGet({ request, env }) {
  const sp = new URL(request.url).searchParams;
  for (const cle of sp.keys()) {
    if (CHAMPS_NOMINATIFS.test(cle)) {
      return reponseJSON({ erreur: `Paramètre refusé : « ${cle} ». Cet endpoint n'accepte aucune donnée nominative — uniquement un profil anonyme.` }, 400);
    }
  }

  const statut = sp.has("statut") ? (STATUTS[cleNom(sp.get("statut"))] || null) : null;
  const famille = sp.has("famille") ? (FAMILLES[cleNom(sp.get("famille"))] || null) : null;
  const age = sp.has("age") ? Number(sp.get("age")) : null;
  if (age !== null && (!Number.isFinite(age) || age < 0 || age > 120)) return reponseJSON({ erreur: "Paramètre age invalide (0–120)." }, 400);
  const credit = ["1", "true", "oui"].includes((sp.get("credit") || "").toLowerCase());
  const collectif = ["1", "true", "oui"].includes((sp.get("collectif") || "").toLowerCase());
  const evts = new Set((sp.get("evts") || "").split(",").map(s => cleNom(s)).filter(Boolean));
  const besoins = new Set((sp.get("besoins") || "").split(",").map(s => s.trim()).filter(Boolean));
  const existants = new Set((sp.get("existants") || "").split(",").map(s => s.trim()).filter(Boolean));

  let matrice, evenements, version, date;
  try {
    [matrice, evenements] = await Promise.all([
      lireJSON(env, request, "/ia/inspecteur/metier/matrice_risques.json"),
      lireJSON(env, request, "/ia/inspecteur/metier/evenements_vie.json"),
    ]);
    try { const v = await lireJSON(env, request, "/version.json"); version = v.version; date = v.date; }
    catch { version = "dev"; date = null; }
  } catch (e) {
    return reponseJSON({ erreur: "Données source indisponibles côté serveur.", detail: String(e.message || e) }, 503);
  }

  const RISQUES = matrice.risques || {};
  const EVTS = evenements.evenements || {};

  // Un profil totalement vide ne produit rien d'utile : on renvoie le vocabulaire attendu.
  if (!statut && !famille && age === null && !credit && !evts.size && !besoins.size) {
    return reponseJSON({
      erreur: "Profil vide : fournis au moins un critère (statut, famille, age, credit, evts, besoins).",
      valeurs_acceptees: {
        statut: Object.keys(STATUTS), famille: ["celibataire", "couple", "enfants", "recomposee"],
        credit: "1/0", collectif: "1/0", evts: Object.keys(EVTS), besoins: Object.keys(RISQUES),
      },
    }, 400);
  }

  const cas = { statut, famille, age, credit, collectif, evts, besoins, existants };
  const res = diagnostiquer(cas, { RISQUES, EVTS });

  return reponseJSON({
    meta: {
      base_consultee: `Gabriel AXA v${version}${date ? " (" + date + ")" : ""}`,
      endpoint: "diagnostic", execution: "deterministe (moteur exécuté, pas approximé par une IA)",
      statuts_epistemiques: "déclaré (dit par le client) > déduit (découle d'un fait) > hypothèse (suggéré par le profil, à confirmer)",
      avertissement: "Aide au raisonnement, jamais une recommandation automatique. Le conseiller décide ; " +
                     "hypothèse ≠ fait ; garanties, exclusions et conditions se vérifient à la fiche et à la notice. La notice PDF fait foi.",
    },
    profil_recu: { statut, famille, age, credit, collectif, evts: [...evts], besoins: [...besoins], existants: [...existants] },
    ...res,
  });
}

export async function onRequestPost() {
  return reponseJSON({ erreur: "Cet endpoint est en LECTURE SEULE (GET uniquement). Aucune écriture n'est possible ici." }, 405);
}
