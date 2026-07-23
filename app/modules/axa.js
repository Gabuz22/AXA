// axa — espace AXA CONSEILLER (V1.3) : assistant de travail complet, indépendant du Patrimoine.
// Routes : #/<section> — accueil, contrat, recherche, assistant, besoins,
// sources, pdf, historique, parametres. Les données viennent du service
// axaKnowledge (piloté par data/AXA/workspace_manifest.json — architecture évolutive).
import * as kb from "../services/axaKnowledge.js";
import { get, set } from "../state/store.js";
import { isEmpty } from "../services/humanView.js";
import { renderMarkdown } from "../services/markdown.js";
import { TUTORIEL, FAMILLE_META, ERREURS_TRANSVERSES, OBJECTIFS } from "./axa_content.js";
import { prospection } from "./prospection.js";
import { calculs } from "./calculs.js";
import { preselection } from "../services/axaPreselection.js";

// Sections réellement implémentées (garde-fou anti-lien-mort : un parcours ne s'affiche
// que si sa cible existe). RDV/animateur s'activent automatiquement à leur implémentation.
const IMPLEMENTED = new Set(["accueil", "premiers_pas", "copilote", "contrat", "recherche", "glossaire",
  "besoins", "rdv", "animateur", "argumentaire", "assistants", "sources", "pdf", "historique", "parametres"]);

const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;" }[c]));

// Impression PDF sans dépendance (quick win 4) : isole l'élément cible via CSS @media print
// (déplie les accordéons pour tout imprimer), puis window.print(). Aucune librairie.
function printTarget(el) {
  if (!el) return;
  el.querySelectorAll("details").forEach(d => d.open = true);
  el.classList.add("print-target"); document.body.classList.add("printing");
  const done = () => { el.classList.remove("print-target"); document.body.classList.remove("printing"); window.removeEventListener("afterprint", done); };
  window.addEventListener("afterprint", done);
  setTimeout(() => window.print(), 60);
}
const printBtnHtml = (id, label = "🖨 Imprimer") => `<button class="btn ghost" id="${id}" style="min-height:30px;padding:0 10px">${label}</button>`;

// Copie presse-papiers avec retour visuel sur un bouton.
function bindCopy(btn, getText, done = "✓ Copié") {
  if (!btn) return;
  btn.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(getText()); const t = btn.textContent; btn.textContent = done; setTimeout(() => btn.textContent = t, 1500); }
    catch { btn.textContent = "⚠ copie refusée"; }
  });
}

export const title = "Gabriel AXA";

// Mention d'indépendance (phase de test) — UNE seule formulation, réutilisée telle quelle sur
// les écrans où elle doit être visible (accueil, tester, assistants, confiance) pour rester
// cohérente. Consigne produit pour la version de test ; pas une validation juridique définitive.
const INDEP_COURT = `Outil <b>indépendant et non officiel</b>, non affilié ni validé par AXA — construit à partir de documents accessibles publiquement.`;
const INDEP_COMPLET = `${INDEP_COURT} Les notices contractuelles et les sources officielles font foi. Toute information doit être <b>vérifiée humainement</b> avant une réponse ou une recommandation au client.`;
// Gabriel AXA : le shell (app.js) fournit la navigation et l'en-tête ; ce module rend UNE section.
// Vue conseiller uniquement (pas de mode « technique/IA » : jargon retiré du produit métier).
export async function mount(el, ctx) {
  const section = ctx?.section || ctx?.path?.[0] || "accueil";
  const human = true;
  el.innerHTML = `<div class="view-body">Chargement…</div>`;
  const body = el.querySelector(".view-body");
  const render = { accueil, decouvrir, cas_usage, portail_ia, tester, premiers_pas, copilote, contrat, recherche, glossaire, assistants, confiance, besoins, rdv, prospection, calculs, animateur, argumentaire, sources, pdf, historique, parametres }[section] || accueil;
  try { await render(body, human, ctx); }
  catch (e) { body.innerHTML = `<p class="warn">Erreur de la section (${esc(e.message)}).</p>`; }
}

/* ---------- Accueil (Chantier 8 — orienté intention : « que veux-tu faire ? ») ---------- */
async function accueil(body) {
  const idx = await kb.source("index_global");
  const stats = idx?.statistiques;
  const resume = await kb.source("contrats_resume_humain");
  const dates = (resume?.contrats || []).map(c => c.date_document).filter(Boolean).sort();
  const EXEMPLES = ["délai de carence", "exclusions décès", "rachat possible ?", "invalidité IPT", "fiscalité transmission"];
  const gotoSearch = q => { set({ axaQuery: (q || "").trim() }); location.hash = "#/recherche"; };
  // Entrées par intention — chaque tuile répond à « je veux… ».
  const INTENTS = [
    ["🧠", "Poser une question", "#/copilote", "preuves + pistes, sourcées"],
    ["📑", "Comprendre un contrat", "#/contrat", "l'essentiel, le mécanisme, les preuves"],
    ["🧩", "Analyser un cas client", "#/besoins", "diagnostic progressif, statuts clairs"],
    ["🗓", "Préparer un rendez-vous", "#/rdv", "avant · pendant · après"],
    ["🗣", "Construire un argumentaire", "#/argumentaire", "trame éditable, sourcée"],
    ["📖", "Vérifier un terme", "#/glossaire", "définitions sourcées par contrat"],
    ["🤖", "Travailler avec une IA", "#/assistants", "un mini-prompt à coller"],
  ];
  // Reprendre : dernières recherches locales + dernier contexte de travail.
  const hist = (kb.history() || []).slice(0, 3);
  const back = get("axaBack");
  const backLbl = { recherche: "ta recherche", copilote: "ta question au copilote", contrat: "la fiche" }[back?.from];
  const reprendre = (hist.length || (back?.q && backLbl)) ? `<h3 class="day-h">Reprendre</h3><div class="filters">
      ${back?.q && backLbl ? `<button class="chip on" id="acc_back">↩ ${backLbl} « ${esc(back.q.length > 36 ? back.q.slice(0, 36) + "…" : back.q)} »</button>` : ""}
      ${hist.map(h => `<button class="chip" data-ex="${esc(h.q)}">🔎 ${esc(h.q)}</button>`).join("")}
      ${hist.length ? `<a class="chip" href="#/historique">🕘 tout l'historique</a>` : ""}</div>` : "";
  body.innerHTML = `
    <section class="hero">
      <h2 class="hero-t">Trouve la bonne réponse contractuelle, <span class="hero-u">sourcée</span>, en quelques secondes.</h2>
      <p class="hero-s">Tape ta question comme tu la poserais à un collègue. Gabriel AXA cherche dans tous les contrats
      et te renvoie la garantie, l'exclusion ou la condition — avec la notice qui fait foi.</p>
      <div class="hero-search"><span class="hero-ic">🔎</span>
        <input id="acc_q" placeholder="Ex : le décès accidentel est-il couvert par MasterLife ?" aria-label="Rechercher une info contractuelle">
        <button class="btn gold" id="acc_go">Rechercher</button></div>
      <div class="filters" id="acc_ex"><span class="muted" style="align-self:center;font-size:12px;margin-right:2px">Exemples :</span>
        ${EXEMPLES.map(x => `<button class="chip" data-ex="${esc(x)}">${esc(x)}</button>`).join("")}</div>
      <p class="hero-new">Nouveau ici ? <a href="#/decouvrir">✨ Découvrir Gabriel AXA en 2 minutes</a> · <a href="#/cas_usage">🎯 Que puis-je faire ?</a></p>
    </section>
    ${reprendre}
    <h3 class="day-h">Que veux-tu faire ?</h3>
    <div class="grid">${INTENTS.map(([i, l, h, s]) => tile(i, l, h, s)).join("")}</div>
    <p class="muted" style="margin-top:16px">${stats ? `Base : <b>${stats.contrats}</b> contrats · <b>${stats.faits_uniques}</b> faits sourcés${dates.length ? ` · notices de ${esc(dates[0])} à ${esc(dates[dates.length - 1])} (chaque fiche affiche la sienne)` : ""}. ` : ""}
    Aucune donnée client dans la base contractuelle. <b>La notice PDF fait toujours foi.</b> <a href="#/pdf">📄 Notices</a></p>
    <p class="muted">${INDEP_COURT} <a href="#/confiance">🔒 Origine des données</a></p>`;
  body.querySelector("#acc_go").onclick = () => gotoSearch(body.querySelector("#acc_q").value);
  body.querySelector("#acc_q").addEventListener("keydown", e => { if (e.key === "Enter") gotoSearch(e.target.value); });
  body.addEventListener("click", e => { const b = e.target.closest("[data-ex]"); if (b) gotoSearch(b.dataset.ex); });
  body.querySelector("#acc_back")?.addEventListener("click", () => {
    if (back.from === "contrat") { location.hash = "#/contrat/" + back.q.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]/g, ""); return; }
    set({ axaQuery: back.q }); location.hash = "#/" + (back.from === "copilote" ? "copilote" : "recherche");
  });
}
function tile(icon, label, href, sub) {
  return `<a class="tile" href="${href}"><span class="tile-i">${icon}</span><span class="tile-l">${esc(label)}</span><span class="tile-s">${esc(sub)}</span></a>`;
}

/* ---------- Premiers pas, FAQ, exemples, bonnes pratiques, limites ---------- */
const PP_EXEMPLES = ["délai de carence décès", "exclusions garantie décès", "rachat possible", "conditions d'âge à l'adhésion", "fiscalité transmission", "invalidité IPT"];
const PP_FAQ = [
  ["Qu'est-ce que Gabriel AXA ?", "Un assistant de recherche dans la base contractuelle AXA (garanties, exclusions, conditions, définitions), à partir de documents publics. Il fait gagner du temps ; il ne remplace pas la notice, qui fait toujours foi."],
  ["Est-ce que ça contient des données client ?", "La base contractuelle, non : les documents embarqués proviennent de sources publiques (notices d'information, conditions générales). Seul l'outil Prospection stocke des coordonnées, et uniquement dans TON navigateur — jamais envoyées, jamais transmises à une IA."],
  ["Puis-je répondre à un client à partir d'un résultat ?", "Le résultat vous oriente et cite sa source. Avant toute réponse ferme, vérifiez la notice PDF à la page indiquée : c'est elle qui fait foi."],
  ["Comment chercher efficacement ?", "Tapez en langage naturel (« le décès accidentel est-il couvert ? »). Les synonymes métier sont tolérés. Filtrez ensuite par type (garantie, exclusion, définition…)."],
  ["Comment utiliser Gabriel AXA avec une IA ?", "Ouvrez « Utiliser avec une IA », copiez le mini-prompt et collez-le dans votre assistant (ChatGPT, Claude, Gemini…). L'IA découvre seule Gabriel AXA, applique ses instructions et répond en citant ses sources."],
  ["Ça marche sur mobile ?", "Oui, l'interface est responsive. La recherche et les fiches sont utilisables sur téléphone."],
];
async function premiers_pas(body) {
  body.innerHTML = `
    <p class="lead">Nouveau sur Gabriel AXA ? L'essentiel en 3 minutes : chercher une information contractuelle,
    ouvrir la fiche, vérifier la source. <a href="#/assistants">→ Utiliser avec ChatGPT / Claude</a></p>

    <h3 class="day-h">Guide rapide</h3>
    <div class="card"><div class="md" id="tuto_md">Rendu…</div></div>

    <h3 class="day-h">Exemples de recherches</h3>
    <div class="filters" id="pp_ex">${PP_EXEMPLES.map(x => `<button class="chip" data-ex="${esc(x)}">${esc(x)}</button>`).join("")}</div>

    <h3 class="day-h">Bonnes pratiques</h3>
    <ul class="hlist">
      <li>Partez d'une question concrète, comme à un collègue.</li>
      <li>Repérez le <b>type</b> du résultat (garantie / exclusion / condition) et son contrat.</li>
      <li><b>Ouvrez la notice</b> à la page citée avant toute réponse client.</li>
    </ul>

    <h3 class="day-h">Limites</h3>
    <ul class="hlist">
      <li>Gabriel AXA <b>n'invente rien</b> : si une information n'est pas dans la base, il ne la fabrique pas.</li>
      <li>Certains tableaux chiffrés (valeurs de rachat, barèmes) sont à <b>vérifier dans la notice</b>.</li>
      <li>La <b>notice PDF fait foi</b> — l'application est une aide, pas une source contractuelle.</li>
    </ul>

    <h3 class="day-h">Questions fréquentes</h3>
    ${PP_FAQ.map(([q, a]) => `<details class="acc"><summary>${esc(q)}</summary><p class="card-b">${esc(a)}</p></details>`).join("")}`;
  const md = body.querySelector("#tuto_md");
  renderMarkdown(TUTORIEL).then(h => { md.innerHTML = h; }).catch(() => { md.textContent = TUTORIEL; });
  body.querySelector("#pp_ex").addEventListener("click", e => {
    const b = e.target.closest("[data-ex]"); if (!b) return;
    set({ axaQuery: b.dataset.ex }); location.hash = "#/recherche";
  });
}

/* ---------- Pourquoi faire confiance aux résultats (Partie 8) ---------- */
async function confiance(body) {
  const idx = await kb.source("index_global");
  const s = idx?.statistiques;
  body.innerHTML = `
    <p class="lead">Gabriel AXA ne « génère » pas de réponses : il <b>retrouve</b> une information déjà écrite dans un
    document AXA et vous <b>renvoie à sa source</b>. Voici pourquoi vous pouvez vous y fier.</p>

    <div class="grid">
      ${tile("📄", "Documents publics", "#/pdf", "notices d'information & CG diffusées par AXA")}
      ${tile("🔗", "Tout est tracé", "#/contrat", "chaque fait cite sa notice et sa page")}
      ${tile("🧠", "Preuve vs raisonnement", "#/assistants", "Pack A = preuve · Pack B = aide")}
    </div>

    <h3 class="day-h">Indépendance</h3>
    <div class="card"><p class="card-b">${INDEP_COMPLET}</p></div>

    <h3 class="day-h">Origine des données</h3>
    <div class="card"><p class="card-b">Les informations proviennent exclusivement des <b>notices d'information et conditions
    générales</b> des produits AXA — des documents <b>publics</b>, remis à tout prospect. Aucune donnée client dans cette base, aucune
    donnée interne, aucune source privée.</p></div>

    <h3 class="day-h">Traçabilité</h3>
    <div class="card"><p class="card-b">Chaque garantie, exclusion, condition ou définition affichée porte un
    <b>badge « 📄 Notice p.X »</b> qui ouvre le PDF à la bonne page. Rien n'est présenté sans sa source.
    ${s ? `La base couvre <b>${s.contrats} contrats</b> et ${s.faits_uniques ? `<b>${s.faits_uniques} faits contractuels</b> sourcés` : "des faits sourcés"}.` : ""}</p></div>

    <h3 class="day-h">Aucune invention</h3>
    <div class="card"><p class="card-b">L'application ne complète jamais un manque par une supposition. Si une information
    n'existe pas dans la base, elle n'apparaît pas — et un tableau chiffré est signalé « à vérifier dans la notice ».
    Les couches de données sont <b>dérivées</b> des documents sources ; les fichiers d'origine (masters) ne sont jamais réécrits.</p></div>

    <h3 class="day-h">La règle qui prime</h3>
    <div class="card"><p class="card-b"><b>La notice PDF fait toujours foi.</b> Gabriel AXA vous fait gagner du temps pour
    <i>trouver</i> et <i>situer</i> l'information ; la réponse au client se valide sur la notice.</p>
      <div class="btns"><a class="btn gold" href="#/recherche">🔎 Essayer une recherche</a><a class="btn ghost" href="#/pdf">📄 Voir les notices</a></div></div>`;
}

/* ---------- Utiliser avec une IA (protocole : donner Gabriel AXA à son IA) ---------- */
const IA_URL = "https://gabuz22.github.io/AXA/ia/";
const IA_START_URL = IA_URL + "start.html";
const IA_INSTRUCTIONS_URL = IA_URL + "instructions-maitres.html";
const IA_TXT_REL = "../ia/instructions-maitres.txt"; // même origine (app et /ia servis sous /AXA/)
// Mini-prompt : le SEUL texte que le conseiller manipule. L'IA découvre et applique seule Gabriel AXA.
const MINI_PROMPT = `Utilise Gabriel AXA :
${IA_START_URL}

Lis d'abord cette page d'initialisation pour les IA, applique son protocole, puis réponds.
N'utilise jamais ta mémoire générale sur les contrats AXA : uniquement les pages de cette base, citées.

Ma question : `;

async function assistants(body) {
  body.innerHTML = `
    <p class="lead">Tu n'as rien à apprendre de Gabriel AXA : tu le <b>donnes à ton IA</b>. Copie ces quelques lignes,
    colle-les dans ton assistant, puis pose tes questions normalement. <b>L'IA découvre seule Gabriel AXA</b>,
    lit ses instructions et choisit le bon parcours pour te répondre — sources à l'appui.</p>

    <h3 class="day-h">Étape 1 · Copiez ces instructions</h3>
    <div class="card">
      <pre class="prompt" style="white-space:pre-wrap;background:var(--surface-2);border:1px solid var(--line);border-radius:8px;padding:12px;font-size:13px;margin:0 0 10px">${esc(MINI_PROMPT)}</pre>
      <div class="btns"><button class="btn gold" id="mini_copy">📋 Copier les instructions</button></div>
    </div>

    <h3 class="day-h">Étape 2 · Ouvrez votre IA</h3>
    <div class="filters">${["ChatGPT", "Claude", "Gemini", "Copilot", "Mistral", "DeepSeek", "Qwen"].map(n => `<span class="chip">${n}</span>`).join("")}</div>
    <p class="muted" style="margin-top:6px">N'importe quelle IA capable de lire une page web convient. Le protocole ne dépend d'aucune d'elles.</p>

    <h3 class="day-h">Étape 3 · Collez les instructions</h3>
    <p class="muted">Dans une <b>nouvelle conversation</b>, collez ce que vous venez de copier.</p>

    <h3 class="day-h">Étape 4 · Posez vos questions</h3>
    <p class="muted">Écrivez votre question à la suite, <b>normalement</b>. L'IA applique le protocole Gabriel AXA :
    elle classe la question, consulte les bons outils et répond en citant contrat, notice et page.</p>

    <div class="warnbox">⚠ La <b>notice PDF fait foi</b>. Selon ses capacités web, une IA peut ne pas ouvrir les liens — vérifiez
    toujours la source avant d'utiliser une réponse avec un client. Ne collez <b>aucune donnée client nominative</b> dans une IA externe (les coordonnées de l'outil Prospection restent dans ton navigateur et ne doivent jamais être copiées dans une IA).
    ${INDEP_COURT}</div>

    <p class="muted" style="margin-top:16px">Votre IA n'ouvre pas les liens ?
      <button class="btn ghost" id="full_copy" style="min-height:30px;padding:0 10px">📋 Copier les instructions complètes</button>
      <a class="btn ghost" href="${IA_INSTRUCTIONS_URL}" target="_blank" rel="noopener" style="min-height:30px;padding:0 10px">↗ Voir les instructions</a>
      <span id="full_state" class="ok" style="font-size:12.5px"></span></p>
    <p class="muted" style="font-size:12px">C'est un secours — le parcours recommandé reste le mini-prompt ci-dessus.</p>`;

  bindCopy(body.querySelector("#mini_copy"), () => MINI_PROMPT, "✓ Instructions copiées");

  // Secours : copie le prompt maître complet, récupéré depuis la Vue IA (même origine). Repli : ouvrir la page.
  body.querySelector("#full_copy").addEventListener("click", async () => {
    const st = body.querySelector("#full_state");
    try {
      const r = await fetch(IA_TXT_REL, { cache: "no-cache" });
      if (!r.ok) throw new Error(String(r.status));
      await navigator.clipboard.writeText(await r.text());
      st.textContent = " ✓ Instructions complètes copiées";
    } catch (e) {
      window.open(IA_INSTRUCTIONS_URL, "_blank", "noopener");
      st.textContent = " ↗ Page ouverte — copiez le texte manuellement";
    }
  });
}

