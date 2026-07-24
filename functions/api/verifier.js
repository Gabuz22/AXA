// /api/verifier — Cloudflare Pages/Worker Function.
//
// Le pendant « aval » des garde-fous : une IA lui envoie son BROUILLON de réponse, l'endpoint
// contrôle mécaniquement la FORME (pas l'exactitude) et renvoie les défauts. L'IA corrige puis
// répond. C'est le même moteur que le vérificateur client-side (ia/verifier.html), exposé pour
// l'auto-correction AVANT envoi, sur toutes les questions — pas seulement celles qui passent par un
// endpoint dédié.
//
// EXCEPTION ASSUMÉE au « GET seulement » des autres endpoints : il faut un POST pour recevoir le
// texte à analyser. Mais « lecture seule » reste vrai au sens qui compte : AUCUNE écriture, aucune
// persistance, aucune mutation de données — le texte est analysé en mémoire et jeté. GET est aussi
// accepté (?texte=...) pour les brouillons courts.

// AFFIRMATION contractuelle (verbes/formules d'assertion), pas simple mention d'un risque : « le
// client a un besoin de décès » ne s'affirme rien d'un contrat et n'a pas à être cité ; « Avizen
// couvre le décès » si. On cible donc ce qui ASSERTE un comportement du contrat.
const CTR = /(couv|garanti|exclu|verse|prévoit|plafonn|indemnis|prise? en charge|s'applique|franchise|carence|délai de|remboursé|éligib)/i;
const REG = /(abattement|barème|plafond fiscal|déduct|madelin|990\s*I|757\s*B|taux\s|impôt|fiscalit)/i;
const REDIR = /(source officielle|réglementaire|législation|impots\.gouv|service-public|urssaf|autorité|évolue|à vérifier (sur|auprès)|non présent dans la base)/i;
const CITE = /\[[^\]]*(?:notice|p\.?\s*\d)/i;
const NUM = /\d/;
const NOMINATIF = /\b(monsieur|madame|m\.|mme)\s+[A-ZÉÈÀ][a-zé]+|\b\d{2}[.\s]?\d{2}[.\s]?\d{2}[.\s]?\d{2}[.\s]?\d{2}\b|@[a-z0-9.-]+\.[a-z]{2,}/i;

// Normalisation légère pour rapprocher un nom cité d'un contrat de l'index.
const cle = s => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]/g, "");
// Cœur d'un nom de notice : sans la date de tête ni l'extension (« 2025-06 Notice … Essen'Ciel.pdf »
// → « Notice … Essen'Ciel »). Sert à identifier le contrat cité SANS ambiguïté préfixe.
const noticeCore = f => cle(String(f || "").replace(/^\s*\d{4}-\d{2}\s*/, "").replace(/\.pdf$/i, ""));
// Identifie le contrat d'une citation : parmi ceux dont le cœur de notice (ou le nom) est contenu
// dans le texte cité, on retient le PLUS SPÉCIFIQUE (le plus long) — « …Essen'Ciel Patrimoine »
// l'emporte sur « …Essen'Ciel », et « p.14 » ne peut plus matcher « Patrimoine » par accident.
function identifierContrat(cInner, contrats) {
  const cand = [];
  for (const c of contrats) {
    const core = noticeCore(c.notice_court), nom = cle(c.nom);
    if (core.length > 8 && cInner.includes(core)) cand.push({ c, poids: core.length });
    else if (nom.length > 8 && cInner.includes(nom)) cand.push({ c, poids: nom.length });
  }
  if (!cand.length) return null;
  cand.sort((a, b) => b.poids - a.poids);
  return cand[0].c;
}

// Contrôle des citations [Contrat — Notice…, p.X, §Y] contre l'index section→page.
// Attrape : page hors bornes, décalage GROSSIER d'une section, contrat non identifié. Ne certifie
// JAMAIS la page exacte (un fait est à 0–2 pages du début de sa section — mesuré). Localise, guide.
function verifierCitations(texte, index) {
  if (!index || !index.contrats) return [];
  const out = [];
  const TOL = (index.meta && index.meta.tolerance_pages) || 2;
  const contrats = Object.values(index.contrats);
  // [ ... p.14 ... §3.1 ]  ou  [ ... p.14, 3.1 ]
  const reCit = /\[([^\]]*?p\.?\s*\d{1,3}[^\]]*)\]/gi;
  let m;
  while ((m = reCit.exec(texte)) !== null) {
    const inner = m[1];
    const pg = Number((inner.match(/p\.?\s*(\d{1,3})/i) || [])[1]);
    if (!pg) continue;
    const secM = inner.match(/§\s*(\d+(?:\.\d+){1,2})|(?:^|[,;\s])(\d+\.\d+(?:\.\d+)?)(?=[\s,;\]])/);
    const sec = secM ? (secM[1] || secM[2]) : null;
    // Identifier le contrat (le plus spécifique), sans ambiguïté préfixe.
    const cInner = cle(inner);
    const hit = identifierContrat(cInner, contrats);
    const label = inner.trim().slice(0, 55);
    if (!hit) { out.push({ niveau: "info", regle: "citation_non_identifiee", message: `Citation « ${label} » : contrat non identifié dans l'index — page non vérifiable.` }); continue; }
    if (pg < 1 || pg > hit.total_pages) {
      out.push({ niveau: "grave", regle: "page_hors_bornes", message: `Citation « ${label} » : page ${pg} HORS BORNES pour ${hit.nom} (notice de ${hit.total_pages} pages) — page probablement inventée.` });
      continue;
    }
    if (sec && hit.sections[sec] != null) {
      const deb = hit.sections[sec];
      if (pg < deb - 1 || pg > deb + TOL + 1) {
        out.push({ niveau: "grave", regle: "section_page_incoherente", message: `Citation « ${label} » : le § ${sec} de ${hit.nom} débute p.${deb}, or tu cites p.${pg} — décalage trop grand, vérifie.` });
      } else {
        out.push({ niveau: "info", regle: "citation_a_confirmer", message: `§ ${sec} de ${hit.nom} débute p.${deb} (tu cites p.${pg}, cohérent) — confirme que le FAIT est bien à cette page : un fait s'étale sur 1–3 pages, cet outil ne certifie pas la page exacte.` });
      }
    }
  }
  return out;
}

