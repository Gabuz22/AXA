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

const CTR = /(garanti|garantie|couvr|exclu|exclusion|franchise|carence|délai|plafond|capital|rente|cotisation|indemnit|prestation|décès|invalidit|incapacit)/i;
const REG = /(abattement|barème|plafond fiscal|déductib|990\s*I|757\s*B|taux\s|impôt|fiscalit)/i;
const REDIR = /(source officielle|réglementaire|législation|impots\.gouv|service-public|urssaf|autorité|évolue|à vérifier (sur|auprès)|non présent dans la base)/i;
const CITE = /\[[^\]]*(?:notice|p\.?\s*\d)/i;
const NUM = /\d/;
const NOMINATIF = /\b(monsieur|madame|m\.|mme)\s+[A-ZÉÈÀ][a-zé]+|\b\d{2}[.\s]?\d{2}[.\s]?\d{2}[.\s]?\d{2}[.\s]?\d{2}\b|@[a-z0-9.-]+\.[a-z]{2,}/i;

function analyser(texte) {
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
  return {
    propre: defauts.length === 0,
    note: "Contrôle MÉCANIQUE de la forme (citations, source officielle, clôture, attestation, absence de nominatif). " +
          "Il ne juge PAS l'exactitude du contenu — la notice PDF fait foi.",
    defauts,
  };
}

function reponseJSON(obj, status = 200) {
  return new Response(JSON.stringify(obj, null, 1), {
    status, headers: { "Content-Type": "application/json; charset=utf-8", "Access-Control-Allow-Origin": "*", "Cache-Control": "no-store" },
  });
}

// GET ?texte=... (brouillons courts)
export async function onRequestGet({ request }) {
  const texte = new URL(request.url).searchParams.get("texte");
  if (texte === null) {
    return reponseJSON({
      usage: "Envoie un brouillon de réponse à vérifier. GET avec ?texte=<url-encodé> (courts), ou POST avec le texte " +
             "dans le corps (recommandé pour un vrai brouillon). Renvoie les défauts de forme à corriger avant d'envoyer.",
      controle: ["attestation de lecture présente", "chaque fait contractuel cité [Contrat — Notice, p.X]",
                 "chiffre réglementaire renvoyé à une source officielle", "clôture « la notice PDF fait foi »",
                 "aucune donnée nominative"],
      note: "Contrôle mécanique de la forme, pas de l'exactitude. Écriture nulle : le texte est analysé puis jeté.",
    });
  }
  const r = analyser(texte);
  return reponseJSON(r, r.erreur ? 400 : 200);
}

// POST : le corps EST le brouillon (texte brut, ou JSON {"texte": "..."}). Aucune écriture.
export async function onRequestPost({ request }) {
  let texte = "";
  try {
    const brut = await request.text();
    if (/^\s*[{[]/.test(brut)) { try { const j = JSON.parse(brut); texte = j.texte ?? j.text ?? brut; } catch { texte = brut; } }
    else texte = brut;
  } catch { texte = ""; }
  const r = analyser(texte);
  return reponseJSON(r, r.erreur ? 400 : 200);
}