/* ---------- Découvrir Gabriel AXA (onboarding) ---------- */
async function decouvrir(body) {
  body.innerHTML = `
    <p class="lead">Gabriel AXA, c'est <b>la base contractuelle AXA — sourcée — que tu interroges en langage naturel</b>.
    Retrouve en quelques secondes une garantie, une exclusion, une condition ou une définition, avec la notice qui fait foi.</p>
    <div class="grid">
      ${tile("⏱", "Pourquoi ça existe", "#/recherche", "gagner du temps : ne plus feuilleter les notices pour un détail")}
      ${tile("👥", "À qui c'est destiné", "#/cas_usage", "conseillers épargne/protection, débutants ou expérimentés, animateurs")}
      ${tile("📄", "Sur quoi c'est fondé", "#/confiance", "documents publics uniquement (notices, CG). Aucune donnée client dans la base.")}
    </div>
    <h3 class="day-h">Ce que ça remplace… et ce que ça ne remplace pas</h3>
    <div class="grid">
      <div class="card"><div class="fiche-retenir-h" style="color:var(--ok)">Ça remplace</div>
        <ul class="hlist"><li>la recherche manuelle dans les PDF</li><li>« quel contrat couvre déjà ça ? »</li><li>retrouver une exclusion ou un délai précis</li></ul></div>
      <div class="card"><div class="fiche-retenir-h" style="color:var(--warn)">Ça ne remplace pas</div>
        <ul class="hlist"><li>la <b>notice PDF</b>, qui fait foi</li><li>ton conseil et ta relation client</li><li>une vérification réglementaire officielle</li></ul></div>
    </div>
    <h3 class="day-h">Essayer maintenant</h3>
    <div class="btns"><a class="btn gold" href="#/recherche">🔎 Lancer une recherche</a>
      <a class="btn" href="#/cas_usage">🎯 Voir des exemples</a>
      <a class="btn ghost" href="#/assistants">🤖 Utiliser avec une IA</a></div>`;
}

/* ---------- Que puis-je faire ? (cas d'usage cliquables) ---------- */
async function cas_usage(body) {
  const CU = [
    ["🔎", "Retrouver une clause", "recherche", "capital décès MasterLife"],
    ["🚫", "Vérifier une exclusion", "recherche", "exclusions garantie décès"],
    ["⏳", "Trouver un délai de carence", "recherche", "délai de carence"],
    ["📖", "Comprendre une définition", "glossaire", ""],
    ["🧠", "Construire un premier raisonnement", "copilote", ""],
    ["🧩", "Analyser un cas client", "besoins", ""],
    ["🗣", "Construire un argumentaire", "argumentaire", ""],
    ["🤖", "Analyse multi-contrats (IA)", "assistants", ""],
    ["🗓", "Préparer un rendez-vous", "rdv", ""],
  ];
  body.innerHTML = `<p class="lead">Des exemples concrets de ce que tu peux faire aujourd'hui. <b>Clique pour l'essayer tout de suite.</b></p>
    <div class="grid" id="cu">${CU.map(([ic, t, r, q]) => `<a class="tile" href="#/${r}" data-route="${r}" data-q="${esc(q)}"><span class="tile-i">${ic}</span><span class="tile-l">${esc(t)}</span><span class="tile-s">${q ? esc("« " + q + " »") : "ouvrir →"}</span></a>`).join("")}</div>
    <p class="muted" style="margin-top:14px">Chaque réponse renvoie à sa <b>notice PDF</b> (la source qui fait foi).</p>`;
  body.querySelector("#cu").addEventListener("click", e => {
    const a = e.target.closest("[data-route]"); if (!a) return; e.preventDefault();
    if (a.dataset.q) set({ axaQuery: a.dataset.q });
    location.hash = "#/" + a.dataset.route;
  });
}

/* ---------- Portail Vue IA (valoriser la couche IA) ---------- */
async function portail_ia(body) {
  const P = [
    ["🧭", "Guide IA", "guide-ia.html", "comment une IA doit répondre : citer, ne pas inventer, arbitrer"],
    ["🕸️", "Concepts", "concepts.html", "synonymes métier reliés aux contrats (IPT, PTIA…)"],
    ["🚦", "Routage", "routage.html", "décomposer une question, choisir les bons contrats"],
    ["⚖️", "Comparateur (pour ton IA)", "comparateur.html", "un sujet, tous les contrats côte à côte"],
    ["🧪", "Méthode", "methode-question-complexe.html", "les parcours pour une question complexe"],
    ["✅", "Qualité", "qualite-routage.html", "mesures de précision du moteur"],
    ["🧾", "Tests", "tests.html", "questions de contrôle et parcours attendus"],
    ["🔢", "Matrices", "matrices.html", "contrats × catégories, concepts × contrats"],
    ["📚", "Sources", "sources-officielles.html", "autorités officielles par thème"],
    ["🧰", "Outils", "outils.html", "tous les outils de circulation"],
  ];
  body.innerHTML = `<p class="lead">La <b>Vue IA</b> est l'espace conçu pour les intelligences artificielles : une projection
    complète et sourcée de la base, lisible sans exécuter de code. Parcours-la, ou <b>copie son adresse pour ton IA</b>.</p>
    <div class="btns"><a class="btn gold" href="${IA_URL}" target="_blank" rel="noopener">↗ Ouvrir la Vue IA</a>
      <button class="btn" id="pia_copy">📋 Copier l'adresse</button>
      <a class="btn ghost" href="#/assistants">🤖 Comment l'utiliser</a></div>
    <h3 class="day-h">Ce qu'elle contient</h3>
    <div class="grid">${P.map(([ic, t, f, d]) => `<a class="tile" href="${IA_URL}${f}" target="_blank" rel="noopener"><span class="tile-i">${ic}</span><span class="tile-l">${esc(t)} ↗</span><span class="tile-s">${esc(d)}</span></a>`).join("")}</div>`;
  bindCopy(body.querySelector("#pia_copy"), () => IA_URL, "✓ Adresse copiée");
}

/* ---------- Tester Gabriel AXA (phase de test conseillers) ----------
   Retours EN LOCAL uniquement (ce navigateur, localStorage) — rien n'est envoyé nulle part.
   Volontaire, minimal, aucune donnée client : le testeur copie son texte et le colle lui-même
   dans le canal de test (le groupe Matrix). Pas de collecte, pas de backend, pas d'analytics. */
const LS_FEEDBACK = "gv_axa_feedback_v1";
const lireRetours = () => { try { return JSON.parse(localStorage.getItem(LS_FEEDBACK)) || []; } catch { return []; } };
const ecrireRetours = v => { try { localStorage.setItem(LS_FEEDBACK, JSON.stringify(v)); } catch {} };
function retourTexte(r) {
  return [
    `Recherche testée : ${r.recherche || "—"}`,
    `Contrat concerné : ${r.contrat || "—"}`,
    `A trouvé l'info : ${r.trouve}`,
    `Utilité perçue : ${r.utilite}`,
    `IA utilisée : ${r.ia}`,
    r.commentaire ? `Commentaire : ${r.commentaire}` : null,
    `— ${new Date(r.date).toLocaleString("fr-FR")}`,
  ].filter(Boolean).join("\n");
}

async function tester(body) {
  body.innerHTML = `<p class="lead">Gabriel AXA est en <b>phase de test</b>. Ton retour construit la prochaine version.
    Utilise-le comme dans ta pratique réelle, puis dis-nous ce qui marche et ce qui manque.</p>
    <h3 class="day-h">Ce qu'on attend de toi</h3>
    <ul class="hlist">
      <li><b>Signale les erreurs</b> : une réponse fausse, une source qui ne correspond pas.</li>
      <li><b>Propose des recherches réelles</b> : les questions que tu poses vraiment en rendez-vous.</li>
      <li><b>Compare avec ta pratique</b> : est-ce plus rapide, plus fiable ?</li>
      <li><b>Dis-nous ce qui manque</b> : un contrat, une garantie, une catégorie.</li>
      <li><b>Note les cas</b> où une IA se trompe ou n'aboutit pas.</li>
    </ul>
    <div class="warnbox">${INDEP_COMPLET}</div>
    <h3 class="day-h">Par où commencer</h3>
    <div class="grid">
      ${tile("🔎", "Une vraie recherche", "#/recherche", "teste une question de RDV")}
      ${tile("🤖", "Avec ton IA", "#/assistants", "colle l'adresse et interroge")}
    </div>
    <h3 class="day-h">Noter un retour</h3>
    <p class="muted">Reste ici, dans ton navigateur — rien n'est envoyé automatiquement. Tu copies et tu colles toi-même dans le groupe Matrix quand tu veux.</p>
    <form id="fb_form" class="card">
      <label>Recherche testée<input id="fb_recherche" class="filter" placeholder="ex. délai de carence Avizen"></label>
      <label>Contrat concerné<input id="fb_contrat" class="filter" placeholder="optionnel"></label>
      <label>As-tu trouvé l'information ?
        <select id="fb_trouve" class="filter"><option>oui</option><option>partiellement</option><option>non</option></select></label>
      <label>Utilité perçue vs ta pratique habituelle ?
        <select id="fb_utilite" class="filter"><option>plus rapide/fiable</option><option>pareil</option><option>moins pratique</option></select></label>
      <label>As-tu utilisé une IA (ChatGPT/Claude/Gemini…) ?
        <select id="fb_ia" class="filter"><option>non</option><option>oui, réponse correcte</option><option>oui, réponse fausse ou incomplète</option></select></label>
      <label>Ce qui était incompréhensible, manquant, ou une erreur constatée
        <textarea id="fb_commentaire" rows="3" style="width:100%;resize:vertical" placeholder="libre"></textarea></label>
      <button type="submit" class="btn gold" style="margin-top:8px">Enregistrer ce retour</button>
    </form>
    <div id="fb_list"></div>`;

  const listEl = body.querySelector("#fb_list");
  function renderListe() {
    const retours = lireRetours();
    listEl.innerHTML = !retours.length ? "" : `
      <h3 class="day-h">Tes retours enregistrés (${retours.length}, sur cet appareil)</h3>
      <div class="btns"><button class="btn ghost" id="fb_copy">📋 Copier tous mes retours</button>
        <button class="btn ghost" id="fb_clear">Vider</button></div>
      <ul class="hlist">${retours.map(r => `<li><span class="muted">${esc(new Date(r.date).toLocaleString("fr-FR"))}</span> — ${esc(r.recherche || "(sans intitulé)")} · ${esc(r.trouve)}</li>`).join("")}</ul>`;
    bindCopy(listEl.querySelector("#fb_copy"), () => retours.map(retourTexte).join("\n\n---\n\n"), "✓ Retours copiés — colle-les dans le groupe Matrix");
    listEl.querySelector("#fb_clear")?.addEventListener("click", () => { if (confirm("Vider tes retours enregistrés sur cet appareil ?")) { ecrireRetours([]); renderListe(); } });
  }
  renderListe();

  body.querySelector("#fb_form").addEventListener("submit", e => {
    e.preventDefault();
    const q = id => body.querySelector(id).value.trim();
    const retours = lireRetours();
    retours.unshift({
      date: new Date().toISOString(), recherche: q("#fb_recherche"), contrat: q("#fb_contrat"),
      trouve: q("#fb_trouve"), utilite: q("#fb_utilite"), ia: q("#fb_ia"), commentaire: q("#fb_commentaire"),
    });
    ecrireRetours(retours);
    body.querySelector("#fb_form").reset();
    renderListe();
  });
}

/* ---------- Fiche contrat (espace de travail conseiller — Chantier 3) ----------
   Hiérarchie progressive : ① l'essentiel → ② mécanisme → ③ appliquer/comparer →
   ⑤ preuves sourcées → ⑥ aller plus loin. Les analyses viennent de la couche DÉRIVÉE
   /ia/inspecteur (générée du graphe de connaissances) et sont TOUJOURS étiquetées
   « analyse IA · à valider » — jamais présentées comme une preuve. Fail-open : sans
   ces fichiers, la fiche reste complète avec les seuls faits sourcés (Pack A). */