function analyser(texte, index) {
  const t = String(texte || "");
  const defauts = [];
  if (!t.trim()) return { erreur: "Aucun texte fourni. Envoie le brouillon de réponse à vérifier (paramètre ?texte= en GET, ou corps de la requête en POST)." };

  // Tolérant à l'accent et aux aléas d'encodage : « consultée », « consultee », etc.
  if (!/Base\s+consult\S*\s*:?\s*Gabriel\s+AXA/i.test(t))
    defauts.push({ niveau: "grave", regle: "attestation", message: "La réponse ne commence pas par « Base consultée : Gabriel AXA vX.X.X » (règle 0) — impossible de prouver que la base a été lue." });
  if (!/notice\s+PDF\s+fait\s+foi/i.test(t))
    defauts.push({ niveau: "moyen", regle: "cloture", message: "Clôture manquante : « La notice PDF fait foi. »" });
  if (NOMINATIF.test(t))
    defauts.push({ niveau: "grave", regle: "nominatif", message: "La réponse semble contenir une donnée nominative (nom, téléphone ou email). Aucune donnée client ne doit apparaître — anonymise." });

  const phr = t.split(/(?<=[.!?])\s+|\n+/);
  const exemples = [];
  let nSansCite = 0;
  for (const raw of phr) {
    const p = raw.trim();
    if (p.length < 12) continue;
    if (CTR.test(p) && !REDIR.test(p) && !CITE.test(p)) {
      nSansCite++;
      if (exemples.length < 3) exemples.push(p.slice(0, 100));
    }
  }
  if (nSansCite > 0)
    defauts.push({ niveau: "grave", regle: "citation", nombre: nSansCite,
      message: `${nSansCite} affirmation(s) contractuelle(s) sans citation [Contrat — Notice, p.X].`, exemples });

  for (const q of phr) {
    if (REG.test(q) && NUM.test(q) && !REDIR.test(q)) {
      defauts.push({ niveau: "grave", regle: "reglementaire_sans_source",
        message: "Un chiffre réglementaire (plafond/abattement/taux) apparaît sans renvoi à une source officielle. Le réglementaire évolue : jamais de chiffre de mémoire.",
        exemple: q.trim().slice(0, 100) });
      break;
    }
  }
  for (const d of verifierCitations(t, index)) defauts.push(d);   // bornes + décalage de section (jamais la page exacte)
  // « propre » ne compte que les défauts à corriger (grave/moyen) ; les « info » sont des aides.
  const bloquants = defauts.filter(d => d.niveau !== "info");
  return {
    propre: bloquants.length === 0,
    note: "Contrôle MÉCANIQUE de la forme (citations, source officielle, clôture, attestation, absence de nominatif) " +
          "et des pages citées (bornes + décalage de section). Il ne certifie PAS la page exacte ni l'exactitude du " +
          "contenu — la notice PDF fait foi.",
    defauts,
  };
}

async function chargerIndex(env, request) {
  try {
    const r = await env.ASSETS.fetch(new Request(new URL("/ia/citations-index.json", request.url)));
    return r.ok ? await r.json() : null;
  } catch { return null; }
}

function reponseJSON(obj, status = 200) {
  return new Response(JSON.stringify(obj, null, 1), {
    status, headers: { "Content-Type": "application/json; charset=utf-8", "Access-Control-Allow-Origin": "*", "Cache-Control": "no-store" },
  });
}

// GET ?texte=... (brouillons courts)
export async function onRequestGet({ request, env }) {
  const texte = new URL(request.url).searchParams.get("texte");
  if (texte === null) {
    return reponseJSON({
      usage: "Envoie un brouillon de réponse à vérifier. GET avec ?texte=<url-encodé> (courts), ou POST avec le texte " +
             "dans le corps (recommandé pour un vrai brouillon). Renvoie les défauts de forme à corriger avant d'envoyer.",
      controle: ["attestation de lecture présente", "chaque fait contractuel cité [Contrat — Notice, p.X]",
                 "chiffre réglementaire renvoyé à une source officielle", "clôture « la notice PDF fait foi »",
                 "aucune donnée nominative", "page citée dans les bornes de la notice et cohérente avec sa section"],
      note: "Contrôle mécanique de la forme, pas de l'exactitude. Il localise la section d'une citation mais ne " +
            "certifie pas la page exacte (un fait est à 0–2 pages du début de sa section). Écriture nulle.",
    });
  }
  const index = await chargerIndex(env, request);
  const r = analyser(texte, index);
  return reponseJSON(r, r.erreur ? 400 : 200);
}

// POST : le corps EST le brouillon (texte brut, ou JSON {"texte": "..."}). Aucune écriture.
export async function onRequestPost({ request, env }) {
  let texte = "";
  try {
    const brut = await request.text();
    if (/^\s*[{[]/.test(brut)) { try { const j = JSON.parse(brut); texte = j.texte ?? j.text ?? brut; } catch { texte = brut; } }
    else texte = brut;
  } catch { texte = ""; }
  const index = await chargerIndex(env, request);
  const r = analyser(texte, index);
  return reponseJSON(r, r.erreur ? 400 : 200);
}