const INSP_BASE = "../ia/inspecteur/";
const _inspCache = new Map();
async function inspJson(rel) {
  if (_inspCache.has(rel)) return _inspCache.get(rel);
  let v = null;
  try { const r = await fetch(INSP_BASE + rel, { cache: "no-cache" }); if (r.ok) v = await r.json(); } catch {}
  _inspCache.set(rel, v); return v;
}
// Clé de rapprochement tolérante aux variantes d'écriture (parenthèses/accents ignorés).
const cleNom = n => String(n || "").replace(/\(.*?\)/g, "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]/g, "");
async function inspFiche(nom) {
  const idx = await inspJson("contrats/index.json");
  const e = (idx?.contrats || []).find(x => x.contrat === nom) || (idx?.contrats || []).find(x => cleNom(x.contrat) === cleNom(nom));
  return e ? await inspJson(e.fichier) : null;
}
// Types de documents (jargon d'archivage) → libellés lisibles par un conseiller.
const TYPE_LABELS = {
  conditions_generales: "Conditions générales",
  notice_information_contrat_groupe_adhesion_facultative: "Contrat de groupe à adhésion facultative",
  notice_information_convention_groupe_adhesion_facultative: "Convention de groupe à adhésion facultative",
  notice_information_contrat_groupe_assurance_vie_entiere: "Assurance vie entière (contrat de groupe)",
  notice_information_contrat_groupe_assurance_vie_multisupport: "Assurance vie multisupport (contrat de groupe)",
  notice_information_contrat_groupe_PER_individuel: "PER individuel (contrat de groupe)",
};
const typeHumain = t => TYPE_LABELS[t] || String(t || "").replace(/^notice_information_/, "").replace(/_/g, " ");
// Étiquette d'honnêteté : toute interprétation issue du raisonnement IA la porte.
const IA_TAG = `<span class="pill pending" title="Analyse produite par une IA à partir des données structurées du contrat — à faire valider, jamais une preuve client">analyse IA · à valider</span>`;
const iaTxt = o => (o && typeof o === "object" && o.texte) ? String(o.texte) : "";
const court = n => String(n || "").replace(/\s*\(.*?\)\s*/g, " ").trim();

async function contrat(body, human, ctx) {
  const resume = await kb.source("contrats_resume_humain");
  const contrats = resume?.contrats || [];
  if (!contrats.length) { body.innerHTML = `<p class="warn">Résumé humain des contrats indisponible (voir manifeste).</p>`; return; }
  if (!human) { body.innerHTML = `<pre>${esc(JSON.stringify(resume, null, 2).slice(0, 200000))}</pre>`; return; }
  const familles = [...new Set(contrats.map(c => c.famille).filter(Boolean))].sort();
  let fam = "all", selected = null; // selected = nom du contrat ouvert (null = sélecteur)
  // Lien profond #/contrat/<slug> : la recherche et le copilote ouvrent DIRECTEMENT la bonne fiche.
  const slugc = s => String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]/g, "");
  const want = ctx?.path?.[0] ? slugc(decodeURIComponent(ctx.path[0])) : null;
  if (want) selected = (contrats.find(c => slugc(c.nom) === want) || contrats.find(c => slugc(c.nom).startsWith(want)))?.nom || null;
  // Carte filename → URL de notice (quick win 3 : lien fait → notice à la bonne page).
  const pdfIdx = await kb.source("pdf_index");
  const pdfByName = new Map();
  for (const p of (pdfIdx?.pdfs || [])) { const base = String(p.path || "").split("/").pop(); if (base) pdfByName.set(base, kb.pdfUrl(p.path)); }
  // Index dérivé (évolution ①) : définitions, conditions de souscription, déclencheurs/plafonds/
  // franchises — surface la couche déjà structurée de Pack A. Repli propre si absent.
  const fiches = await kb.source("fiches_conseiller");
  const slug = s => String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]/g, "");
  const derivedByKey = new Map();
  for (const d of (fiches?.contrats || [])) {
    derivedByKey.set(slug(d.id), d);
    derivedByKey.set(slug(d.nom), d);
    for (const a of (d.aliases || [])) derivedByKey.set(slug(a), d);
  }
  const findDerived = c => {
    const k = slug(c.nom);
    if (derivedByKey.has(k)) return derivedByKey.get(k);
    for (const [dk, d] of derivedByKey) if (dk && (k.startsWith(dk) || dk.startsWith(k))) return d;
    return null;
  };
  // P1 : contrats présents dans le dérivé mais absents de la vue humaine (ex. EssenCiel Patrimoine)
  // → ajoutés en fiche MINIMALE, honnête (données limitées), avec notice PDF. Rien inventé.
  const known = new Set(contrats.map(c => slug(c.nom)));
  for (const d of (fiches?.contrats || [])) {
    if (known.has(slug(d.nom)) || [...known].some(k => k.startsWith(slug(d.id)) || slug(d.id).startsWith(k))) continue;
    const pdfs = (pdfIdx?.pdfs || []).filter(p => slug(p.nom_contrat) === slug(d.nom));
    contrats.push({ nom: d.nom, famille: (d.domaines || [])[0] || "", resume_neutre: "", pdfs, _minimal: true });
  }
  contrats.sort((a, b) => String(a.nom).localeCompare(String(b.nom), "fr", { sensitivity: "base" })); // tri alphabétique (quick win)
  const noticeHref = (docSource, page) => {
    const base = String(docSource).split("/").pop();
    const first = page ? String(page).split(",")[0].trim() : "";
    return (pdfByName.get(base) || ("../data/AXA/00_PACKAGE_ACTIF/Contrats-AXA/" + docSource)) + (first ? "#page=" + first : "");
  };
  // Source PDF = badge clair et actionnable (jamais masquée) : « 📄 Notice p.X ».
  const sourceLink = f => {
    const s = f && typeof f === "object" ? f.source : null;
    if (!s || !s.document_source) return "";
    const titre = "Ouvrir la notice" + (s.page ? " page " + s.page : "") + (s.section ? " — " + s.section : "");
    return `<a class="fsrc" href="${esc(noticeHref(s.document_source, s.page))}" target="_blank" rel="noopener" title="${esc(titre)}">📄 Notice${s.page ? " p." + esc(String(s.page)) : ""}</a>`;
  };
  // Un fait = une carte lisible (titre · texte · conditions/limites · source), plutôt qu'une puce dense.
  const fitem = f => {
    if (typeof f === "string") return isEmpty(f) ? "" : `<div class="fitem"><p class="fitem-b">${esc(f)}</p></div>`;
    const t = f.titre && !f.titre.startsWith("_") ? f.titre : "", x = f.resume_humain || f.texte || "";
    if (isEmpty(t) && isEmpty(x)) return "";
    const cond = (f.conditions_importantes || []).filter(Boolean), lim = (f.limites_exclusions || []).filter(Boolean);
    return `<div class="fitem">${t ? `<div class="fitem-t">${esc(t)}</div>` : ""}${x ? `<p class="fitem-b">${esc(x)}</p>` : ""}`
      + `${cond.length ? `<p class="fitem-x"><span class="fitem-xl">Conditions</span> ${esc(cond.join(" · "))}</p>` : ""}`
      + `${lim.length ? `<p class="fitem-x"><span class="fitem-xl">Limites</span> ${esc(lim.join(" · "))}</p>` : ""}`
      + `${sourceLink(f)}</div>`;
  };
  // Rubrique repliable, avec poids visuel selon la priorité (prio), une teinte de type (tone)
  // et `why` = pourquoi ce bloc compte pour le conseiller (affiché en tête du bloc).
  const fsec = (label, items, { open = false, prio = false, tone = "", why = "", id = "" } = {}) => {
    const rendered = (items || []).map(fitem).filter(Boolean);
    if (!rendered.length) return "";
    return `<details class="fsec ${prio ? "prio" : ""} ${tone}"${open ? " open" : ""}${id ? ` id="${id}"` : ""}><summary class="fsec-h"><span class="fsec-l">${esc(label)}</span><span class="fsec-n">${rendered.length}</span></summary><div class="fsec-body">${why ? `<p class="fsec-why">${esc(why)}</p>` : ""}${rendered.join("")}</div></details>`;
  };
  const pdfsFor = c => (c.pdfs || []).map(p => typeof p === "string" ? p : (p.nom_fichier || p.fichier || "")).filter(Boolean);
  const meta = c => FAMILLE_META[c.famille] || null;
  const confusablesFor = c => contrats.filter(x => x.famille === c.famille && x.nom !== c.nom).map(x => x.nom);
  const bullets = arr => `<ul class="hlist">${arr.map(x => `<li>${esc(x)}</li>`).join("")}</ul>`;

  // Matrice de risques métier (heuristique étiquetée) : besoins couverts + questions par contrat.
  const matrice = await inspJson("metier/matrice_risques.json");
  const risquesPour = nom => Object.values(matrice?.risques || {}).filter(r => (r.contrats || []).some(x => cleNom(x) === cleNom(nom)));
  const besoinsPour = nom => risquesPour(nom).map(r => String(r.libelle || "").split("—")[0].trim()).filter(Boolean);
  const iaSlug = n => String(n || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const titres3 = (arr, n = 3) => (arr || [])
    .map(f => typeof f === "string" ? f : (f.titre && !f.titre.startsWith("_") ? f.titre : (f.resume_humain || "")))
    .filter(x => x && !isEmpty(x)).slice(0, n);
  const essB = (label, html, { ia = false, cls = "" } = {}) => html ? `<div class="ess-b ${cls}"><div class="ess-h">${esc(label)}${ia ? " " + IA_TAG : ""}</div>${html}</div>` : "";

  // Résumé copiable de la fiche (texte prudent, sourcé, analyses IA marquées).
  const resumeTexte = (c, insp) => {
    const m = meta(c);
    const L = [`FICHE CONTRAT — ${c.nom} (${c.famille || "?"}) · notice ${c.date_document || "?"}`, ""];
    const fin = iaTxt(insp?.finalite);
    if (fin) L.push("CE QUE C'EST (analyse IA, à valider) : " + fin);
    else if (c.resume_neutre) L.push("RÉSUMÉ : " + c.resume_neutre);
    if (m?.cible) L.push("À QUI : " + m.cible);
    const bes = besoinsPour(c.nom);
    if (bes.length) L.push("BESOINS COUVERTS (heuristique IA) : " + bes.join(" · "));
    const fav = iaTxt(insp?.situations_favorables); if (fav) L.push("PERTINENT QUAND (IA, à valider) : " + fav);
    const dfav = iaTxt(insp?.situations_defavorables); if (dfav) L.push("MOINS ADAPTÉ SI (IA, à valider) : " + dfav);
    const src = f => (f && typeof f === "object" && f.source?.page) ? ` (notice p.${String(f.source.page)})` : "";
    const sec = (t, arr) => {
      const xs = (arr || []).filter(f => typeof f === "string" ? f : (f.titre && !f.titre.startsWith("_")));
      if (xs.length) { L.push("", t + " :"); xs.slice(0, 8).forEach(f => L.push("- " + (typeof f === "string" ? f : f.titre) + src(f))); }
    };
    sec("GARANTIES (sourcées)", c.garanties_principales);
    sec("EXCLUSIONS (sourcées)", c.exclusions_importantes);
    sec("POINTS DE VIGILANCE", c.points_de_vigilance);
    L.push("", "RÈGLE : la notice PDF fait foi — aucune réponse client sans vérification. Les analyses IA sont à valider.");
    return L.join("\n");
  };

  const fiche = (c, insp) => {
    const d = findDerived(c);
    const m = meta(c), conf = confusablesFor(c), pdfs = pdfsFor(c);
    const mainNotice = (c.pdfs || []).map(p => pdfByName.get(String(p.nom_fichier || p.fichier || p).split("/").pop())).find(Boolean);
    const vCounts = insp?.validation?.counts;

    // ① L'ESSENTIEL — répondre d'abord aux questions que se pose le conseiller.
    const finalite = iaTxt(insp?.finalite);
    const r = c.resume_neutre || "";
    const quoi = finalite
      ? `<p class="ess-p">${esc(finalite)}</p>${r ? `<details class="fold"><summary class="muted" style="font-size:12.5px;cursor:pointer">résumé documentaire complet (sourcé)</summary><p class="ess-p muted" style="margin-top:6px">${esc(r)}</p></details>` : ""}`
      : (r ? `<p class="ess-p">${esc(r.length > 420 ? r.slice(0, 420) + "…" : r)}</p>` : "");
    const besoins = besoinsPour(c.nom);
    const favorables = iaTxt(insp?.situations_favorables), defavorables = iaTxt(insp?.situations_defavorables);
    const limites = titres3(c.exclusions_importantes);
    const vig = titres3(c.points_de_vigilance);
    const pieges = vig.length ? vig : (m?.erreurs || []).slice(0, 3);
    const questions = [...new Set([...risquesPour(c.nom).flatMap(rq => rq.questions || []), ...(m?.questions || [])])].slice(0, 4);
    const essentiel = `<section class="ess"><div class="fiche-niv"><span class="niv-n">1</span>L'essentiel <span class="niv-s">ce qu'il faut savoir avant d'en parler</span></div>
      <div class="ess-grid">
        ${essB("Ce que c'est", quoi, { ia: !!finalite, cls: "ess-wide" })}
        ${essB("À qui il s'adresse", m?.cible ? `<p class="ess-p">${esc(m.cible)}</p>` : "")}
        ${essB("Besoins couverts", besoins.length ? `<div class="fiche-chips">${besoins.map(bq => `<span class="fchip">${esc(bq)}</span>`).join("")}</div>` : "", { ia: true })}
        ${essB("✓ Pertinent quand", favorables ? `<p class="ess-p">${esc(favorables)}</p>` : "", { ia: true, cls: "t-okb" })}
        ${essB("⚠ Moins adapté si", defavorables ? `<p class="ess-p">${esc(defavorables)}</p>` : "", { ia: true, cls: "t-warnb" })}
        ${essB("Limites principales", limites.length ? bullets(limites) + `<p class="ess-more"><a href="#" data-goto="sec_exclusions">→ toutes les exclusions, sourcées</a></p>` : "")}
        ${essB("Pièges à éviter", pieges.length ? bullets(pieges) : "")}
        ${essB("Questions à poser au client", questions.length ? bullets(questions) : "")}
      </div>
      <p class="ess-statut">📄 Notice ${esc(c.date_document || "—")}${vCounts ? ` · <b>${vCounts.validated ?? 0}</b> faits validés (sourcés notice) · ${vCounts.derived_deterministic ?? 0} relations dérivées · ${vCounts.simulated_claude ?? 0} analyses IA à valider` : ""} — <b>la notice PDF fait foi</b>.</p></section>`;

    // ② COMPRENDRE LE MÉCANISME
    const logique = iaTxt(insp?.logique_contractuelle);
    const arch = insp?.architecture_garanties;
    const mecanisme = (logique || arch?.principales?.length) ? `<div class="fiche-niv"><span class="niv-n">2</span>Comprendre le mécanisme</div>
      <details class="fsec t-accent"><summary class="fsec-h"><span class="fsec-l">Comment ce contrat fonctionne</span><span class="fsec-tag">analyse IA · à valider</span></summary><div class="fsec-body">
        ${logique ? `<div class="fitem"><div class="fitem-t">Logique contractuelle</div><p class="fitem-b">${esc(logique)}</p></div>` : ""}
        ${arch?.principales?.length ? `<div class="fitem"><div class="fitem-t">Architecture des garanties</div>${bullets(arch.principales)}${arch.secondaires?.length ? `<p class="fitem-x"><span class="fitem-xl">Optionnelles</span> ${esc(arch.secondaires.join(" · "))}</p>` : ""}</div>` : ""}
      </div></details>` : "";

    // ③ APPLIQUER À UN CAS · ④ COMPARER — les actions de travail, côte à côte.
    const confusion = iaTxt(insp?.confusions_frequentes);
    const slugMoi = slugc(c.nom);
    const travailler = `<div class="fiche-niv"><span class="niv-n">3</span>Travailler avec ce contrat</div>
      <div class="fiche-work">
        <div class="ess-b"><div class="ess-h">Appliquer à un cas</div>
          <div class="btns">
            <button class="btn" data-act="copilote">🧠 Poser une question sur ${esc(court(c.nom))}</button>
            <a class="btn ghost" href="#/besoins">🎯 Analyser un cas client</a>
            <button class="btn ghost" data-act="rdv">🗓 Préparer un rendez-vous</button>
            <button class="btn ghost" data-act="arg">🗣 Créer un argumentaire</button>
          </div></div>
        <div class="ess-b"><div class="ess-h">À ne pas confondre${confusion ? " " + IA_TAG : ""}</div>
          ${confusion ? `<p class="ess-p" style="margin-bottom:8px">${esc(confusion)}</p>` : `<p class="ess-p muted">Aucune confusion fréquente signalée.</p>`}
          <div class="btns">${conf.slice(0, 3).map(p => `<a class="btn ghost" href="#/contrat/${slugc(p)}">📑 ${esc(court(p))}</a>`).join("")}</div></div>
      </div>`;

    // ⑤ VÉRIFIER LES PREUVES — faits sourcés, chaque bloc dit pourquoi il compte.
    const enriched = (d?.faits || []).filter(f => f.declencheurs.length || f.plafonds.length || f.franchises.length);
    const preuves = [
      `<div class="fiche-niv"><span class="niv-n">4</span>Vérifier les preuves <span class="niv-s">faits sourcés — chaque ligne renvoie à la notice</span></div>`,
      fsec("Garanties principales", c.garanties_principales, { open: true, prio: true, tone: "t-ok", why: "Ce que le contrat paie : la promesse de base." }),
      fsec("Exclusions importantes", c.exclusions_importantes, { open: true, prio: true, tone: "t-crit", id: "sec_exclusions", why: "Ce qu'il ne paiera pas : première source de litige avec un client." }),
      d?.conditions_souscription?.length ? `<details class="fsec prio t-accent"><summary class="fsec-h"><span class="fsec-l">Conditions de souscription</span><span class="fsec-n">${d.conditions_souscription.length}</span></summary><div class="fsec-body"><p class="fsec-why">Qui peut souscrire, à quel âge, avec quelles formalités.</p>${d.conditions_souscription.map(x => `<div class="fitem"><p class="fitem-b">${esc(x.texte)}</p>${sourceLink(x)}</div>`).join("")}</div></details>` : "",
      fsec("Points de vigilance", c.points_de_vigilance, { prio: true, tone: "t-warn", why: "Les pièges relevés dans la notice : à connaître avant de s'engager." }),
      fsec("Délais & franchises", c.delais_franchises, { tone: "t-neutral", why: "Quand la garantie commence vraiment à payer." }),
      enriched.length ? `<details class="fsec t-neutral"><summary class="fsec-h"><span class="fsec-l">Déclencheurs, plafonds &amp; franchises</span><span class="fsec-n">${enriched.length}</span></summary><div class="fsec-body"><p class="fsec-why">Ce qui déclenche la garantie, et jusqu'où elle paie.</p>${enriched.map(f => `<div class="fitem"><div class="fitem-t">${esc(f.titre)}</div>${f.declencheurs.length ? `<p class="fitem-x"><span class="fitem-xl">Déclencheurs</span> ${esc(f.declencheurs.join(" · "))}</p>` : ""}${f.plafonds.length ? `<p class="fitem-x"><span class="fitem-xl">Plafonds</span> ${esc(f.plafonds.join(" · "))}</p>` : ""}${f.franchises.length ? `<p class="fitem-x"><span class="fitem-xl">Franchises</span> ${esc(f.franchises.join(" · "))}</p>` : ""}${sourceLink(f)}</div>`).join("")}</div></details>` : "",
      fsec("Cotisations & prix", c.cotisations_prix, { tone: "t-neutral", why: "Ce que ça coûte, et comment ça évolue." }),
      fsec("Fiscalité", c.fiscalite, { tone: "t-neutral", why: "Le traitement fiscal évolue : vérifier la source officielle avant tout chiffre." }),
      d?.definitions?.length ? `<details class="fsec t-neutral"><summary class="fsec-h"><span class="fsec-l">Définitions</span><span class="fsec-n">${d.definitions.length}</span></summary><div class="fsec-body"><p class="fsec-why">Les mots ont un sens contractuel précis — c'est souvent là que tout se joue.</p>${d.definitions.map(x => `<div class="fitem"><div class="fitem-t">${esc(x.terme)}</div><p class="fitem-b">${esc(x.definition)}</p>${sourceLink(x)}</div>`).join("")}</div></details>` : "",
      fsec("Options", c.options, { tone: "t-neutral", why: "Les extensions possibles de la couverture." }),
      fsec("Formules", c.formules, { tone: "t-neutral", why: "Les niveaux de couverture proposés." }),
    ].filter(Boolean).join("");

    // ⑥ ALLER PLUS LOIN
    const plusLoin = [
      `<div class="fiche-niv"><span class="niv-n">5</span>Aller plus loin</div>`,
      m ? `<details class="fsec t-neutral"><summary class="fsec-h"><span class="fsec-l">Repères conseiller</span><span class="fsec-tag">méthodo · non contractuel</span></summary><div class="fsec-body">
        <div class="fitem"><div class="fitem-t">Cas d'usage</div>${bullets(m.cas_usage)}</div>
        <div class="fitem"><div class="fitem-t">Erreurs fréquentes</div>${bullets([...m.erreurs, ...ERREURS_TRANSVERSES])}</div></div></details>` : "",
      pdfs.length ? `<details class="fsec t-neutral"><summary class="fsec-h"><span class="fsec-l">Documents PDF liés</span><span class="fsec-n">${pdfs.length}</span></summary><div class="fsec-body"><div class="fitem">${bullets(pdfs)}<p class="muted" style="margin-top:6px"><a href="#/pdf">→ ouvrir les notices contractuelles</a></p></div></div></details>` : "",
      `<details class="fsec t-neutral"><summary class="fsec-h"><span class="fsec-l">Donner cette fiche à une IA</span></summary><div class="fsec-body"><div class="fitem"><p class="fitem-b">La même connaissance, projetée pour un assistant : <a href="${IA_URL}contrat/${iaSlug(c.nom)}.html" target="_blank" rel="noopener">↗ fiche Vue IA</a> · <a href="#/assistants">🤖 utiliser avec une IA</a></p></div></div></details>`,
    ].filter(Boolean).join("");

    return `<article class="card fiche">
      <header class="fiche-head">
        <div class="fiche-id">
          <h2 class="fiche-name">${esc(c.nom)}</h2>
          ${c.type_contrat ? `<div class="fiche-type">${esc(typeHumain(c.type_contrat))}</div>` : ""}
          <div class="fiche-badges">${c.famille ? `<span class="fbadge fam">${esc(c.famille)}</span>` : ""}${c.date_document ? `<span class="fbadge" title="Date de la notice de référence">notice ${esc(c.date_document)}</span>` : ""}</div>
        </div>
        <div class="fiche-actions">${mainNotice ? `<a class="btn gold" href="${esc(mainNotice)}" target="_blank" rel="noopener">📄 Notice</a>` : ""}<button class="btn ghost" data-act="copy">📋 Copier le résumé</button><button class="btn ghost" data-print>Imprimer</button></div>
      </header>
      ${c.assureur ? `<div class="fiche-assureur"><span class="fiche-assureur-l">Assureur</span> ${esc(c.assureur)}</div>` : ""}
      ${c._minimal ? `<div class="warnbox">Données limitées pour ce contrat — se référer à la notice PDF. Fiche minimale.</div>` : ""}
      ${essentiel}
      ${mecanisme}
      ${travailler}
      ${preuves}
      ${plusLoin}
      <p class="fiche-foot">Repères indicatifs — pour le cas précis, la notice PDF fait foi. Aucune réponse client sans vérifier la source. Les blocs « analyse IA » sont des aides à valider, jamais une preuve.</p>
    </article>`;
  };
  async function render(q = "") {
    const ql = q.trim().toLowerCase();
    let list = contrats;
    if (fam !== "all") list = list.filter(c => c.famille === fam);
    if (ql) list = list.filter(c => JSON.stringify(c).toLowerCase().includes(ql));
    // Tuile du sélecteur : nom + famille + besoins couverts (le conseiller choisit par usage).
    const tileCard = c => { const bes = besoinsPour(c.nom).slice(0, 2).join(" · ");
      return `<a class="tile contract-pick" data-open="${esc(c.nom)}"><span class="tile-l">${esc(c.nom)}</span><span class="tile-s">${esc([c.famille, "notice " + (c.date_document || "?")].filter(Boolean).join(" · "))}</span>${bes ? `<span class="tile-s">${esc(bes)}</span>` : ""}<span class="tile-s go">ouvrir la fiche →</span></a>`; };
    let content;
    if (selected) {
      const c = contrats.find(x => x.nom === selected);
      const insp = c ? await inspFiche(c.nom) : null;
      // Retour au contexte : la recherche/question/comparaison qui a mené ici reste à un clic.
      const back = get("axaBack");
      const backLbl = { recherche: "ta recherche", copilote: "ta question" }[back?.from];
      const backLink = back?.q && backLbl ? ` · <a href="#" id="axa_ctx">↩ revenir à ${backLbl} « ${esc(back.q.length > 42 ? back.q.slice(0, 42) + "…" : back.q)} »</a>` : "";
      content = `<p class="crumb"><a href="#" id="axa_back">← Tous les contrats</a>${backLink}</p>` + (c ? fiche(c, insp) : "<p class='muted'>Contrat introuvable.</p>");
    } else {
      content = `<p class="muted">Ouvre la fiche d'un contrat : c'est ton espace de travail — l'essentiel, le mécanisme, le cas client, la comparaison et les preuves sourcées.</p>
        <div class="grid">${list.map(tileCard).join("") || "<p class='muted'>Aucun contrat ne correspond à ce filtre.</p>"}</div>`;
    }
    body.innerHTML = `<div class="view-head" style="margin-top:0"><input class="filter" id="axaq" placeholder="🔎 filtrer les contrats…" aria-label="Filtrer les contrats" value="${esc(q)}"></div>
      <div class="filters">${["all", ...familles].map(f => `<button class="chip ${fam === f ? "on" : ""}" data-f="${esc(f)}">${f === "all" ? "toutes" : esc(f)}</button>`).join("")}</div>
      ${content}`;
    body.querySelectorAll("[data-f]").forEach(b => b.onclick = () => { fam = b.dataset.f; selected = null; render(body.querySelector("#axaq").value); });
    body.querySelectorAll("[data-open]").forEach(a => a.onclick = e => { e.preventDefault(); selected = a.dataset.open; render(""); window.scrollTo(0, 0); });
    body.querySelector("#axa_back")?.addEventListener("click", e => { e.preventDefault(); selected = null; render(""); });
    body.querySelector("#axa_ctx")?.addEventListener("click", e => {
      e.preventDefault(); const back = get("axaBack");
      if (!back?.q) return;
      set({ axaQuery: back.q }); location.hash = "#/" + (back.from === "copilote" ? "copilote" : "recherche");
    });
    body.querySelectorAll("[data-print]").forEach(b => b.onclick = () => printTarget(b.closest(".card")));
    if (selected) {
      const c = contrats.find(x => x.nom === selected);
      if (c) {
        const insp = await inspFiche(c.nom); // instantané : déjà en cache
        bindCopy(body.querySelector("[data-act=copy]"), () => resumeTexte(c, insp), "✓ Résumé copié");
        body.querySelector("[data-act=copilote]")?.addEventListener("click", () => { set({ axaQuery: c.nom + " " }); location.hash = "#/copilote"; });
        body.querySelector("[data-act=rdv]")?.addEventListener("click", () => { set({ axaRdvPrefill: c.nom }); location.hash = "#/rdv"; });
        body.querySelector("[data-act=arg]")?.addEventListener("click", () => { set({ axaArgPrefill: c.nom }); location.hash = "#/argumentaire"; });
        body.querySelectorAll("[data-goto]").forEach(a => a.onclick = e => {
          e.preventDefault(); const s = body.querySelector("#" + a.dataset.goto);
          if (s) { s.open = true; s.scrollIntoView({ behavior: "smooth", block: "start" }); }
        });
      }
    }
    const inp = body.querySelector("#axaq");
    let t; inp.addEventListener("input", e => { clearTimeout(t); t = setTimeout(async () => { const v = e.target.value; selected = null; await render(v); const i2 = body.querySelector("#axaq"); i2.focus(); i2.setSelectionRange(v.length, v.length); }, 250); });
  }
  await render();
}

/* ---------- Recherche globale ---------- */
async function recherche(body) {
  // Filtres par type de résultat (buckets lisibles ; prédicat sur le type ou le texte).
  const FILTERS = [
    { id: "all", label: "Tous" },
    { id: "definition", label: "Définitions", pred: t => t === "définition" },
    { id: "garantie", label: "Garanties", pred: t => /garantie/.test(t) },
    { id: "exclusion", label: "Exclusions", pred: t => /exclusion/.test(t) },
    { id: "condition", label: "Conditions", pred: t => t === "condition de souscription" },
    { id: "pfd", label: "Plafonds/franchises/déclencheurs", text: /(plafond|limite|franchise|carence|d[ée]lai|d[ée]clencheur)/i },
    { id: "contrat", label: "Contrats", pred: t => t === "contrat" || t === "contrat (JSON enrichi)" },
  ];
  const matchFilter = (f, h) => f.id === "all" ? true : (f.pred ? f.pred(h.type) : f.text.test((h.label || "") + " " + (h.text || "")));
  let active = "all", lastHits = [];

  body.innerHTML = `<div class="view-head" style="margin-top:0"><input class="filter" id="gq" placeholder="Rechercher (mots-clés tolérés, synonymes)…" aria-label="Recherche globale AXA" autofocus></div>
    <div class="filters" id="gfilters"></div>
    <div id="gres"><p class="muted">Tape au moins 2 caractères. Recherche tokenisée + synonymes métier — les résultats sont triés par pertinence. Sources sourcées (PDF/page).</p></div>`;
  const res = body.querySelector("#gres");
  const input = body.querySelector("#gq");
  const filtersEl = body.querySelector("#gfilters");

  function highlight(text, terms) {
    let out = esc(String(text).slice(0, 280));
    for (const t of terms) { if (t.length < 2) continue; out = out.replace(new RegExp("(" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi"), "<mark>$1</mark>"); }
    return out;
  }
  const rnorm = s => String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  // Le texte des faits commence souvent par son propre titre : on ne l'affiche qu'une fois.
  const sansTitre = (text, label) => {
    let t = String(text || "").trim(); const L = String(label || "").trim();
    for (let i = 0; i < 2 && L && rnorm(t).startsWith(rnorm(L)); i++) t = t.slice(L.length).replace(/^\s*[—:.\-]\s*/, "");
    return t.trim() || L;
  };
  function paint() {
    const shown = lastHits.filter(h => matchFilter(FILTERS.find(f => f.id === active), h));
    filtersEl.innerHTML = FILTERS.map(f => {
      const n = f.id === "all" ? lastHits.length : lastHits.filter(h => matchFilter(f, h)).length;
      return n || f.id === "all" ? `<button class="chip ${active === f.id ? "on" : ""}" data-fid="${f.id}">${esc(f.label)}${f.id === "all" ? "" : ` (${n})`}</button>` : "";
    }).join("");
    filtersEl.querySelectorAll("[data-fid]").forEach(b => b.onclick = () => { active = b.dataset.fid; paint(); });
    const terms = (rnorm(input.value.trim()).match(/[a-z0-9]{2,}/g)) || [];
    // Badge de tête HONNÊTE (V-Matrix) : si le meilleur résultat ne recoupe que faiblement les
    // termes saisis (couverture pondérée < 50 %, synonymes inclus — service axaKnowledge), on ne le
    // présente PAS comme « meilleur résultat » : badge « correspondance faible » + explication.
    // Un résultat faible reste affiché (il peut servir) mais n'est jamais présenté comme fiable.
    const carte = (h, tete) => `
      <article class="card ${tete ? "cop-base" : ""}"><div class="card-h">${tete ? (h.faible
          ? `<span class="pill pending">correspondance faible</span>`
          : `<span class="pill integrated">meilleur résultat</span>`) : ""}
        <span class="pill">${esc(h.type)}</span><strong>${esc(h.label || "(sans titre)")}</strong><span class="muted">${esc(h.contrat || "")}</span></div>
      <p class="card-b">${highlight(sansTitre(h.text, h.label), terms)}</p>
      <p class="muted">${tete ? (h.faible
          ? `<span class="muted">ne recoupe qu'une partie de tes termes — cette question est peut-être <b>hors du périmètre des 9 contrats</b> de la base. À vérifier, ne t'appuie pas dessus tel quel · </span>`
          : `<span class="muted">celui qui recoupe le mieux tes termes — vérifie la notice (fait foi) · </span>`) : ""}<a href="${h.ref}">→ ouvrir la fiche</a></p></article>`;
    // État vide HUMAIN : distinguer « rien pour ce filtre » de « rien du tout », expliquer
    // ce que ça signifie et proposer la suite — jamais un cul-de-sac.
    const etatVide = () => {
      const q = input.value.trim();
      if (lastHits.length) return `<p class='muted'>Aucun résultat de ce type — ${lastHits.length} au total dans les autres filtres ci-dessus.</p>`;
      return `<div class="card"><div class="card-h"><span class="pill pending">aucun fait trouvé</span><strong>« ${esc(q)} »</strong></div>
        <p class="card-b">Soit le mot n'est pas celui de la notice, soit l'information n'est <b>pas dans la base</b> — elle n'y est jamais inventée. <b>Ne réponds pas au client sans vérifier.</b></p>
        <ul class="hlist">
          <li>Reformule avec le mot de la notice (« rachat » plutôt que « récupérer l'argent »).</li>
          <li>Précise le contrat (« carence Avizen »).</li>
          <li>Matière réglementaire (impôt, retraite légale, succession) → <a href="#/sources">sources officielles</a>.</li>
          <li>En dernier recours : <a href="#/pdf">ouvrir la notice</a> — elle fait foi.</li>
        </ul>
        <div class="btns"><button class="btn ghost" id="gr_cop">🧠 Poser la question au copilote</button></div></div>`;
    };
    res.innerHTML = shown.length ? `<p class="muted">${shown.length} résultat(s)${active !== "all" ? " · filtre : " + esc(FILTERS.find(f => f.id === active).label) : ""}</p>`
      + shown.map((h, i) => carte(h, i === 0)).join("")
      : etatVide();
    res.querySelector("#gr_cop")?.addEventListener("click", () => { set({ axaQuery: input.value.trim() }); location.hash = "#/copilote"; });
  }
  let t;
  async function run(q) {
    q = (q || "").trim();
    if (q.length < 2) { lastHits = []; filtersEl.innerHTML = ""; res.innerHTML = "<p class='muted'>Tape au moins 2 caractères.</p>"; return; }
    res.innerHTML = "<p class='muted'>Recherche…</p>";
    set({ axaBack: { from: "recherche", q } }); // la fiche ouverte proposera « revenir à ta recherche »
    lastHits = await kb.searchAll(q);
    // Déduplication d'affichage : même titre + même contrat (variantes d'écriture tolérées) = 1 carte.
    const vu = new Set();
    lastHits = lastHits.filter(h => {
      const k = rnorm(String(h.contrat || "").replace(/\(.*?\)/g, "")).replace(/[^a-z0-9]/g, "") + "|" +
                rnorm(h.label || h.text.slice(0, 40)).replace(/[^a-z0-9]/g, "");
      if (vu.has(k)) return false; vu.add(k); return true;
    });
    paint();
  }
  input.addEventListener("input", e => { clearTimeout(t); t = setTimeout(() => run(e.target.value), 250); });
  // Requête transportée depuis la barre du bandeau (recherche contextuelle AXA).
  const carried = (get("axaQuery") || "").trim();
  if (carried.length >= 2) { input.value = carried; run(carried); }
}

/* ---------- Copilote de réponse (SANS IA) — interface de travail GUIDÉE ----------
   Doctrine inchangée : Pack A = preuve contractuelle (fait foi) ; Pack B = raisonnement
   (jamais cité seul). Mais au lieu d'une liste brute, le copilote produit un plan de travail :
   ① ce que j'ai compris → ② base de réponse → ③ preuves PAR CONTRAT (dédupliquées) →
   ④ pistes hiérarchisées → ⑤ prochaine action → ⑥ questions de suivi. Tout est déterministe. */
const COPILOTE_EXEMPLES = ["décès accidentel couvert ?", "délai de carence", "rachat possible", "exclusions décès", "invalidité IPT", "bénéficiaire"];

// Type de question détecté par lexique (déterministe, affiché à l'utilisateur).
const COP_TYPES = [
  ["exclusion", ["exclu", "exclusion"], "une exclusion"],
  ["delai", ["delai", "carence", "attente", "franchise"], "un délai / une franchise"],
  ["plafond", ["plafond", "capital", "montant", "limite"], "un plafond / un montant"],
  ["rachat", ["rachat", "racheter", "retrait"], "le rachat ou le retrait"],
  ["fiscalite", ["fiscal", "impot", "succession", "transmission", "abattement"], "la fiscalité"],
  ["beneficiaire", ["beneficiaire"], "la clause bénéficiaire"],
  ["definition", ["definition", "signifie", "veut dire"], "une définition"],
  ["couverture", ["couvert", "couverture", "garanti", "garantie", "prise en charge", "rembourse"], "une couverture / garantie"],
];
// Questions de suivi par type (relancent le copilote — jamais une avalanche : 3 max).
const COP_SUIVI = {
  couverture: c => [`exclusions ${c}`, `délai de carence ${c}`, `plafond ${c}`],
  exclusion: c => [`garanties ${c}`, `conditions ${c}`, `délai de carence ${c}`],
  delai: c => [`exclusions ${c}`, `plafond ${c}`],
  plafond: c => [`garanties ${c}`, `exclusions ${c}`],
  rachat: c => [`fiscalité rachat ${c}`, `délais ${c}`],
  fiscalite: c => [`bénéficiaire ${c}`, `plafond ${c}`],
  beneficiaire: c => [`fiscalité transmission ${c}`, `garanties ${c}`],
  definition: c => [`garanties ${c}`, `exclusions ${c}`],
};
// Priorité humaine des branches Pack B (nécessaire > utile > secondaire).
const COP_B_PRIORITE = {
  regles_transverses_et_garde_fous: ["nécessaire", "garde-fou à respecter avant de répondre"],
  arbres_decision: ["utile", "pour structurer le raisonnement"],
  modeles_reponse_par_question: ["utile", "pour formuler la réponse"],
  raisonnements_complexes: ["utile", "si le cas est complexe"],
  matrices_croisement_avance: ["secondaire", "croisements avancés"],
};

async function copilote(body) {
  body.innerHTML = `
    <p class="lead">Pose ta question : le copilote la décode, rassemble les <b>preuves (Pack A — font foi)</b>
    par contrat, hiérarchise les <b>pistes (Pack B — jamais une preuve)</b> et te propose la suite.
    <b>Sans IA, tout est sourcé — la notice PDF fait toujours foi.</b></p>
    <div class="view-head" style="margin-top:0">
      <input class="filter" id="cop_q" placeholder="Ex : le décès accidentel est-il couvert par MasterLife ?" aria-label="Question au copilote" autofocus>
    </div>
    <div class="filters" id="cop_ex">${COPILOTE_EXEMPLES.map(x => `<button class="chip" data-ex="${esc(x)}">${esc(x)}</button>`).join("")}</div>
    <div id="cop_res"><p class="muted">Tape une question (≥ 2 caractères) ou choisis un exemple. Aucune donnée client n'est stockée.</p></div>`;
  const input = body.querySelector("#cop_q");
  const res = body.querySelector("#cop_res");

  const norm = s => String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  const slugc = s => norm(s).replace(/[^a-z0-9]/g, "");
  const highlight = (text, terms) => {
    let out = esc(String(text).slice(0, 320));
    for (const t of terms) { if (t.length < 2) continue; out = out.replace(new RegExp("(" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi"), "<mark>$1</mark>"); }
    return out;
  };
  // Le texte des preuves commence souvent par son propre titre ("X — X. …") : on ne l'affiche qu'une fois.
  const texteSansTitre = (text, label) => {
    let t = String(text || "").trim(); const L = String(label || "").trim();
    for (let i = 0; i < 2 && L && norm(t).startsWith(norm(L)); i++) t = t.slice(L.length).replace(/^\s*[—:.\-]\s*/, "");
    return t.trim() || L;
  };

  const contratsRef = ((await kb.source("contrats_resume_humain"))?.contrats || []).map(c => c.nom);

  // ① Compréhension déterministe de la question : contrats cités + type détecté (montrés à l'utilisateur).
  function comprendre(q) {
    const nq = slugc(q);
    const cites = contratsRef.filter(n => {
      const s = slugc(n).replace(/assurance(vie|obseques)|garantiedesaccidentsdelavie|plandepargne.*/g, "");
      return s.length >= 5 && nq.includes(s.slice(0, Math.min(s.length, 9)));
    });
    const type = COP_TYPES.find(([, kws]) => kws.some(k => norm(q).includes(k)));
    return { cites, type: type ? { id: type[0], libelle: type[2] } : null };
  }

  function briefText(q, comp, groupes, reasoning) {
    const L = ["QUESTION : " + q,
               "COMPRIS : " + (comp.type ? comp.type.libelle : "recherche générale") +
               (comp.cites.length ? " · contrat(s) : " + comp.cites.join(", ") : " · aucun contrat précisé"), "",
               "PREUVES CONTRACTUELLES (Pack A — à vérifier sur la notice PDF, qui fait foi) :"];
    for (const g of groupes) for (const h of g.items) L.push(`- [${g.contrat}] ${h.label} : ${texteSansTitre(h.text, h.label)}`);
    if (!groupes.length) L.push("- (aucune preuve trouvée — ne pas répondre sans vérifier la notice)");
    L.push("", "PISTES (Pack B — aide à la décision, NON contractuel) :");
    reasoning.slice(0, 4).forEach(r => L.push(`- [${r.branchLabel}] ${r.text}`));
    L.push("", "RÈGLE : la notice PDF fait foi. Vérifier avant toute réponse au client.");
    return L.join("\n");
  }

  // Nom canonique d'un contrat, tolérant aux variantes d'écriture (« EssenCiel » =
  // « Essen'Ciel (assurance obsèques) ») : clé = slug du nom SANS parenthèses.
  const cleContrat = n => slugc(String(n || "").replace(/\(.*?\)/g, ""));
  const refParCle = new Map(contratsRef.map(n => [cleContrat(n), n]));
  const canonNom = n => refParCle.get(cleContrat(n)) || n;

  // Regroupe les preuves PAR CONTRAT, dédupliquées (même titre + même contrat = 1 seule carte).
  function grouper(preuves, cites) {
    const vu = new Set(); const parContrat = new Map();
    for (const h of preuves) {
      const c = h.contrat ? canonNom(h.contrat) : "Transverse";
      const cle = cleContrat(c) + "|" + slugc(h.label || h.text.slice(0, 40));
      if (vu.has(cle)) continue; vu.add(cle);
      if (!parContrat.has(c)) parContrat.set(c, []);
      parContrat.get(c).push(h);
    }
    const groupes = [...parContrat.entries()].map(([contrat, items]) => ({
      contrat, items: items.slice(0, 3), enPlus: Math.max(0, items.length - 3),
      cite: cites.some(n => slugc(n) === slugc(contrat)),
      score: Math.max(...items.map(i => i.score || 0)),
    }));
    groupes.sort((a, b) => (b.cite - a.cite) || (b.score - a.score));
    return groupes;
  }

  function render(q, comp, groupes, reasoning) {
    const terms = norm(q).match(/[a-z0-9]{2,}/g) || [];
    const meilleur = groupes[0]?.items[0];
    const contratPrincipal = comp.cites[0] || groupes[0]?.contrat;
    const directes = !!(comp.cites.length && groupes[0]?.cite);

    // ① Ce que j'ai compris
    const h = [`<div class="card cop-compris"><div class="card-h"><span class="pill">① ce que j'ai compris</span></div>
      <p class="card-b">Tu cherches ${comp.type ? "<b>" + esc(comp.type.libelle) + "</b>" : "une information contractuelle"}
      ${comp.cites.length ? " sur <b>" + comp.cites.map(esc).join("</b> et <b>") + "</b>."
                          : ".<br><span class='muted'>Aucun contrat précisé — je regarde les 9. Précise un contrat pour une réponse plus sûre.</span>"}
      ${comp.cites.length > 1 ? "<br><span class='muted'>Plusieurs contrats cités : demande la comparaison à ton IA (voir « Utiliser avec une IA »).</span>" : ""}</p></div>`];

    // ② Base de réponse (jamais une réponse inventée : le meilleur élément sourcé + prudence).
    // Signal faible = la preuve de tête ne couvre presque aucun mot significatif de la question
    // (question hors domaine contractuel ou trop large) → prévenir au lieu de faire semblant.
    const motsClefs = terms.filter(t => t.length >= 4);
    const meule = meilleur ? norm([meilleur.label, meilleur.text, meilleur.contrat, meilleur.type].join(" ")) : "";
    const couverture = meilleur && motsClefs.length
      ? motsClefs.filter(t => meule.includes(t)).length / motsClefs.length : 1;
    if (meilleur && couverture < 0.4 && !directes) {
      h.push(`<div class="card"><div class="card-h"><span class="pill pending">② signal faible</span></div>
        <p class="card-b warn">Ta question ne recoupe presque aucun terme de la base contractuelle —
        elle est peut-être <b>hors du domaine des contrats</b> ou <b>trop large</b>.</p>
        <p class="muted">Ce que j'ai de plus proche (à prendre avec prudence) :
        <b>${esc(meilleur.label || "")}</b> <span class="muted">(${esc(groupes[0].contrat)})</span> —
        ${highlight(texteSansTitre(meilleur.text, meilleur.label), terms)}</p>
        <p class="muted">Reformule avec les mots de la notice, précise un contrat, ou vois les
        <a href="#/sources">sources officielles</a> si c'est réglementaire.</p></div>`);
    } else if (meilleur) {
      h.push(`<div class="card cop-base"><div class="card-h"><span class="pill integrated">② base de réponse</span>
        <span class="pill ${directes ? "integrated" : "pending"}">${directes ? "preuve directe du contrat visé" : "élément le plus proche — à confirmer"}</span></div>
        <p class="card-b"><b>${esc(meilleur.label || "")}</b> <span class="muted">(${esc(groupes[0].contrat)} · ${esc(meilleur.type)})</span><br>
        ${highlight(texteSansTitre(meilleur.text, meilleur.label), terms)}</p>
        <p class="muted">Formule ta réponse à partir de cet élément, après contrôle de la notice (elle fait foi)${directes ? "" :
          " — et vérifie que le contrat correspond bien à la situation du client"}.</p>
        <p class="muted"><a href="${meilleur.ref}">→ ouvrir la fiche ${esc(groupes[0].contrat)}</a> · <a href="#/pdf">📄 notice</a></p></div>`);
    } else {
      h.push(`<div class="card"><div class="card-h"><span class="pill pending">② pas de preuve trouvée</span></div>
        <p class="card-b warn">Je n'ai trouvé aucun fait contractuel pour ces mots. <b>Ne réponds pas au client sans vérifier.</b></p>
        <p class="muted">Essaie : reformuler avec le mot de la notice (ex. « rachat » plutôt que « récupérer l'argent »),
        préciser le contrat, ou <a href="#/pdf">ouvrir la notice</a> · <a href="#/sources">source officielle</a> si c'est réglementaire.</p></div>`);
    }

    // ③ Preuves par contrat (dédupliquées, 3 max par contrat, contrat visé ouvert)
    if (groupes.length) {
      h.push(`<h3 class="day-h">③ Preuves par contrat <span class="pill integrated">Pack A · font foi</span></h3>`);
      groupes.slice(0, 5).forEach((g, i) => {
        h.push(`<details class="acc" ${i === 0 ? "open" : ""}><summary><b>${esc(g.contrat)}</b>
          <span class="muted">${g.items.length + g.enPlus} preuve(s)${g.cite ? " · contrat cité dans ta question" : ""}</span></summary>
          ${g.items.map(x => `<article class="card"><div class="card-h"><span class="pill">${esc(x.type)}</span><strong>${esc(x.label || "(sans titre)")}</strong></div>
            <p class="card-b">${highlight(texteSansTitre(x.text, x.label), terms)}</p>
            <p class="muted"><a href="${x.ref}">→ fiche</a> · <a href="#/pdf">📄 notice</a></p></article>`).join("")}
          ${g.enPlus ? `<p class="muted">+ ${g.enPlus} autre(s) — <a href="${g.items[0].ref}">voir la fiche complète</a></p>` : ""}</details>`);
      });
    }

    // ④ Pistes hiérarchisées (Pack B) — repliées, jamais un mur
    if (reasoning.length) {
      h.push(`<h3 class="day-h">④ Pistes à examiner <span class="pill pending">Pack B · jamais une preuve</span></h3>`);
      reasoning.slice(0, 4).forEach(r => {
        const [prio, pourquoi] = COP_B_PRIORITE[r.branch] || ["secondaire", r.branchLabel];
        h.push(`<details class="acc"><summary><span class="pill ${prio === "nécessaire" ? "integrated" : "pending"}">${prio}</span>
          <b>${esc(r.label)}</b> <span class="muted">— ${esc(pourquoi)}</span></summary>
          <p class="card-b">${highlight(r.text, terms)}</p></details>`);
      });
    }

    // ⑤ Prochaine action (contextualisée)
    h.push(`<h3 class="day-h">⑤ Prochaine action</h3><div class="card"><div class="btns">
      ${contratPrincipal ? `<a class="btn gold" href="#/contrat/${slugc(contratPrincipal)}">📑 Ouvrir la fiche ${esc(contratPrincipal)}</a>` : ""}
      <button class="btn ghost" id="cop_copy">📋 Copier le brief sourcé</button>
      <a class="btn ghost" href="#/assistants">📦 Poser la question à ton IA (pack)</a></div></div>`);

    // ⑥ Questions de suivi (3 max, liées au cas)
    const suite = (COP_SUIVI[comp.type?.id] || COP_SUIVI.couverture)(contratPrincipal || "").map(s => s.trim());
    h.push(`<h3 class="day-h">⑥ Questions de suivi</h3><div class="filters">${
      [...new Set(suite)].slice(0, 3).map(s => `<button class="chip" data-suivi="${esc(s)}">${esc(s)}</button>`).join("")}</div>`);

    res.innerHTML = h.join("");
    bindCopy(res.querySelector("#cop_copy"), () => briefText(q, comp, groupes, reasoning));
    res.querySelectorAll("[data-suivi]").forEach(b => b.onclick = () => { input.value = b.dataset.suivi; run(b.dataset.suivi); window.scrollTo(0, 0); });
  }

  let t;
  async function run(q) {
    q = (q || "").trim();
    if (q.length < 2) { res.innerHTML = `<p class="muted">Tape une question (≥ 2 caractères) ou choisis un exemple.</p>`; return; }
    res.innerHTML = `<p class="muted">Analyse de la question, recherche des preuves et des pistes…</p>`;
    set({ axaBack: { from: "copilote", q } }); // la fiche ouverte proposera « revenir à ta question »
    const comp = comprendre(q);
    const [preuves, reasoning] = await Promise.all([kb.searchAll(q, { includeMaster: false }), kb.reasoningB(q)]);
    render(q, comp, grouper(preuves.slice(0, 24), comp.cites), reasoning);
  }
  input.addEventListener("input", e => { clearTimeout(t); t = setTimeout(() => run(e.target.value), 250); });
  body.querySelector("#cop_ex").addEventListener("click", e => {
    const b = e.target.closest("[data-ex]"); if (!b) return;
    input.value = b.dataset.ex; run(b.dataset.ex); input.focus();
  });
  const carried = (get("axaQuery") || "").trim();
  if (carried.length >= 2) { input.value = carried; run(carried); }
}

/* ---------- Glossaire transversal (dérivé, sourcé) ---------- */
async function glossaire(body, human) {
  const fiches = await kb.source("fiches_conseiller");
  const gloss = fiches?.glossaire || [];
  if (!gloss.length) { body.innerHTML = `<p class="warn">Glossaire indisponible (régénérer <code>scripts/build_axa_fiches.py</code>).</p>`; return; }
  if (!human) { body.innerHTML = `<pre>${esc(JSON.stringify(gloss, null, 2).slice(0, 120000))}</pre>`; return; }
  // Lien vers la notice (réutilise la logique pdf_index → URL#page).
  const pdfIdx = await kb.source("pdf_index");
  const pdfByName = new Map();
  for (const p of (pdfIdx?.pdfs || [])) { const b = String(p.path || "").split("/").pop(); if (b) pdfByName.set(b, kb.pdfUrl(p.path)); }
  const srcLink = s => {
    if (!s || !s.document_source) return "";
    const b = String(s.document_source).split("/").pop();
    const url = (pdfByName.get(b) || ("../data/AXA/00_PACKAGE_ACTIF/Contrats-AXA/" + s.document_source)) + (s.page ? "#page=" + s.page : "");
    return ` <a class="src-link" href="${esc(url)}" target="_blank" rel="noopener" title="Notice${s.page ? " p." + s.page : ""}">📄 notice${s.page ? " p." + s.page : ""}</a>`;
  };
  const norm = s => String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  function render(q = "") {
    const ql = norm(q.trim());
    const list = ql ? gloss.filter(g => norm(g.terme).includes(ql) || g.entrees.some(e => norm(e.definition).includes(ql))) : gloss;
    body.innerHTML = `<p class="lead">Glossaire transversal : ${gloss.length} termes définis dans les notices AXA, regroupés par terme (sourcés — la notice fait foi).</p>
      <div class="view-head" style="margin-top:0"><input class="filter" id="glq" placeholder="🔎 filtrer un terme…" aria-label="Filtrer le glossaire" value="${esc(q)}"></div>
      ${list.map(g => `<article class="card"><div class="card-h"><strong>${esc(g.terme)}</strong>${g.entrees.length > 1 ? `<span class="tag">défini dans ${g.entrees.length} contrats</span>` : ""}</div>
        <ul class="hlist">${g.entrees.map(e => `<li><span class="muted">${esc(e.contrat)} :</span> ${esc(e.definition)}${srcLink(e.source)}</li>`).join("")}</ul></article>`).join("") || "<p class='muted'>Aucun terme.</p>"}`;
    const inp = body.querySelector("#glq");
    let t; inp.addEventListener("input", e => { clearTimeout(t); const v = e.target.value; t = setTimeout(() => { render(v); const i = body.querySelector("#glq"); i.focus(); i.setSelectionRange(v.length, v.length); }, 200); });
  }
  render();
}

/* ---------- Cas client (Chantier 5 — divulgation progressive, statuts explicites) ----------
   Part de quelques faits (profil, événements, besoins exprimés, contrats en place) et
   construit le diagnostic AU FUR ET À MESURE : risques priorisés avec statut
   (déclaré / déduit / hypothèse), audit de l'existant (couvert-à-vérifier / doublon / trou),
   contrats à examiner, retours d'expérience étiquetés, données qui affineraient. Jamais une
   recommandation automatique : le conseiller décide, la notice PDF fait foi. */
function bullets(arr) { return `<ul class="hlist">${arr.map(x => `<li>${esc(x)}</li>`).join("")}</ul>`; }
const EVT_LABELS = {
  naissance: "👶 Naissance / enfant à venir", achat_immobilier: "🏠 Achat immobilier / crédit",
  passage_independant: "🧰 Passage en indépendant", mariage_pacs: "💍 Mariage / PACS",
  divorce: "⚡ Divorce / séparation", approche_retraite: "🌅 Retraite qui approche",
  deces_proche: "🕯 Décès d'un proche", sport_a_risque: "🏔 Sport / activité à risque",
};
// Ordre socle des priorités : dettes d'abord, catastrophique avant probable, protéger avant épargner.
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
// Passerelle entre les risques de la matrice métier (produit) et les besoins canoniques du barème
// de présélection (ia/axa_scoring_recherche_personnalisee.json). Les deux vocabulaires sont
// utilisés ENSEMBLE : mots-clés du barème ∪ mots-clés de la matrice. `null` = pas d'équivalent
// canonique (accident de la vie privée, dépendance) → seuls les mots-clés de la matrice comptent.
const RISQUE_BESOIN = {
  emprunt: "assurance_emprunteur",
  deces_protection_famille: "proteger_famille",
  arret_travail_itt: "arret_travail",
  invalidite: "invalidite",
  accident_vie_privee: null,
  education_enfants: "proteger_famille",
  dependance: null,
  obseques: "obseques_rapatriement",
  retraite_revenu: "retraite",
  epargne_transmission: "transmission",
};
// L'importance d'un besoin se déduit de son rang de priorité et de son statut épistémique :
// un besoin DÉCLARÉ par le client pèse plus qu'une HYPOTHÈSE déduite de son profil.
const POIDS_STATUT = { declare: 1, deduit: 0.85, hypothese: 0.7 };
const importanceDe = (rang, statut) => Math.round(Math.max(30, 100 - 8 * rang) * (POIDS_STATUT[statut] ?? 0.7));

async function besoins(body) {
  const resume = await kb.source("contrats_resume_humain");
  const contrats = resume?.contrats || [];
  const [matrice, evtsData, biblio] = await Promise.all([
    inspJson("metier/matrice_risques.json"), inspJson("metier/evenements_vie.json"), inspJson("experience/bibliotheque.json")]);
  const RISQUES = matrice?.risques || {};
  const EVTS = evtsData?.evenements || {};
  const DOSSIERS = biblio?.dossiers || [];
  if (!Object.keys(RISQUES).length) {
    body.innerHTML = `<p class="warn">La matrice métier n'est pas disponible (couche /ia/inspecteur non générée).
      En attendant : la <a href="#/recherche">recherche</a> et les <a href="#/contrat">fiches contrat</a> restent complètes.</p>`;
    return;
  }
  const shortR = id => String(RISQUES[id]?.libelle || id).split("—")[0].trim();
  const couvrent = id => (RISQUES[id]?.contrats || []);
  const COLLECTIF_COUVRE = new Set(["deces_protection_famille", "arret_travail_itt", "invalidite"]);

  // État du cas — local à l'écran, jamais stocké.
  const cas = { statut: "", fam: "", age: "", budget: "", credit: false, collectif: false, evts: new Set(), besoins: new Set(), existants: new Set() };
  // Dernière présélection calculée (asynchrone) — reprise par la synthèse copiable.
  let presel = null, preselJeton = 0;

  body.innerHTML = `
    <p class="lead">Pars de la <b>situation réelle</b> : coche ce que tu sais, le diagnostic se construit au fur et à mesure —
    pas de formulaire à terminer avant d'avoir de la valeur. <b>Aucune donnée client n'est stockée.</b></p>
    <div class="card">
      <div class="ess-h" style="margin-bottom:8px">La situation <span style="text-transform:none;letter-spacing:0">— dans n'importe quel ordre</span></div>
      <div class="row3">
        <label>Statut professionnel<select id="cc_statut"><option value="">je ne sais pas encore</option><option>Salarié</option><option>Indépendant / TNS</option><option>Fonctionnaire</option><option>Retraité</option><option>Sans activité</option></select></label>
        <label>Situation familiale<select id="cc_fam"><option value="">je ne sais pas encore</option><option>Célibataire</option><option>En couple</option><option>Avec enfants</option><option>Famille recomposée</option></select></label>
        <label>Âge<input id="cc_age" type="number" min="16" max="100" placeholder="ex. 42"></label>
      </div>
      <div class="filters" style="margin:8px 0 0">
        <label class="inline"><input type="checkbox" id="cc_credit"> crédit en cours</label>
        <label class="inline"><input type="checkbox" id="cc_collectif"> couverture collective employeur</label>
        <label class="inline" style="margin-left:10px">budget <input id="cc_budget" type="number" min="0" step="5" placeholder="€/mois" style="width:88px;margin:0 6px"> <span class="muted">optionnel</span></label>
      </div>
      <div class="ess-h" style="margin:12px 0 4px">Événements récents ou à venir</div>
      <div class="filters" id="cc_evts">${Object.keys(EVTS).map(k => `<button class="chip" data-evt="${k}">${esc(EVT_LABELS[k] || k)}</button>`).join("")}</div>
      <div class="ess-h" style="margin:10px 0 4px">Besoins exprimés par le client</div>
      <div class="filters" id="cc_bes">${Object.keys(RISQUES).map(k => `<button class="chip" data-bes="${k}">${esc(shortR(k))}</button>`).join("")}</div>
      <div class="ess-h" style="margin:10px 0 4px">Contrats déjà en place</div>
      <div class="filters" id="cc_ex">${contrats.map(c => `<button class="chip" data-ex="${esc(c.nom)}">${esc(court(c.nom))}</button>`).join("")}</div>
      <div class="filters" style="margin-top:12px"><span class="muted" style="align-self:center;font-size:12px">Essayer :</span>
        <button class="chip" id="cc_demo1">démo : artisan TNS, 2 enfants, crédit</button>
        <button class="chip" id="cc_demo2">démo : 26 ans, célibataire, sportif</button>
        <button class="chip" id="cc_reset">↺ tout effacer</button></div>
    </div>
    <div id="cc_out"><p class="muted">Le diagnostic apparaît ici dès la première information cochée.</p></div>`;

  const flagsDe = () => {
    const f = new Set();
    if (cas.statut === "Indépendant / TNS") f.add("tns");
    if (cas.statut === "Salarié") f.add("salarie");
    if (cas.fam === "Avec enfants" || cas.fam === "Famille recomposée") f.add("enfants");
    if (cas.fam === "Famille recomposée") f.add("famille_recomposee");
    if (cas.credit) f.add("credit");
    const age = Number(cas.age);
    if (age >= 55) f.add("senior");
    if (age && age < 35) f.add("jeune");
    if (cas.fam === "Célibataire" && !f.has("enfants")) f.add("solo");
    return f;
  };
  // Chaque risque actif porte son STATUT épistémique : déclaré > déduit > hypothèse.
  const risquesActifs = flags => {
    const out = new Map(); const rank = { declare: 3, deduit: 2, hypothese: 1 };
    const add = (id, st, via) => {
      if (!RISQUES[id]) return;
      const cur = out.get(id);
      if (!cur) out.set(id, { statut: st, via: via ? [via] : [] });
      else { if (rank[st] > rank[cur.statut]) cur.statut = st; if (via) cur.via.push(via); }
    };
    for (const b of cas.besoins) add(b, "declare", "exprimé par le client");
    for (const e of cas.evts) for (const rid of (EVTS[e]?.risques || [])) add(rid, "deduit", "événement : " + String(EVT_LABELS[e] || e).replace(/^\S+\s/, ""));
    if (flags.has("credit")) add("emprunt", "deduit", "crédit en cours");
    if (flags.has("tns")) { add("arret_travail_itt", "hypothese", "statut TNS"); add("invalidite", "hypothese", "statut TNS"); }
    if (flags.has("enfants")) { add("deces_protection_famille", "hypothese", "enfants à charge"); add("education_enfants", "hypothese", "enfants à charge"); }
    if (flags.has("senior")) { add("dependance", "hypothese", "âge ≥ 55"); add("obseques", "hypothese", "âge ≥ 55"); add("retraite_revenu", "hypothese", "âge ≥ 55"); }
    return out;
  };
  const prioriser = (actifs, flags) => {
    const score = id => {
      let s = ORDRE_SOCLE.indexOf(id); if (s < 0) s = 99;
      if (flags.has("credit") && id === "emprunt") s -= 6;
      if (flags.has("tns") && id === "arret_travail_itt") s -= 3;
      if (flags.has("enfants") && id === "education_enfants") s -= 2;
      if (flags.has("enfants") && id === "deces_protection_famille") s -= 1;
      if (flags.has("senior") && (id === "dependance" || id === "obseques")) s -= 3;
      // Célibataire sans personne à charge : décès/éducation rétrogradés (sauf besoin exprimé).
      if (flags.has("solo") && !cas.besoins.has(id) && (id === "deces_protection_famille" || id === "education_enfants")) s += 8;
      return s;
    };
    return [...actifs.keys()].sort((x, y) => score(x) - score(y));
  };

  /* ---------- ② Présélection classée (barème contractuel migré du cockpit) ----------
     Le diagnostic ① reste synchrone et instantané ; la présélection se pose dès que les
     conditions de souscription sourcées sont lues. Elle ne remplace pas le raisonnement du
     conseiller : elle CLASSE les candidats de la matrice avec un motif vérifiable pour chacun,
     et n'en fait jamais disparaître un sans dire pourquoi. */
  const badgeElig = e => e.statut === "probable" ? `<span class="pill integrated">âge : compatible</span>`
    : e.statut === "exclue" ? `<span class="pill pending">âge hors plage d'adhésion</span>`
    : e.statut === "incertaine" ? `<span class="pill pending">âge : réserve à lever</span>`
    : `<span class="pill">âge : non documenté</span>`;
  const badgeBudget = b => !b.estimation ? `<span class="pill">${esc(b.statut)}</span>`
    : `<span class="pill${/au-dessus/.test(b.statut) ? " pending" : ""}">${esc(b.statut)} — à partir de ${esc(String(b.estimation.valeur).replace(".", ","))} €/mois</span>`;
  // L'estimation de prix vient d'une phrase de notice : elle est affichée avec, jamais seule.
  const citationPrix = b => !b.estimation ? "" : `<p class="fitem-x"><span class="fitem-xl">Ordre de grandeur</span> « ${esc(b.estimation.phrase)} » — ${esc(b.estimation.source.document_source || "notice")}${b.estimation.source.page ? ", p. " + esc(b.estimation.source.page) : ""}. Non contractuel : le tarificateur fait foi.</p>`;
  const citation = p => `<p class="fitem-x"><span class="fitem-xl">Source</span> « ${esc(p.phrase)} » — ${esc(p.doc || "notice")}${p.page ? ", p. " + esc(p.page) : ""}${p.section ? " · " + esc(p.section) : ""}</p>`;
  // Besoins que ce contrat n'adresse pas du tout (à distinguer de ceux qu'il annonce sans les documenter).
  const nonAdresses = r => r.besoins.detail.filter(d => !d.rattache).map(d => d.libelle);

  function carteContrat(r, rang, trous) {
    // « Répond à » : les besoins actifs que la matrice métier rattache à ce contrat (le POURQUOI
    // du classement reste le besoin du client, pas le score).
    const pour = [...trous, ...ordreCourant.filter(id => !trous.includes(id))]
      .filter(id => couvrent(id).some(n => cleNom(n) === r.cle));
    const q = pour.length ? (RISQUES[pour[0]].questions || [])[0] : null;
    const axes = `éligibilité ${r.eligibilite.score} · besoins ${Math.round(r.besoins.scoreCouverture)} · importance ${Math.round(r.besoins.scoreImportance)} · budget ${r.budget.score} · confiance ${r.confiance}`;
    return `<div class="fitem">
      <div class="fitem-t">${rang}. ${esc(court(r.nom))} <span class="pill integrated">score ${esc(String(r.score).replace(".", ","))}/100</span> ${badgeElig(r.eligibilite)} ${badgeBudget(r.budget)}</div>
      ${pour.length ? `<p class="fitem-x"><span class="fitem-xl">Répond à</span> ${esc(pour.map(shortR).join(" · "))}</p>` : ""}
      ${r.eligibilite.preuves.slice(0, 1).map(citation).join("")}
      ${citationPrix(r.budget)}
      ${q ? `<p class="fitem-x"><span class="fitem-xl">À demander d'abord</span> ${esc(q)}</p>` : ""}
      <p class="fitem-x"><span class="fitem-xl">Décomposition</span> ${esc(axes)}</p>
      ${r.besoins.annonces.length ? `<p class="fitem-x"><span class="fitem-xl">À creuser</span> ${esc(r.besoins.annonces.join(", "))} — la matrice rattache ce besoin au contrat, mais aucune source chargée ne le documente : à vérifier à la notice.</p>` : ""}
      ${nonAdresses(r).length ? `<p class="fitem-x"><span class="fitem-xl">N'adresse pas</span> ${esc(nonAdresses(r).join(", "))}</p>` : ""}
      <div class="btns" style="margin:6px 0 0"><a class="btn ghost" href="#/contrat/${esc(r.cle)}">📑 Ouvrir la fiche sourcée</a></div>
    </div>`;
  }

  function rendrePresel(res, trous) {
    if (!res.classes.length) {
      return `<p class="muted">Aucun contrat de la base ne dépasse le seuil de ${res.seuil}/100 pour ce cas.
        ${res.ecartes.length ? `Voir ci-dessous pourquoi les ${res.ecartes.length} contrats examinés ont été écartés.` : ""}</p>
        ${blocEcartes(res)}`;
    }
    const sansCandidat = trous.filter(id => !couvrent(id).length);
    return `<p class="muted" style="margin-top:0">${res.classes.length} contrat(s) sur ${res.total} examiné(s), classés par le barème contractuel
      (éligibilité 25 % · besoins couverts 30 % · importance des besoins 20 % · budget 15 % · confiance documentaire 10 %).
      ${res.remunerationExclue ? "<b>La rémunération conseiller n'entre pas dans le calcul.</b>" : ""}</p>
      ${res.classes.map((r, i) => carteContrat(r, i + 1, trous)).join("")}
      ${sansCandidat.length ? `<div class="fitem"><div class="fitem-t">Sans candidat dans la base</div>
        <p class="fitem-b muted">${esc(sansCandidat.map(shortR).join(" · "))} — aucun contrat de la base ne couvre ce besoin : voir l'offre hors périmètre.</p></div>` : ""}
      ${blocEcartes(res)}`;
  }

  const blocEcartes = res => !res.ecartes.length ? "" : `<details class="acc" style="margin-top:10px">
    <summary>👁 Les ${res.ecartes.length} contrats écartés, et pourquoi <span class="muted">— rien n'est masqué en silence</span></summary>
    ${res.ecartes.map(r => `<div class="fitem" style="margin:8px 0"><div class="fitem-t">${esc(court(r.nom))} <span class="pill pending">${esc(r.motif)}</span></div>
      ${r.eligibilite.preuves.slice(0, 1).map(citation).join("")}
      <div class="btns" style="margin:6px 0 0"><a class="btn ghost" href="#/contrat/${esc(r.cle)}">📑 Vérifier au contrat</a></div></div>`).join("")}
    <p class="muted" style="margin:8px 0 0">Une limite d'âge lue dans une notice peut ne viser qu'une garantie ou une option : la notice PDF fait foi.</p></details>`;

  let ordreCourant = [];
  async function peindrePresel(ordre, actifs, trous) {
    const jeton = ++preselJeton;
    const zone = body.querySelector("#cc_presel");
    if (!zone) return;
    const criteres = {
      age: cas.age === "" ? null : Number(cas.age),
      budget_mensuel: cas.budget === "" ? null : Number(cas.budget),
      besoins: ordre.map((id, i) => ({
        id, libelle: shortR(id), importance: importanceDe(i, actifs.get(id).statut),
        besoin_canonique: RISQUE_BESOIN[id] ?? null, mots_cles: RISQUES[id]?.mots_cles || [],
        contrats: couvrent(id),   // la matrice métier tranche ce que les mots-clés se contentent d'orienter
      })),
      existants: [...cas.existants],
    };
    let res;
    try { res = await preselection(criteres); }
    catch (e) {
      if (jeton === preselJeton) zone.innerHTML = `<p class="warn">Présélection indisponible (${esc(e.message)}) — les fiches contrat restent complètes.</p>`;
      return;
    }
    if (jeton !== preselJeton || !body.querySelector("#cc_presel")) return;   // un changement plus récent a relancé le calcul
    presel = res;
    body.querySelector("#cc_presel").innerHTML = rendrePresel(res, trous);
    // Le RDV se prépare sur le contrat le mieux classé, pas sur le premier venu de la matrice.
    const btn = body.querySelector("#cc_rdv");
    if (btn && res.classes[0]) { btn.dataset.contrat = res.classes[0].nom; btn.textContent = `🗓 Préparer le RDV (${court(res.classes[0].nom)})`; }
  }

  function paint() {
    const out = body.querySelector("#cc_out");
    const flags = flagsDe();
    const actifs = risquesActifs(flags);
    if (!actifs.size) { out.innerHTML = `<p class="muted">Le diagnostic apparaît ici dès la première information cochée.</p>`; return; }
    const ordre = prioriser(actifs, flags);
    const exNoms = [...cas.existants];
    const couvertsPar = id => exNoms.filter(n => couvrent(id).some(x => cleNom(x) === cleNom(n)));
    const stBadge = st => st === "declare" ? `<span class="pill integrated">déclaré</span>`
      : st === "deduit" ? `<span class="pill">déduit</span>` : `<span class="pill pending">hypothèse</span>`;

    // ① Diagnostic priorisé, chaque ligne dit son statut, son rang et l'état de couverture.
    const lignes = ordre.map((id, i) => {
      const a = actifs.get(id);
      const cvts = couvertsPar(id);
      const parCollectif = cas.collectif && COLLECTIF_COUVRE.has(id);
      let etat;
      if (cvts.length >= 2) etat = `<span class="pill pending">doublon possible : ${esc(cvts.map(court).join(" + "))}</span>`;
      else if (cvts.length === 1) etat = `<span class="pill">couvert par ${esc(court(cvts[0]))} — à vérifier au contrat</span>`;
      else if (parCollectif) etat = `<span class="pill">peut-être couvert par le collectif — à vérifier</span>`;
      else etat = `<span class="pill pending">non couvert — trou potentiel</span>`;
      return `<div class="fitem"><div class="fitem-t">${i + 1}. ${esc(shortR(id))} ${stBadge(a.statut)} ${etat}</div>
        <p class="fitem-x"><span class="fitem-xl">Pourquoi ce rang</span> ${esc(POURQUOI_RANG[id] || "")}</p>
        ${a.via.length ? `<p class="fitem-x"><span class="fitem-xl">D'où ça vient</span> ${esc([...new Set(a.via)].join(" · "))}</p>` : ""}</div>`;
    }).join("");

    // ② Contrats à examiner pour les trous (candidats de la matrice, hors existants).
    const trous = ordre.filter(id => !couvertsPar(id).length && !(cas.collectif && COLLECTIF_COUVRE.has(id))).slice(0, 4);
    const candOf = id => couvrent(id).filter(n => !exNoms.some(x => cleNom(x) === cleNom(n)));

    // ③ Retours d'expérience applicables (bibliothèque, filtrés par sous-ensemble de flags).
    const lecons = [];
    for (const d of DOSSIERS) for (const l of (d.lecons || []))
      if ((l.si || []).length && (l.si || []).every(fl => flags.has(fl))) lecons.push(l);
    const TYPE_LECON = { piege: "⚠ piège", question_a_poser: "❓ à poser", strategie: "🧭 stratégie", arbitrage: "⚖ arbitrage", risque_cache: "🕳 risque caché" };
    const expBloc = lecons.length ? `<details class="acc" open><summary>📚 Retours d'expérience applicables (${lecons.length}) <span class="muted">— dossiers similaires, à valider</span></summary>
      ${lecons.slice(0, 5).map(l => `<div class="fitem" style="margin:8px 0"><div class="fitem-t">${TYPE_LECON[l.type] || esc(l.type || "")}</div><p class="fitem-b">${esc(l.lecon)}</p></div>`).join("")}</details>` : "";

    // ④ Les données qui changeraient le diagnostic (uniquement celles qui manquent).
    const manquent = [];
    if (!cas.statut) manquent.push("Statut professionnel : il change la priorité arrêt de travail (le TNS est mal couvert par le régime obligatoire).");
    if (!cas.fam) manquent.push("Situation familiale : qui dépend de ce revenu ? (décès, éducation)");
    if (!cas.age) manquent.push("Âge : il conditionne l'assurabilité (dépendance, obsèques) et les limites de souscription.");
    if (cas.statut === "Salarié" && !cas.collectif) manquent.push("Couverture collective : un salarié en a souvent une — vérifier avant de doubler décès/ITT/invalidité.");
    if (!cas.existants.size) manquent.push("Contrats existants : sans eux, impossible de voir doublons et trous réels.");

    const cand1 = trous.length ? candOf(trous[0])[0] : null;
    const synthese = () => {
      const L = ["CAS CLIENT — diagnostic provisoire (aide au raisonnement, à valider)", ""];
      const sit = [cas.statut, cas.fam, cas.age ? cas.age + " ans" : "", cas.credit ? "crédit en cours" : "", cas.collectif ? "couverture collective" : ""].filter(Boolean).join(" · ");
      if (sit) L.push("SITUATION : " + sit);
      if (cas.evts.size) L.push("ÉVÉNEMENTS : " + [...cas.evts].map(e => String(EVT_LABELS[e] || e).replace(/^\S+\s/, "")).join(" · "));
      if (exNoms.length) L.push("DÉJÀ EN PLACE : " + exNoms.join(" · "));
      L.push("", "RISQUES PAR PRIORITÉ :");
      ordre.forEach((id, i) => {
        const a = actifs.get(id); const cvts = couvertsPar(id);
        const etat = cvts.length >= 2 ? "doublon possible (" + cvts.join(" + ") + ")" : cvts.length === 1 ? "couvert par " + cvts[0] + " — à vérifier" : (cas.collectif && COLLECTIF_COUVRE.has(id)) ? "peut-être couvert par le collectif" : "non couvert (trou potentiel)";
        L.push(`${i + 1}. ${shortR(id)} [${a.statut}] — ${etat}`);
      });
      if (presel?.classes?.length) {
        L.push("", `PRÉSÉLECTION CLASSÉE (barème contractuel, seuil ${presel.seuil}/100 — rémunération exclue du calcul) :`);
        presel.classes.forEach((r, i) => {
          L.push(`${i + 1}. ${court(r.nom)} — score ${String(r.score).replace(".", ",")}/100 · ${r.eligibilite.statut === "probable" ? "âge compatible" : "âge : " + r.eligibilite.statut} · ${r.budget.statut}`);
          if (r.besoins.absents.length) L.push(`   non couvert par ce contrat : ${r.besoins.absents.join(", ")}`);
        });
        if (presel.ecartes.length) L.push("", "ÉCARTÉS : " + presel.ecartes.map(r => `${court(r.nom)} (${r.motif})`).join(" · "));
      } else if (trous.length) {
        L.push("", "CONTRATS À EXAMINER :"); trous.forEach(id => { const cands = candOf(id); if (cands.length) L.push(`- ${shortR(id)} : ${cands.join(" ou ")}`); });
      }
      if (manquent.length) { L.push("", "À CLARIFIER :"); manquent.forEach(x => L.push("- " + x)); }
      L.push("", "RÈGLE : hypothèse ≠ fait ; le conseiller décide ; la notice PDF fait foi. Aide IA à valider — jamais une recommandation automatique.");
      return L.join("\n");
    };

    out.innerHTML = `
      <h3 class="day-h">① Diagnostic — risques par priorité ${IA_TAG}</h3>
      <p class="muted" style="margin-top:0"><span class="pill integrated">déclaré</span> = dit par le client ·
        <span class="pill">déduit</span> = découle d'un fait (événement, crédit) ·
        <span class="pill pending">hypothèse</span> = suggéré par le profil, à confirmer</p>
      ${lignes}
      <h3 class="day-h">② Contrats à examiner — présélection classée ${IA_TAG}</h3>
      <div id="cc_presel"><p class="muted">Calcul de la présélection…</p></div>
      ${expBloc}
      ${manquent.length ? `<h3 class="day-h">③ Ce qui affinerait le diagnostic</h3>${bullets(manquent)}` : ""}
      <h3 class="day-h">④ Et maintenant</h3>
      <div class="card"><div class="btns">
        <button class="btn ghost" id="cc_copy">📋 Copier la synthèse du cas</button>
        <button class="btn ghost" id="cc_rdv">🗓 Préparer le RDV${cand1 ? " (" + esc(court(cand1)) + ")" : ""}</button>
        ${cand1 ? `<button class="btn ghost" id="cc_cop">🧠 Creuser au copilote</button>` : ""}
      </div></div>
      <div class="warnbox">⚖️ Aide au raisonnement (matrice métier IA, étiquetée, à valider) — <b>pas une recommandation</b>.
      Le conseiller décide ; garanties, exclusions et conditions se vérifient dans la fiche et la notice PDF.</div>`;
    bindCopy(out.querySelector("#cc_copy"), synthese, "✓ Synthèse copiée");
    const btnRdv = out.querySelector("#cc_rdv");
    btnRdv?.addEventListener("click", () => { set({ axaRdvPrefill: btnRdv.dataset.contrat || cand1 || exNoms[0] || "", axaRdvCase: synthese() }); location.hash = "#/rdv"; });
    out.querySelector("#cc_cop")?.addEventListener("click", () => { set({ axaQuery: `${court(cand1)} ${shortR(trous[0])} ` }); location.hash = "#/copilote"; });
    ordreCourant = ordre;
    peindrePresel(ordre, actifs, trous);
  }

  // Câblage : chaque changement re-diagnostique (divulgation progressive).
  const $ = sel => body.querySelector(sel);
  $("#cc_statut").onchange = e => { cas.statut = e.target.value; paint(); };
  $("#cc_fam").onchange = e => { cas.fam = e.target.value; paint(); };
  $("#cc_age").oninput = e => { cas.age = e.target.value; paint(); };
  $("#cc_budget").oninput = e => { cas.budget = e.target.value; paint(); };
  $("#cc_credit").onchange = e => { cas.credit = e.target.checked; paint(); };
  $("#cc_collectif").onchange = e => { cas.collectif = e.target.checked; paint(); };
  const toggleChip = (setRef, key, el) => { setRef.has(key) ? setRef.delete(key) : setRef.add(key); el.classList.toggle("on"); paint(); };
  $("#cc_evts").addEventListener("click", e => { const b = e.target.closest("[data-evt]"); if (b) toggleChip(cas.evts, b.dataset.evt, b); });
  $("#cc_bes").addEventListener("click", e => { const b = e.target.closest("[data-bes]"); if (b) toggleChip(cas.besoins, b.dataset.bes, b); });
  $("#cc_ex").addEventListener("click", e => { const b = e.target.closest("[data-ex]"); if (b) toggleChip(cas.existants, b.dataset.ex, b); });
  const applique = patch => {
    Object.assign(cas, { statut: "", fam: "", age: "", budget: "", credit: false, collectif: false }, patch);
    cas.evts = new Set(patch.evts || []); cas.besoins = new Set(patch.besoins || []); cas.existants = new Set(patch.existants || []);
    $("#cc_statut").value = cas.statut; $("#cc_fam").value = cas.fam; $("#cc_age").value = cas.age; $("#cc_budget").value = cas.budget;
    $("#cc_credit").checked = cas.credit; $("#cc_collectif").checked = cas.collectif;
    body.querySelectorAll("#cc_evts .chip, #cc_bes .chip, #cc_ex .chip").forEach(ch =>
      ch.classList.toggle("on", cas.evts.has(ch.dataset.evt) || cas.besoins.has(ch.dataset.bes) || cas.existants.has(ch.dataset.ex)));
    paint();
  };
  $("#cc_demo1").onclick = () => applique({ statut: "Indépendant / TNS", fam: "Avec enfants", age: "42", credit: true, existants: [contrats.find(c => /excelium/i.test(c.nom))?.nom].filter(Boolean) });
  $("#cc_demo2").onclick = () => applique({ statut: "Salarié", fam: "Célibataire", age: "26", evts: ["sport_a_risque"] });
  $("#cc_reset").onclick = () => applique({});
}

/* ---------- Rendez-vous : Avant · Pendant · Après (Chantier 6) ----------
   La journée réelle du conseiller, en un seul espace :
   ① AVANT — kit de préparation enrichi du cerveau inspecteur (accroche, questions de la
     matrice de risques, pièges du contrat, objections), repris du cas client si on en vient.
   ② PENDANT — accès rapide sans perdre le dossier (nouvel onglet), notes locales, marqueurs
     « à vérifier / objection / donnée manquante », formulations prudentes.
   ③ APRÈS — compte-rendu généré depuis les notes, mail client prudent, suites et 2e RDV.
   Notes en localStorage UNIQUEMENT (ce navigateur) — rien ne part dans le dépôt. */
async function rdv(body) {
  const resume = await kb.source("contrats_resume_humain");
  const contrats = resume?.contrats || [];
  const matrice = await inspJson("metier/matrice_risques.json");
  const RISQUES = Object.values(matrice?.risques || {});
  const risquesDuContrat = nom => RISQUES.filter(r => (r.contrats || []).some(x => cleNom(x) === cleNom(nom)));
  const LS_NOTES = "axa_rdv_notes_v1";
  const lireNotes = () => { try { return localStorage.getItem(LS_NOTES) || ""; } catch { return ""; } };
  const ecrireNotes = v => { try { localStorage.setItem(LS_NOTES, v); } catch {} };

  // État de l'écran : survit au changement d'onglet (pas au rechargement — sauf les notes).
  const st = { phase: "avant", obj: "", profil: "", contrat: "", etape: "" };
  const pre = get("axaRdvPrefill");
  if (pre && contrats.some(c => c.nom === pre)) {
    st.contrat = pre;
    const cPre = contrats.find(x => x.nom === pre);
    if (cPre && OBJECTIFS.some(o => o.famille === cPre.famille)) st.obj = cPre.famille;
  }
  const caseCtx = get("axaRdvCase") || ""; // synthèse du cas client, consommée une fois
  set({ axaRdvPrefill: null, axaRdvCase: null });

  const FORMULATIONS = ["« Sous réserve de vérification au contrat… »", "« La notice précise que… (page X) »", "« Je reviens vers vous après vérification »"];
  const OBJECTIONS = ["« C'est trop cher » → clarifier le besoin et les garanties réellement utiles",
    "« J'ai déjà un contrat » → comparer sans dénigrer, vérifier les doublons et les manques",
    "« Je vais réfléchir » → identifier la vraie objection, proposer une prochaine étape datée"];

  async function render() {
    const tabs = `<div class="filters" style="margin-top:0">${[["avant", "① Avant — préparer"], ["pendant", "② Pendant — s'appuyer"], ["apres", "③ Après — conclure"]]
      .map(([id, l]) => `<button class="chip ${st.phase === id ? "on" : ""}" data-ph="${id}">${l}</button>`).join("")}</div>`;
    let content = "";

    if (st.phase === "avant") {
      content = `
      <div class="card"><h3 style="margin:0 0 8px">Contexte du rendez-vous</h3>
        <div class="row3">
          <label>Objectif principal<select id="rv_obj"><option value="">—</option>${OBJECTIFS.map(o => `<option value="${esc(o.famille)}" ${st.obj === o.famille ? "selected" : ""}>${esc(o.label)}</option>`).join("")}</select></label>
          <label>Profil client<input id="rv_profil" placeholder="ex. 40 ans, marié, 2 enfants, salarié" value="${esc(st.profil)}"></label>
          <label>Contrat pressenti<select id="rv_contrat"><option value="">— (optionnel)</option>${contrats.map(c => `<option ${st.contrat === c.nom ? "selected" : ""}>${esc(c.nom)}</option>`).join("")}</select></label>
        </div>
        <div class="btns"><button class="btn gold" id="rv_go">🗓 Générer le kit de préparation</button>
          <a class="btn ghost" href="#/besoins">🧩 Partir d'un cas client</a></div>
        ${caseCtx ? `<details class="acc" style="margin-top:10px" open><summary>🧩 Cas client repris — le diagnostic te suit</summary><pre style="white-space:pre-wrap;font-size:12px;background:var(--surface-2);border-radius:8px;padding:10px;margin:8px 0 0">${esc(caseCtx)}</pre></details>` : ""}
      </div>
      <div id="rv_out"></div>`;
    } else if (st.phase === "pendant") {
      const ficheHref = st.contrat ? `#/contrat/${cleNom(st.contrat)}` : "#/contrat";
      content = `
      <div class="card"><div class="ess-h">Accès rapide — s'ouvre dans un autre onglet, ton dossier reste ici</div>
        <div class="btns">
          <a class="btn ghost" href="#/recherche" target="_blank" rel="noopener">🔎 Recherche</a>
          <a class="btn ghost" href="${ficheHref}" target="_blank" rel="noopener">📑 Fiche ${st.contrat ? esc(court(st.contrat)) : "contrat"}</a>
          <a class="btn ghost" href="#/glossaire" target="_blank" rel="noopener">📖 Glossaire</a>
          <a class="btn ghost" href="#/pdf" target="_blank" rel="noopener">📄 Notices</a>
        </div></div>
      <div class="card"><div class="ess-h">Notes du rendez-vous <span style="text-transform:none;letter-spacing:0">— locales à ce navigateur, jamais dans le dépôt</span></div>
        <div class="filters" style="margin:6px 0">
          ${[["À VÉRIFIER", "🔎 à vérifier"], ["OBJECTION", "💬 objection"], ["DONNÉE MANQUANTE", "❓ donnée manquante"], ["ACCORD", "✅ accord"]]
            .map(([tag, l]) => `<button class="chip" data-tag="${tag}">${l}</button>`).join("")}
        </div>
        <textarea id="rv_notes" rows="10" style="width:100%;resize:vertical" placeholder="Note librement. Les boutons ci-dessus insèrent un marqueur — le compte-rendu s'en servira.">${esc(lireNotes())}</textarea>
        <div class="btns" style="margin-top:8px"><button class="btn ghost" id="rv_ncopy">📋 Copier les notes</button>
          <button class="btn danger" id="rv_nclear">🗑 Effacer</button></div></div>
      <div class="card"><div class="ess-h">Formulations prudentes</div>${bullets(FORMULATIONS)}
        <p class="muted">Aucun chiffre fiscal ou social définitif en séance — « je vérifie et je reviens vers vous ».</p></div>`;
    } else {
      const notes = lireNotes();
      const lignes = notes.split("\n").map(l => l.trim()).filter(Boolean);
      const verifs = lignes.filter(l => /^— (À VÉRIFIER|DONNÉE MANQUANTE)/.test(l));
      const accords = lignes.filter(l => /^— ACCORD/.test(l));
      const libres = lignes.filter(l => !/^— (À VÉRIFIER|DONNÉE MANQUANTE|OBJECTION|ACCORD)/.test(l));
      const objLabel = OBJECTIFS.find(o => o.famille === st.obj)?.label || "";
      const cr = ["COMPTE-RENDU DE RENDEZ-VOUS — " + new Date().toLocaleDateString("fr-FR"),
        "Client : [À COMPLÉTER]" + (st.profil ? " · " + st.profil : ""),
        (objLabel ? "Objectif : " + objLabel + " · " : "") + (st.contrat ? "Contrat évoqué : " + st.contrat : ""), "",
        "CE QUI A ÉTÉ DIT / OBSERVÉ :", ...(libres.length ? libres.map(x => "- " + x.replace(/^—\s*/, "")) : ["- [À COMPLÉTER]"]),
        "", "ACCORDS :", ...(accords.length ? accords.map(x => "- " + x.replace(/^— ACCORD\s*:?\s*/, "")) : ["- [aucun noté]"]),
        "", "POINTS À VÉRIFIER AVANT TOUTE RÉPONSE :", ...(verifs.length ? verifs.map(x => "- " + x.replace(/^—\s*/, "")) : ["- [aucun noté]"]),
        "", "PROCHAINE ÉTAPE : " + (st.etape || "[À COMPLÉTER]"),
        "", "Rappel : aucune réponse engageante sans vérification au contrat / à la notice (elle fait foi)."].join("\n");
      const mail = ["Objet : Suite à notre rendez-vous", "", "Bonjour [PRÉNOM],", "",
        "Merci pour notre échange de ce jour" + (objLabel ? " au sujet de : " + objLabel.toLowerCase() : "") + ".",
        verifs.length ? "Comme convenu, je vérifie les points suivants et je reviens vers vous avant le [DATE] :" : "Comme convenu, je reviens vers vous avant le [DATE].",
        ...verifs.map(x => "- " + x.replace(/^—\s*(À VÉRIFIER|DONNÉE MANQUANTE)\s*:?\s*/, "")),
        "", "Les éléments évoqués restent à confirmer au regard des conditions du contrat — la notice d'information fait foi.",
        "", "Bien cordialement,", "[SIGNATURE]"].join("\n");
      content = `
      <div class="card"><div class="ess-h">Compte-rendu — généré depuis tes notes</div>
        <label style="display:block;margin:6px 0">Prochaine étape convenue<input id="rv_etape" placeholder="ex. second RDV le 20/07 pour présenter la proposition" value="${esc(st.etape)}" style="width:100%"></label>
        <pre id="rv_cr" style="white-space:pre-wrap;font-size:12.5px;background:var(--surface-2);border-radius:8px;padding:12px">${esc(cr)}</pre>
        <div class="btns"><button class="btn gold" id="rv_crcopy">📋 Copier le compte-rendu</button></div></div>
      <div class="card"><div class="ess-h">Mail client — trame prudente à adapter</div>
        <pre style="white-space:pre-wrap;font-size:12.5px;background:var(--surface-2);border-radius:8px;padding:12px">${esc(mail)}</pre>
        <div class="btns"><button class="btn ghost" id="rv_mailcopy">📋 Copier le mail</button></div></div>
      <div class="card"><div class="ess-h">Et ensuite</div>
        <div class="btns">
          <button class="btn ghost" id="rv_rdv2">🗓 Préparer le 2ᵉ rendez-vous</button>
          <a class="btn ghost" href="#/besoins">🧩 Compléter le cas client</a>
          ${st.contrat ? `<a class="btn ghost" href="#/contrat/${cleNom(st.contrat)}">📑 Revoir la fiche ${esc(court(st.contrat))}</a>` : ""}
        </div>
        <p class="muted" style="margin-top:8px">Après envoi du compte-rendu : penser à effacer les notes locales (onglet « Pendant »).</p></div>`;
    }

    body.innerHTML = `
      <p class="lead"><span class="qbadge q-beta">BÊTA</span> Le rendez-vous en trois temps : <b>préparer</b>, <b>s'appuyer en séance</b>, <b>conclure</b>.
      Aucune donnée client ne quitte ce navigateur.</p>
      ${tabs}${content}`;
    body.querySelectorAll("[data-ph]").forEach(bt => bt.onclick = () => { st.phase = bt.dataset.ph; render(); });

    if (st.phase === "avant") {
      body.querySelector("#rv_obj").onchange = e => { st.obj = e.target.value; };
      body.querySelector("#rv_profil").oninput = e => { st.profil = e.target.value; };
      body.querySelector("#rv_contrat").onchange = e => { st.contrat = e.target.value; };
      body.querySelector("#rv_go").onclick = async () => { await kitAvant(); };
      if (st.contrat || st.obj || caseCtx) await kitAvant(); // contexte déjà connu → le kit sort tout de suite
    } else if (st.phase === "pendant") {
      const ta = body.querySelector("#rv_notes");
      ta.addEventListener("input", () => ecrireNotes(ta.value));
      body.querySelectorAll("[data-tag]").forEach(bt => bt.onclick = () => {
        ta.value = (ta.value ? ta.value.replace(/\n?$/, "\n") : "") + "— " + bt.dataset.tag + " : ";
        ecrireNotes(ta.value); ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length);
      });
      bindCopy(body.querySelector("#rv_ncopy"), () => ta.value, "✓ Notes copiées");
      body.querySelector("#rv_nclear").onclick = () => { if (ta.value && !confirm("Effacer toutes les notes locales ?")) return; ta.value = ""; ecrireNotes(""); };
    } else {
      body.querySelector("#rv_etape").oninput = e => { st.etape = e.target.value; };
      body.querySelector("#rv_etape").onchange = () => render();
      bindCopy(body.querySelector("#rv_crcopy"), () => body.querySelector("#rv_cr").textContent, "✓ Compte-rendu copié");
      bindCopy(body.querySelector("#rv_mailcopy"), () => body.querySelectorAll("pre")[1].textContent, "✓ Mail copié");
      body.querySelector("#rv_rdv2").onclick = () => { st.phase = "avant"; st.profil = (st.profil ? st.profil + " · " : "") + "2ᵉ rendez-vous"; render(); };
    }
  }

  // Kit de préparation : méthodo famille + cerveau inspecteur du contrat pressenti (étiqueté).
  async function kitAvant() {
    const c = contrats.find(x => x.nom === st.contrat);
    const insp = c ? await inspFiche(c.nom) : null;
    const meta = FAMILLE_META[st.obj];
    const rqs = c ? risquesDuContrat(c.nom) : [];
    const questions = [...new Set([...rqs.flatMap(r => r.questions || []), ...((meta?.questions) || [])])].slice(0, 6);
    const vigilance = c ? (c.points_de_vigilance || []).map(f => f.titre || f.resume_humain || f).filter(x => typeof x === "string" && !x.startsWith("_")).slice(0, 5) : (meta?.erreurs || []);
    const accroche = iaTxt(insp?.finalite), favorable = iaTxt(insp?.situations_favorables), defavorable = iaTxt(insp?.situations_defavorables);
    const contratsVerif = st.contrat ? [st.contrat] : contrats.filter(x => x.famille === st.obj).map(x => x.nom);
    const objLabel = st.obj ? (OBJECTIFS.find(o => o.famille === st.obj)?.label || st.obj) : "";
    const sec = (t, arr) => arr.length ? `<h3 class="day-h">${t}</h3>${bullets(arr)}` : "";
    body.querySelector("#rv_out").innerHTML = `
      <div class="card" id="rv_card"><div class="card-h"><strong>Kit de préparation${st.profil ? " — " + esc(st.profil) : ""}</strong>
        <button class="btn ghost" id="rv_copy" style="min-height:30px;padding:0 10px">📋 Copier</button>
        ${printBtnHtml("rv_print")}</div>
      ${c && accroche ? `<h3 class="day-h">🎯 L'accroche — pourquoi ce contrat existe ${IA_TAG}</h3><p class="card-b">${esc(accroche)}</p>` : ""}
      ${sec("🧭 Objectifs du RDV", ["Comprendre le besoin réel et les couvertures déjà en place", objLabel ? `Explorer la piste : ${objLabel}` : "Qualifier l'objectif", "Repartir avec une prochaine étape datée"])}
      ${sec("❓ Questions de découverte", questions.length ? questions : ["Situation, objectif, budget, horizon, contrats existants ?"])}
      ${c && favorable ? `<h3 class="day-h">✓ Ce contrat est pertinent quand ${IA_TAG}</h3><p class="card-b">${esc(favorable)}</p>` : ""}
      ${c && defavorable ? `<h3 class="day-h">⚠ Il l'est moins quand ${IA_TAG}</h3><p class="card-b">${esc(defavorable)}</p>` : ""}
      ${sec("🚨 Pièges à ne pas rater", vigilance)}
      ${sec("💬 Objections probables — exemples à adapter", OBJECTIONS)}
      ${sec("📑 Contrats à vérifier avant le RDV", contratsVerif)}
      ${sec("🗣 Formulations prudentes", FORMULATIONS)}
      <div class="warnbox">⚖️ Kit d'aide à la préparation — les blocs « analyse IA » sont à valider, jamais une preuve.
      La réponse client s'appuie sur le contrat / la notice PDF / une source officielle.</div>
      <div class="btns" style="padding:0 18px 14px"><button class="btn" id="rv_allerpendant">▶ Passer en mode rendez-vous (pendant)</button></div></div>`;
    const asText = ["KIT DE PRÉPARATION" + (st.profil ? " — " + st.profil : ""), ""];
    if (caseCtx) asText.push("CAS CLIENT :", caseCtx, "");
    if (accroche) asText.push("ACCROCHE (analyse IA, à valider) : " + accroche, "");
    asText.push("QUESTIONS DE DÉCOUVERTE :", ...questions.map(x => "- " + x), "");
    if (favorable) asText.push("PERTINENT QUAND (IA, à valider) : " + favorable, "");
    if (vigilance.length) asText.push("PIÈGES :", ...vigilance.map(x => "- " + x), "");
    asText.push("OBJECTIONS :", ...OBJECTIONS.map(x => "- " + x), "", "CONTRATS À VÉRIFIER :", ...contratsVerif.map(x => "- " + x),
      "", "Rappel : la notice PDF fait foi ; aucun conseil définitif automatisé ; analyses IA à valider.");
    bindCopy(body.querySelector("#rv_copy"), () => asText.join("\n"), "✓ Kit copié");
    body.querySelector("#rv_print").onclick = () => printTarget(body.querySelector("#rv_card"));
    body.querySelector("#rv_allerpendant").onclick = () => { st.phase = "pendant"; render(); };
  }

  await render();
}

/* ---------- Mode animateur commercial ---------- */
async function animateur(body) {
  const resume = await kb.source("contrats_resume_humain");
  const contrats = resume?.contrats || [];
  if (!contrats.length) { body.innerHTML = `<p class="warn">Données contrats indisponibles.</p>`; return; }
  body.innerHTML = `
    <p class="lead">Outils pour animateur commercial : préparer un brief, repérer les erreurs, générer des cas pratiques et des questions de contrôle. Toujours distinguer preuve (Pack A) et raisonnement (Pack B).</p>
    <div class="card"><label>Contrat à travailler<select id="an_c">${contrats.map(c => `<option>${esc(c.nom)}</option>`).join("")}</select></label>
      <div class="btns"><button class="btn gold" id="an_go">🎓 Générer le brief</button></div></div>
    <div id="an_out"></div>`;
  body.querySelector("#an_go").onclick = () => {
    const c = contrats.find(x => x.nom === body.querySelector("#an_c").value);
    const meta = FAMILLE_META[c.famille] || {};
    const titres = key => (c[key] || []).map(f => f.titre || f).filter(x => typeof x === "string" && !x.startsWith("_")).slice(0, 5);
    const gar = titres("garanties_principales"), exc = titres("exclusions_importantes");
    const questionsControle = [
      `Cite deux garanties principales de ${c.nom} — et leur source.`,
      `Nomme une exclusion importante de ${c.nom} : où la vérifier ?`,
      `${c.nom} : quel est le public cible et une erreur fréquente à éviter ?`,
    ];
    const sec = (t, arr) => arr.length ? `<h3 class="day-h">${t}</h3>${bullets(arr)}` : "";
    body.querySelector("#an_out").innerHTML = `
      <div class="card" id="an_card"><div class="card-h"><strong>Brief animateur — ${esc(c.nom)}</strong><span class="tag t-themes">${esc(c.famille)}</span>
        <button class="btn ghost" id="an_copy" style="min-height:30px;padding:0 10px">📋 Copier</button>
        ${printBtnHtml("an_print")}</div>
      ${c.resume_neutre ? `<p class="card-b">${esc(c.resume_neutre.slice(0, 300))}${c.resume_neutre.length > 300 ? "…" : ""}</p>` : ""}
      ${sec("✅ Points clés à maîtriser (garanties)", gar)}
      ${sec("🚫 À bien connaître (exclusions)", exc)}
      ${sec("⚠ Erreurs fréquentes à éviter", [...(meta.erreurs || []), ...ERREURS_TRANSVERSES])}
      ${sec("🎯 Cas pratique", [`Un client type « ${meta.cible || "à qualifier"} » vous interroge sur ${c.nom}. Préparez une réponse sourcée en 3 points, puis indiquez où vérifier dans la notice PDF.`])}
      ${sec("📋 Checklist de maîtrise", ["Sait citer 2 garanties + source", "Sait citer 1 exclusion + où la vérifier", "Distingue Pack A (preuve) et Pack B (raisonnement)", "Ne donne jamais de chiffre fiscal définitif sans source"])}
      ${sec("❓ Questions de contrôle", questionsControle)}
      <div class="warnbox">⚖️ Support de formation. La preuve reste le contrat / la notice PDF. Une matrice (Pack B) n'est jamais une preuve client.</div></div>`;
    const asText = `BRIEF ANIMATEUR — ${c.nom} (${c.famille})\n\nPOINTS CLÉS\n${gar.map(x => "- " + x).join("\n")}\n\nEXCLUSIONS\n${exc.map(x => "- " + x).join("\n")}\n\nERREURS FRÉQUENTES\n${[...(meta.erreurs || []), ...ERREURS_TRANSVERSES].map(x => "- " + x).join("\n")}\n\nQUESTIONS DE CONTRÔLE\n${questionsControle.map(x => "- " + x).join("\n")}\n\nRappel : Pack A = preuve, Pack B = raisonnement ; la notice PDF fait foi.`;
    bindCopy(body.querySelector("#an_copy"), () => asText);
    body.querySelector("#an_print").onclick = () => printTarget(body.querySelector("#an_card"));
  };
}

/* ---------- Argumentaire (Chantier 7 — support de vente ÉDITABLE, sourcé, honnête) ----------
   Pas un texte généré à prendre ou à laisser : une trame structurée que le conseiller
   ADAPTE avant usage (zone éditable), avec la distinction affichée entre contenu VALIDÉ
   (faits sourcés notice) et SUGGESTION IA (analyses à valider), et des [À COMPLÉTER]
   là où la donnée manque au lieu de l'inventer. Deux formats : trame d'entretien, mail. */
const ARG_PROFILS = [["", "Profil général"], ["tns", "Indépendant / TNS"], ["famille", "Famille avec enfants"], ["senior", "Senior / retraite proche"], ["jeune", "Jeune actif"]];
const ARG_RISQUES_PROFIL = {
  tns: ["arret_travail_itt", "invalidite", "retraite_revenu", "emprunt"],
  famille: ["deces_protection_famille", "education_enfants", "emprunt", "arret_travail_itt"],
  senior: ["dependance", "obseques", "epargne_transmission", "retraite_revenu"],
  jeune: ["accident_vie_privee", "invalidite", "arret_travail_itt", "epargne_transmission"],
};
async function argumentaire(body) {
  const resume = await kb.source("contrats_resume_humain");
  const contrats = resume?.contrats || [];
  if (!contrats.length) { body.innerHTML = `<p class="warn">Données contrats indisponibles.</p>`; return; }
  const matrice = await inspJson("metier/matrice_risques.json");
  const RISQUES = matrice?.risques || {};
  const st = { contrat: "", profil: "", format: "trame" };
  const pre = get("axaArgPrefill");
  if (pre && contrats.some(c => c.nom === pre)) st.contrat = pre;
  if (!st.contrat) st.contrat = contrats[0].nom;
  set({ axaArgPrefill: null });

  body.innerHTML = `
    <p class="lead"><span class="qbadge q-beta">BÊTA</span> Une trame d'argumentaire à <b>adapter</b>, pas un texte à réciter :
    les faits sourcés (validés) et les analyses IA (suggestions à valider) sont <b>distingués</b>, et ce qui manque est marqué
    <b>[À COMPLÉTER]</b> au lieu d'être inventé.</p>
    <div class="card"><div class="row3">
      <label>Contrat<select id="ag_c">${contrats.map(c => `<option ${st.contrat === c.nom ? "selected" : ""}>${esc(c.nom)}</option>`).join("")}</select></label>
      <label>Profil client<select id="ag_p">${ARG_PROFILS.map(([v, l]) => `<option value="${v}">${esc(l)}</option>`).join("")}</select></label>
      <label>Format<select id="ag_f"><option value="trame">Trame d'entretien</option><option value="mail">Mail de proposition</option></select></label>
    </div>
    <div class="btns"><button class="btn gold" id="ag_go">🗣 Construire la trame</button></div></div>
    <div id="ag_out"></div>`;

  async function construire() {
    const c = contrats.find(x => x.nom === st.contrat);
    const insp = await inspFiche(c.nom);
    const titres = (key, n) => (c[key] || []).map(f => typeof f === "string" ? f : (f.titre && !f.titre.startsWith("_") ? f.titre : "")).filter(Boolean).slice(0, n);
    const pages = key => (c[key] || []).map(f => (f && typeof f === "object" && f.source?.page) ? `${f.titre} (notice p.${f.source.page})` : (f.titre || "")).filter(x => x && !x.startsWith("_")).slice(0, 3);
    const accroche = iaTxt(insp?.finalite), favorable = iaTxt(insp?.situations_favorables), defavorable = iaTxt(insp?.situations_defavorables);
    // Besoins du contrat, resserrés sur le profil choisi (heuristique matrice, étiquetée).
    const rIds = Object.keys(RISQUES).filter(id => (RISQUES[id].contrats || []).some(x => cleNom(x) === cleNom(c.nom)));
    const pref = ARG_RISQUES_PROFIL[st.profil] || [];
    const rOrd = [...rIds].sort((x, y) => (pref.indexOf(x) < 0 ? 9 : pref.indexOf(x)) - (pref.indexOf(y) < 0 ? 9 : pref.indexOf(y)));
    const besoins = rOrd.slice(0, 3).map(id => String(RISQUES[id].libelle || id).split("—")[0].trim());
    const profilLbl = ARG_PROFILS.find(([v]) => v === st.profil)?.[1] || "Profil général";
    const V = "[VALIDÉ — sourcé notice]", S = "[SUGGESTION IA — à valider]";
    let L;
    if (st.format === "trame") {
      L = [`TRAME D'ENTRETIEN — ${c.nom} · ${profilLbl}`, "",
        `1. ACCROCHE ${accroche ? S : ""}`,
        accroche || "[À COMPLÉTER — pourquoi ce contrat existe, en une phrase]", "",
        `2. LE BESOIN DU CLIENT ${besoins.length ? S : ""}`,
        besoins.length ? "Angles à explorer pour ce profil : " + besoins.join(" · ") : "[À COMPLÉTER — reformuler le besoin exprimé]",
        "Reformuler avec ses mots : « Si je comprends bien, vous voulez… [À COMPLÉTER] »", "",
        `3. CE QUE LE CONTRAT APPORTE ${V}`,
        ...(pages("garanties_principales").map(x => "- " + x)),
        "→ montrer la notice à la page citée, pas de promesse orale.", "",
        `4. POUR CE CLIENT ${favorable ? S : ""}`,
        favorable ? "Pertinent quand : " + favorable : "[À COMPLÉTER]",
        defavorable ? "Le dire honnêtement si : " + defavorable : "", "",
        `5. À NE PAS PROMETTRE ${V}`,
        ...(pages("exclusions_importantes").map(x => "- " + x)),
        ...(titres("points_de_vigilance", 2).map(x => "- Vigilance : " + x)), "",
        "6. OBJECTIONS PROBABLES [SUGGESTION — exemples à adapter]",
        "- « C'est trop cher » → revenir au besoin : que se passe-t-il sans couverture ?",
        "- « J'ai déjà un contrat » → proposer de vérifier doublons et trous, sans dénigrer.",
        "- « Je vais réfléchir » → identifier la vraie objection, proposer une étape datée.", "",
        "7. PROCHAINE ÉTAPE",
        "« Je vous propose [À COMPLÉTER : simulation / second RDV / vérification] d'ici le [DATE]. »", "",
        "RÈGLES : la notice PDF fait foi · aucun chiffre fiscal sans source officielle · les suggestions IA se valident avant usage."];
    } else {
      L = [`Objet : Notre échange sur ${court(c.nom)} — [À COMPLÉTER]`, "", "Bonjour [PRÉNOM],", "",
        `Suite à notre échange, voici l'essentiel sur ${c.nom}${besoins.length ? ` au regard de votre situation (${besoins[0].toLowerCase()})` : ""}.`, "",
        `Ce que ce contrat apporte ${V} :`,
        ...(pages("garanties_principales").map(x => "- " + x)), "",
        `Points d'attention dont nous avons parlé ${V} :`,
        ...(pages("exclusions_importantes").slice(0, 2).map(x => "- " + x)), "",
        "Ces éléments sont indicatifs : les conditions exactes figurent dans la notice d'information, qui fait foi — je vous la remets avec la proposition.", "",
        "Prochaine étape proposée : [À COMPLÉTER] avant le [DATE].", "",
        "Bien cordialement,", "[SIGNATURE]"];
    }
    const texte = L.filter(x => x !== "").join("\n").replace(/\n{3,}/g, "\n\n");
    const nManque = (texte.match(/\[À COMPLÉTER/g) || []).length;
    body.querySelector("#ag_out").innerHTML = `
      <div class="card">
        <div class="card-h"><strong>${st.format === "trame" ? "Trame d'entretien" : "Mail de proposition"} — ${esc(court(c.nom))}</strong>
          <span class="pill integrated">validé = sourcé</span><span class="pill pending">suggestion IA = à valider</span>
          ${nManque ? `<span class="pill pending">${nManque} champ(s) à compléter</span>` : ""}</div>
        <p class="muted" style="margin:0 0 8px">Adapte le texte ci-dessous avant usage — c'est ta trame, pas un script.</p>
        <textarea id="ag_txt" rows="22" style="width:100%;resize:vertical;font-size:13px;line-height:1.5">${esc(texte)}</textarea>
        <div class="btns" style="margin-top:8px">
          <button class="btn gold" id="ag_copy">📋 Copier</button>
          <button class="btn ghost" id="ag_regen">⟳ Régénérer</button>
          <a class="btn ghost" href="#/contrat/${cleNom(c.nom)}">📑 Revenir aux preuves (fiche)</a>
          ${printBtnHtml("ag_print")}</div>
        <div class="warnbox" style="margin-top:10px">⚖️ Support d'aide à l'entretien. Les blocs « suggestion IA » se valident avant usage ;
        les chiffres et conditions exactes se montrent sur la notice (elle fait foi).</div></div>`;
    const ta = body.querySelector("#ag_txt");
    bindCopy(body.querySelector("#ag_copy"), () => ta.value, "✓ Trame copiée");
    body.querySelector("#ag_regen").onclick = () => { if (ta.value === texte || confirm("Écraser tes modifications et régénérer ?")) construire(); };
    body.querySelector("#ag_print").onclick = () => {
      const pre2 = document.createElement("pre"); pre2.style.whiteSpace = "pre-wrap"; pre2.textContent = ta.value;
      ta.parentElement.appendChild(pre2); pre2.classList.add("print-only-temp");
      printTarget(pre2); setTimeout(() => pre2.remove(), 4000);
    };
  }
  body.querySelector("#ag_c").onchange = e => { st.contrat = e.target.value; };
  body.querySelector("#ag_p").onchange = e => { st.profil = e.target.value; };
  body.querySelector("#ag_f").onchange = e => { st.format = e.target.value; };
  body.querySelector("#ag_go").onclick = () => construire();
  if (pre) construire(); // arrivé depuis une fiche : la trame sort tout de suite
}

/* ---------- Formulaires ---------- */

/* ---------- Sources officielles (quand contrat / notice / réglementation) ---------- */
const AUTORITES = [
  ["Légifrance", "https://www.legifrance.gouv.fr", "Textes de loi et codes (assurances, sécurité sociale, CGI)."],
  ["BOFiP-Impôts", "https://bofip.impots.gouv.fr", "Doctrine fiscale de l'administration."],
  ["impots.gouv.fr", "https://www.impots.gouv.fr", "Fiscalité des particuliers."],
  ["Service-Public.fr", "https://www.service-public.fr", "Information administrative de référence."],
  ["Ameli", "https://www.ameli.fr", "Santé, maladie, invalidité (régime général)."],
  ["L'Assurance retraite (CNAV)", "https://www.lassuranceretraite.fr", "Retraite du régime général."],
  ["ACPR", "https://acpr.banque-france.fr", "Contrôle prudentiel assurances & banques."],
  ["AMF", "https://www.amf-france.org", "Marchés financiers, épargne."],
  ["URSSAF", "https://www.urssaf.fr", "Cotisations sociales."],
  ["CNIL", "https://www.cnil.fr", "Données personnelles."],
];
async function sources(body) {
  body.innerHTML = `
    <p class="lead">Gabriel AXA s'appuie sur des <b>documents publics AXA</b>. Pour une matière <b>réglementaire</b>
    (fiscalité, retraite, succession, protection sociale…), la référence n'est pas le contrat mais une <b>autorité officielle</b>.
    Voici quand consulter quoi.</p>

    <h3 class="day-h">Quelle source, quand ?</h3>
    <div class="grid">
      <div class="card"><div class="fiche-retenir-h">1 · Le contrat / la fiche</div><p class="card-b">Pour une <b>garantie, exclusion, condition, définition, barème contractuel</b> : commence par la fiche contrat (Gabriel AXA).</p></div>
      <div class="card"><div class="fiche-retenir-h">2 · La notice PDF</div><p class="card-b">Avant toute réponse client : <b>vérifie la notice</b> à la bonne page. <b>Elle fait foi.</b></p></div>
      <div class="card"><div class="fiche-retenir-h">3 · La source officielle</div><p class="card-b">Pour une <b>règle susceptible d'évoluer</b> (fiscalité, âge légal, plafond légal, succession, régime social) : consulte l'autorité compétente ci-dessous.</p></div>
    </div>

    <h3 class="day-h">Pourquoi une vérification réglementaire ?</h3>
    <div class="card"><p class="card-b">La réglementation <b>change</b> (barèmes fiscaux, âges de retraite, abattements). La base Gabriel AXA
    <b>ne stocke aucune règle réglementaire</b> et n'en invente pas : quand une question en dépend, elle vous <b>oriente vers la source officielle</b>
    plutôt que de risquer un chiffre périmé.</p></div>

    <h3 class="day-h">Autorités de référence</h3>
    <div class="grid">
      ${AUTORITES.map(([n, u, d]) => `<a class="tile" href="${u}" target="_blank" rel="noopener"><span class="tile-l">${esc(n)} ↗</span><span class="tile-s">${esc(d)}</span></a>`).join("")}
    </div>
    <p class="muted" style="margin-top:14px">Ces liens renvoient à des <b>autorités publiques</b> ; ils n'apportent aucune donnée dans Gabriel AXA.
    <a href="${IA_URL}sources-officielles.html" target="_blank" rel="noopener">↗ Détail par thème (Vue IA)</a></p>`;
}

/* ---------- PDF contractuels ---------- */
async function pdf(body) {
  const d = await kb.source("pdf_index");
  const pdfs = d?.pdfs || [];
  if (!pdfs.length) { body.innerHTML = `<p class="warn">Index PDF indisponible.</p>`; return; }
  const byContract = new Map();
  for (const p of pdfs) { const k = p.nom_contrat || "Autres"; if (!byContract.has(k)) byContract.set(k, []); byContract.get(k).push(p); }
  body.innerHTML = `<p class="muted">${pdfs.length} documents contractuels — <b>la notice PDF fait foi</b>.</p>` +
    [...byContract.entries()].map(([name, list]) => `<details class="acc" open><summary><strong>${esc(name)}</strong> <span class="muted">(${list.length})</span></summary>
      <ul class="hlist">${list.map(p => `<li><a href="${esc(kb.pdfUrl(p.path))}" target="_blank" rel="noopener">📄 ${esc(p.nom_fichier)}</a>
        <span class="muted">${esc([p.type_document, p.date_document, p.pages ? p.pages + " p." : ""].filter(Boolean).join(" · "))}</span></li>`).join("")}</ul></details>`).join("");
}

/* ---------- Historique ---------- */
async function historique(body) {
  const items = kb.history();
  body.innerHTML = `
    <div class="btns"><button class="btn danger" id="hx_clear" ${items.length ? "" : "disabled"}>🗑 Vider l'historique</button></div>
    ${items.length ? `<div class="tblwrap"><table class="tbl"><thead><tr><th>Recherche</th><th>Résultats</th><th>Quand</th></tr></thead><tbody>
      ${items.map(h => `<tr class="rowlink" data-q="${esc(h.q)}"><td style="text-align:left">${esc(h.q)}</td><td>${h.n}</td><td>${esc(new Date(h.at).toLocaleString("fr-FR"))}</td></tr>`).join("")}
    </tbody></table></div><p class="muted">Cliquer une ligne pour relancer la recherche. Historique local à ce navigateur.</p>`
    : "<p class='muted'>Aucune recherche enregistrée pour l'instant.</p>"}`;
  body.querySelector("#hx_clear")?.addEventListener("click", () => { kb.clearHistory(); historique(body); });
  body.querySelectorAll("[data-q]").forEach(tr => tr.onclick = () => {
    location.hash = "#/recherche";
    setTimeout(() => { const i = document.querySelector("#gq"); if (i) { i.value = tr.dataset.q; i.dispatchEvent(new Event("input")); } }, 400);
  });
}

/* ---------- Paramètres ---------- */
async function parametres(body) {
  body.innerHTML = `
    <div class="card"><h3 style="margin:0 0 8px">Espace AXA Conseiller</h3>
      <div class="btns">
        <button class="btn" id="px_reload">↻ Recharger le manifeste et les sources</button>
        <button class="btn ghost" id="px_clearhx">Vider l'historique de recherches</button>
        <span class="muted" id="px_st"></span></div>
      <p class="muted">Le manifeste (<code>data/AXA/workspace_manifest.json</code>) déclare les sources par rôle.
      Nouvelle version d'un master : mettre à jour le chemin, committer, recharger — aucun changement de code.
      Règles : aucune donnée client dans le dépôt · la notice PDF fait foi · l'IA propose, le conseiller décide.</p></div>`;
  body.querySelector("#px_reload").onclick = () => { kb.clearCache(); body.querySelector("#px_st").textContent = "Caches vidés — les sections rechargeront les sources."; };
  body.querySelector("#px_clearhx").onclick = () => { kb.clearHistory(); body.querySelector("#px_st").textContent = "Historique vidé."; };
}
