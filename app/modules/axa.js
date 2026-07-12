// axa — espace AXA CONSEILLER (V1.3) : assistant de travail complet, indépendant du Patrimoine.
// Routes : #/<section> — accueil, contrat, recherche, assistant, comparateur, besoins,
// formulaires, sources, pdf, historique, parametres. Les données viennent du service
// axaKnowledge (piloté par data/AXA/workspace_manifest.json — architecture évolutive).
import * as kb from "../services/axaKnowledge.js";
import { get, set } from "../state/store.js";
import { isEmpty } from "../services/humanView.js";
import { renderMarkdown } from "../services/markdown.js";
import { TUTORIEL, PROMPTS, PARCOURS, FAMILLE_META, ERREURS_TRANSVERSES, OBJECTIFS } from "./axa_content.js";

// Sections réellement implémentées (garde-fou anti-lien-mort : un parcours ne s'affiche
// que si sa cible existe). RDV/animateur s'activent automatiquement à leur implémentation.
const IMPLEMENTED = new Set(["accueil", "premiers_pas", "copilote", "contrat", "recherche", "glossaire", "comparateur",
  "besoins", "rdv", "animateur", "assistant", "assistants", "formulaires", "sources", "pdf", "historique", "parametres"]);

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
// Gabriel AXA : le shell (app.js) fournit la navigation et l'en-tête ; ce module rend UNE section.
// Vue conseiller uniquement (pas de mode « technique/IA » : jargon retiré du produit métier).
export async function mount(el, ctx) {
  const section = ctx?.section || ctx?.path?.[0] || "accueil";
  const human = true;
  el.innerHTML = `<div class="view-body">Chargement…</div>`;
  const body = el.querySelector(".view-body");
  const render = { accueil, decouvrir, cas_usage, portail_ia, tester, premiers_pas, copilote, contrat, recherche, glossaire, assistant, assistants, confiance, comparateur, besoins, rdv, animateur, formulaires, sources, pdf, historique, parametres }[section] || accueil;
  try { await render(body, human, ctx); }
  catch (e) { body.innerHTML = `<p class="warn">Erreur de la section (${esc(e.message)}).</p>`; }
}

/* ---------- Accueil ---------- */
async function accueil(body) {
  const idx = await kb.source("index_global");
  const stats = idx?.statistiques;
  // Parcours orientés terrain (n'affiche que les cibles implémentées → aucun lien mort).
  const parcours = PARCOURS.filter(p => IMPLEMENTED.has(p.href.split("/").pop() || "accueil"));
  const EXEMPLES = ["délai de carence", "exclusions décès", "rachat possible ?", "invalidité IPT", "fiscalité transmission"];
  const gotoSearch = q => { set({ axaQuery: (q || "").trim() }); location.hash = "#/recherche"; };
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
    <h3 class="day-h">Accès rapides</h3>
    <div class="grid">
      ${tile("📑", "Contrats", "#/contrat", `${stats?.contrats ?? 9} fiches contractuelles, A→Z`)}
      ${tile("⚖️", "Comparateur", "#/comparateur", "deux contrats côte à côte")}
      ${tile("📖", "Glossaire", "#/glossaire", "les termes AXA définis, sourcés")}
      ${tile("🧠", "Copilote de réponse", "#/copilote", "preuve + raisonnement, sourcé")}
      ${tile("🤖", "Utiliser avec une IA", "#/assistants", "un mini-prompt à coller dans ton IA")}
      ${tile("📄", "Notices PDF", "#/pdf", "la source qui fait foi")}
    </div>
    ${stats ? `<h3 class="day-h">Base de connaissances</h3>
    <div class="grid kpis">
      <div class="tile"><span class="tile-s">Contrats</span><span class="tile-l">${stats.contrats}</span><span class="tile-s">à jour</span></div>
      <div class="tile"><span class="tile-s">Faits contractuels</span><span class="tile-l">${stats.faits_uniques}</span><span class="tile-s">${Object.keys(stats.categories_source || {}).length} catégories</span></div>
      <div class="tile"><span class="tile-s">Garanties</span><span class="tile-l">${stats.categories_source?.garantie ?? "—"}</span><span class="tile-s">exclusions : ${stats.categories_source?.exclusion ?? "—"}</span></div>
      <div class="tile"><span class="tile-s">Points de vigilance</span><span class="tile-l">${stats.categories_source?.point_vigilance ?? "—"}</span><span class="tile-s">fiscalité : ${stats.categories_source?.fiscalite ?? "—"}</span></div>
    </div>` : ""}
    <p class="muted" style="margin-top:16px">Aucune donnée client stockée. <b>La notice PDF fait toujours foi.</b></p>`;
  body.querySelector("#acc_go").onclick = () => gotoSearch(body.querySelector("#acc_q").value);
  body.querySelector("#acc_q").addEventListener("keydown", e => { if (e.key === "Enter") gotoSearch(e.target.value); });
  body.querySelector("#acc_ex").addEventListener("click", e => { const b = e.target.closest("[data-ex]"); if (b) gotoSearch(b.dataset.ex); });
}
function tile(icon, label, href, sub) {
  return `<a class="tile" href="${href}"><span class="tile-i">${icon}</span><span class="tile-l">${esc(label)}</span><span class="tile-s">${esc(sub)}</span></a>`;
}

/* ---------- Premiers pas, FAQ, exemples, bonnes pratiques, limites ---------- */
const PP_EXEMPLES = ["délai de carence décès", "exclusions garantie décès", "rachat possible", "conditions d'âge à l'adhésion", "fiscalité transmission", "invalidité IPT"];
const PP_FAQ = [
  ["Qu'est-ce que Gabriel AXA ?", "Un assistant de recherche dans la base contractuelle AXA (garanties, exclusions, conditions, définitions), à partir de documents publics. Il fait gagner du temps ; il ne remplace pas la notice, qui fait toujours foi."],
  ["Est-ce que ça contient des données client ?", "Non. Aucune donnée client n'est stockée. Les documents embarqués proviennent de sources publiques (notices d'information, conditions générales)."],
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
      <li>En cas de doute entre deux contrats proches, utilisez le <a href="#/comparateur">comparateur</a>.</li>
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

    <h3 class="day-h">Origine des données</h3>
    <div class="card"><p class="card-b">Les informations proviennent exclusivement des <b>notices d'information et conditions
    générales</b> des produits AXA — des documents <b>publics</b>, remis à tout prospect. Aucune donnée client, aucune
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
const IA_INSTRUCTIONS_URL = IA_URL + "instructions-maitres.html";
const IA_TXT_REL = "../ia/instructions-maitres.txt"; // même origine (app et /ia servis sous /AXA/)
// Mini-prompt : le SEUL texte que le conseiller manipule. L'IA découvre et applique seule Gabriel AXA.
const MINI_PROMPT = `Utilise Gabriel AXA :
${IA_INSTRUCTIONS_URL}

Lis d'abord ces instructions destinées aux IA, applique-les, puis réponds.

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
    toujours la source avant d'utiliser une réponse avec un client. Ne saisissez <b>aucune donnée client nominative</b>.</div>

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
      ${tile("📄", "Sur quoi c'est fondé", "#/confiance", "documents publics uniquement (notices, CG). Aucune donnée client.")}
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
    ["⚖️", "Comparer deux contrats", "comparateur", ""],
    ["🧠", "Construire un premier raisonnement", "copilote", ""],
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
    ["⚖️", "Comparateur", "comparateur.html", "un sujet, tous les contrats côte à côte"],
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

/* ---------- Tester Gabriel AXA (phase de test conseillers) ---------- */
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
    <div class="warnbox">Rappel : la <b>notice PDF fait foi</b>. Pendant le test, vérifie toujours avant d'utiliser une réponse avec un client.</div>
    <h3 class="day-h">Par où commencer</h3>
    <div class="grid">
      ${tile("🔎", "Une vraie recherche", "#/recherche", "teste une question de RDV")}
      ${tile("⚖️", "Une comparaison", "#/comparateur", "deux contrats que tu proposes")}
      ${tile("🤖", "Avec ton IA", "#/assistants", "colle l'adresse et interroge")}
    </div>`;
}

/* ---------- Fiche contrat (écran métier conseiller) ---------- */
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
  // Rubrique repliable, avec poids visuel selon la priorité (prio) et une teinte de type (tone).
  const fsec = (label, items, { open = false, prio = false, tone = "" } = {}) => {
    const rendered = (items || []).map(fitem).filter(Boolean);
    if (!rendered.length) return "";
    return `<details class="fsec ${prio ? "prio" : ""} ${tone}"${open ? " open" : ""}><summary class="fsec-h"><span class="fsec-l">${esc(label)}</span><span class="fsec-n">${rendered.length}</span></summary><div class="fsec-body">${rendered.join("")}</div></details>`;
  };
  const pdfsFor = c => (c.pdfs || []).map(p => typeof p === "string" ? p : (p.nom_fichier || p.fichier || "")).filter(Boolean);
  const meta = c => FAMILLE_META[c.famille] || null;
  const confusablesFor = c => contrats.filter(x => x.famille === c.famille && x.nom !== c.nom).map(x => x.nom);
  const bullets = arr => `<ul class="hlist">${arr.map(x => `<li>${esc(x)}</li>`).join("")}</ul>`;

  const card = c => {
    const d = findDerived(c);
    const r = c.resume_neutre || "";
    const m = meta(c), conf = confusablesFor(c), pdfs = pdfsFor(c);
    // Notice principale du contrat (bouton d'en-tête) : 1er PDF connu.
    const mainNotice = (c.pdfs || []).map(p => pdfByName.get(String(p.nom_fichier || p.fichier || p).split("/").pop())).find(Boolean);
    // « À retenir » : comptes calculés à partir des données présentes (aucune invention).
    const n = (a) => (a || []).length;
    const chips = [
      [n(c.garanties_principales), "garantie", "garanties"], [n(c.exclusions_importantes), "exclusion", "exclusions"],
      [n(c.points_de_vigilance), "point de vigilance", "points de vigilance"], [n(d?.conditions_souscription), "condition", "conditions"],
      [n(d?.definitions), "définition", "définitions"],
    ].filter(x => x[0]).map(([k, s, p]) => `${k} ${k > 1 ? p : s}`);

    // Rubriques PRIORITAIRES (ouvertes, teintées par type).
    const priBlock = [
      fsec("Garanties principales", c.garanties_principales, { open: true, prio: true, tone: "t-ok" }),
      fsec("Exclusions importantes", c.exclusions_importantes, { open: true, prio: true, tone: "t-crit" }),
      d?.conditions_souscription?.length ? `<details class="fsec prio t-accent" open><summary class="fsec-h"><span class="fsec-l">Conditions de souscription</span><span class="fsec-n">${d.conditions_souscription.length}</span></summary><div class="fsec-body">${d.conditions_souscription.map(x => `<div class="fitem"><p class="fitem-b">${esc(x.texte)}</p>${sourceLink(x)}</div>`).join("")}</div></details>` : "",
      fsec("Points de vigilance", c.points_de_vigilance, { open: true, prio: true, tone: "t-warn" }),
    ].filter(Boolean).join("");

    // Rubriques SECONDAIRES (repliées, sobres).
    const enriched = (d?.faits || []).filter(f => f.declencheurs.length || f.plafonds.length || f.franchises.length);
    const secBlock = [
      fsec("Options", c.options, { tone: "t-neutral" }),
      fsec("Délais & franchises", c.delais_franchises, { tone: "t-neutral" }),
      fsec("Cotisations & prix", c.cotisations_prix, { tone: "t-neutral" }),
      fsec("Fiscalité", c.fiscalite, { tone: "t-neutral" }),
      enriched.length ? `<details class="fsec t-neutral"><summary class="fsec-h"><span class="fsec-l">Déclencheurs, plafonds &amp; franchises</span><span class="fsec-n">${enriched.length}</span></summary><div class="fsec-body">${enriched.map(f => `<div class="fitem"><div class="fitem-t">${esc(f.titre)}</div>${f.declencheurs.length ? `<p class="fitem-x"><span class="fitem-xl">Déclencheurs</span> ${esc(f.declencheurs.join(" · "))}</p>` : ""}${f.plafonds.length ? `<p class="fitem-x"><span class="fitem-xl">Plafonds</span> ${esc(f.plafonds.join(" · "))}</p>` : ""}${f.franchises.length ? `<p class="fitem-x"><span class="fitem-xl">Franchises</span> ${esc(f.franchises.join(" · "))}</p>` : ""}${sourceLink(f)}</div>`).join("")}</div></details>` : "",
      d?.definitions?.length ? `<details class="fsec t-neutral"><summary class="fsec-h"><span class="fsec-l">Définitions</span><span class="fsec-n">${d.definitions.length}</span></summary><div class="fsec-body">${d.definitions.map(x => `<div class="fitem"><div class="fitem-t">${esc(x.terme)}</div><p class="fitem-b">${esc(x.definition)}</p>${sourceLink(x)}</div>`).join("")}</div></details>` : "",
      fsec("Formules", c.formules, { tone: "t-neutral" }),
      m ? `<details class="fsec t-neutral"><summary class="fsec-h"><span class="fsec-l">Repères conseiller</span><span class="fsec-tag">méthodo · non contractuel</span></summary><div class="fsec-body">
        <div class="fitem"><div class="fitem-t">Cible</div><p class="fitem-b">${esc(m.cible)}</p></div>
        <div class="fitem"><div class="fitem-t">Questions à poser</div>${bullets(m.questions)}</div>
        <div class="fitem"><div class="fitem-t">Cas d'usage</div>${bullets(m.cas_usage)}</div>
        <div class="fitem"><div class="fitem-t">Erreurs fréquentes</div>${bullets([...m.erreurs, ...ERREURS_TRANSVERSES])}</div></div></details>` : "",
      conf.length ? `<details class="fsec t-neutral"><summary class="fsec-h"><span class="fsec-l">À ne pas confondre</span><span class="fsec-n">${conf.length}</span></summary><div class="fsec-body"><div class="fitem"><p class="fitem-b">Même famille (${esc(c.famille)}) : ${esc(conf.join(", "))}. Vérifier les garanties/exclusions propres à chacun.</p></div></div></details>` : "",
      pdfs.length ? `<details class="fsec t-neutral"><summary class="fsec-h"><span class="fsec-l">Documents PDF liés</span><span class="fsec-n">${pdfs.length}</span></summary><div class="fsec-body"><div class="fitem">${bullets(pdfs)}<p class="muted" style="margin-top:6px"><a href="#/pdf">→ ouvrir les notices contractuelles</a></p></div></div></details>` : "",
    ].filter(Boolean).join("");

    return `<article class="card fiche">
      <header class="fiche-head">
        <div class="fiche-id">
          <h2 class="fiche-name">${esc(c.nom)}</h2>
          ${c.type_contrat ? `<div class="fiche-type">${esc(c.type_contrat)}</div>` : ""}
          <div class="fiche-badges">${c.famille ? `<span class="fbadge fam">${esc(c.famille)}</span>` : ""}${c.date_document ? `<span class="fbadge">${esc(c.date_document)}</span>` : ""}</div>
        </div>
        <div class="fiche-actions">${mainNotice ? `<a class="btn gold" href="${esc(mainNotice)}" target="_blank" rel="noopener">📄 Notice</a>` : ""}<button class="btn ghost" data-print>Imprimer</button></div>
      </header>
      ${c.assureur ? `<div class="fiche-assureur"><span class="fiche-assureur-l">Assureur</span> ${esc(c.assureur)}</div>` : ""}
      ${c._minimal ? `<div class="warnbox">Données limitées pour ce contrat — se référer à la notice PDF. Fiche minimale.</div>` : ""}
      ${(r || chips.length) ? `<section class="fiche-retenir"><div class="fiche-retenir-h">À retenir</div>
        ${chips.length ? `<div class="fiche-chips">${chips.map(ch => `<span class="fchip">${esc(ch)}</span>`).join("")}</div>` : ""}
        ${r ? (r.length > 320 ? `<details class="fold"><summary class="fiche-resume">${esc(r.slice(0, 320))}…</summary><p class="fiche-resume" style="margin-top:6px">${esc(r.slice(320))}</p></details>` : `<p class="fiche-resume">${esc(r)}</p>`) : ""}</section>` : ""}
      ${priBlock}
      ${secBlock ? `<div class="fiche-sep">Détails complémentaires</div>${secBlock}` : ""}
      <p class="fiche-foot">Repères indicatifs — pour le cas précis, la notice PDF fait foi. Aucune réponse client sans vérifier la source.</p>
    </article>`;
  };
  function render(q = "") {
    const ql = q.trim().toLowerCase();
    let list = contrats;
    if (fam !== "all") list = list.filter(c => c.famille === fam);
    if (ql) list = list.filter(c => JSON.stringify(c).toLowerCase().includes(ql));
    // Tuile compacte du sélecteur (usage rapide : trouver le contrat sans dérouler 8 fiches).
    const tileCard = c => `<a class="tile contract-pick" data-open="${esc(c.nom)}"><span class="tile-l">${esc(c.nom)}</span><span class="tile-s">${esc(c.famille || "")}</span><span class="tile-s go">ouvrir la fiche →</span></a>`;
    // Mode : recherche/filtre actif → fiches filtrées ; sinon sélection → fiche unique ; sinon sélecteur.
    let content;
    if (ql || fam !== "all") content = list.map(card).join("") || "<p class='muted'>Aucun contrat.</p>";
    else if (selected) { const c = contrats.find(x => x.nom === selected); content = `<p class="crumb"><a href="#" id="axa_back">← Tous les contrats</a></p>` + (c ? card(c) : ""); }
    else content = `<p class="muted">Choisis un contrat pour ouvrir sa fiche (garanties, exclusions, définitions, conditions, sources PDF). Ou filtre/recherche ci-dessus.</p><div class="grid">${contrats.map(tileCard).join("")}</div>`;
    body.innerHTML = `<div class="view-head" style="margin-top:0"><input class="filter" id="axaq" placeholder="🔎 rechercher un contrat…" aria-label="Filtrer les contrats" value="${esc(q)}"></div>
      <div class="filters">${["all", ...familles].map(f => `<button class="chip ${fam === f ? "on" : ""}" data-f="${esc(f)}">${f === "all" ? "toutes" : esc(f)}</button>`).join("")}</div>
      ${content}`;
    body.querySelectorAll("[data-f]").forEach(b => b.onclick = () => { fam = b.dataset.f; selected = null; render(body.querySelector("#axaq").value); });
    body.querySelectorAll("[data-open]").forEach(a => a.onclick = e => { e.preventDefault(); selected = a.dataset.open; render(""); });
    body.querySelector("#axa_back")?.addEventListener("click", e => { e.preventDefault(); selected = null; render(""); });
    body.querySelectorAll("[data-print]").forEach(b => b.onclick = () => printTarget(b.closest(".card")));
    const inp = body.querySelector("#axaq");
    let t; inp.addEventListener("input", e => { clearTimeout(t); t = setTimeout(() => { const v = e.target.value; selected = null; render(v); body.querySelector("#axaq").focus(); const i2 = body.querySelector("#axaq"); i2.setSelectionRange(v.length, v.length); }, 250); });
  }
  render();
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
    const carte = (h, tete) => `
      <article class="card ${tete ? "cop-base" : ""}"><div class="card-h">${tete ? `<span class="pill integrated">meilleur résultat</span>` : ""}
        <span class="pill">${esc(h.type)}</span><strong>${esc(h.label || "(sans titre)")}</strong><span class="muted">${esc(h.contrat || "")}</span></div>
      <p class="card-b">${highlight(sansTitre(h.text, h.label), terms)}</p>
      <p class="muted">${tete ? `<span class="muted">celui qui recoupe le mieux tes termes — vérifie la notice (fait foi) · </span>` : ""}<a href="${h.ref}">→ ouvrir la fiche</a></p></article>`;
    res.innerHTML = shown.length ? `<p class="muted">${shown.length} résultat(s)${active !== "all" ? " · filtre : " + esc(FILTERS.find(f => f.id === active).label) : ""}</p>`
      + shown.map((h, i) => carte(h, i === 0)).join("")
      : "<p class='muted'>Aucun résultat pour ce filtre.</p>";
  }
  let t;
  async function run(q) {
    q = (q || "").trim();
    if (q.length < 2) { lastHits = []; filtersEl.innerHTML = ""; res.innerHTML = "<p class='muted'>Tape au moins 2 caractères.</p>"; return; }
    res.innerHTML = "<p class='muted'>Recherche…</p>";
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
      ${comp.cites.length > 1 ? "<br><span class='muted'>Plusieurs contrats cités : pense au comparateur (ci-dessous).</span>" : ""}</p></div>`];

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
    const deux = groupes.slice(0, 2).map(g => g.contrat);
    h.push(`<h3 class="day-h">⑤ Prochaine action</h3><div class="card"><div class="btns">
      ${contratPrincipal ? `<a class="btn gold" href="#/contrat/${slugc(contratPrincipal)}">📑 Ouvrir la fiche ${esc(contratPrincipal)}</a>` : ""}
      ${deux.length === 2 ? `<a class="btn ghost" href="#/comparateur/${slugc(deux[0])}/${slugc(deux[1])}">⚖ Comparer ${esc(deux[0])} ↔ ${esc(deux[1])}</a>` : ""}
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

/* ---------- Assistant IA (cadré : aucun appel API en V1) ---------- */
async function assistant(body) {
  const prompt = await kb.source("prompt_conseiller");
  const modeEmploi = await kb.source("mode_emploi_ia");
  body.innerHTML = `
    <p class="lead">L'assistant IA n'est <b>pas encore connecté</b> (aucun appel API — voir ADR-004).
    En attendant, ce poste de travail prépare tout pour tes assistants externes :</p>
    ${modeEmploi ? `<div class="card"><h3 style="margin:0 0 8px">Mode d'emploi IA — double master (Pack A stable / Pack B matrices)</h3>
      <div class="btns"><button class="btn gold" id="me_copy">📋 Copier le mode d'emploi</button><span class="muted" id="me_st"></span></div>
      <details class="acc"><summary class="muted">Lire le mode d'emploi</summary><div class="md" id="me_md">Rendu…</div></details>
      <p class="muted">Règle d'or : Pack A = preuve contractuelle · Pack B = raisonnement (jamais cité seul comme preuve) ·
      réponse client = toujours vérifiée contrat/PDF/source officielle.</p></div>` : ""}
    <div class="card"><h3 style="margin:0 0 8px">Mode d'emploi IA — prompt conseiller officiel</h3>
      ${prompt ? `<div class="btns"><button class="btn gold" id="as_copy">📋 Copier le prompt</button><span class="muted" id="as_st"></span></div>
      <details class="acc"><summary class="muted">Aperçu</summary><div class="md" id="as_md">Rendu…</div></details>`
      : `<p class="muted">Prompt conseiller introuvable (rôle prompt_conseiller du manifeste).</p>`}
    </div>
    <div class="grid">
      ${tile("📄", "Notices contractuelles", "#/pdf", "la source qui fait foi")}
      ${tile("🧠", "Copilote de réponse", "#/copilote", "preuve + raisonnement, sourcé")}
    </div>
    <p class="muted">L'assistant conversationnel n'est pas branché dans Gabriel AXA (aucun appel API) :
    l'application prépare tout pour ChatGPT / Claude et garde la notice PDF comme référence qui fait foi.</p>`;
  body.querySelector("#as_copy")?.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(prompt); body.querySelector("#as_st").textContent = "Copié."; }
    catch { body.querySelector("#as_st").textContent = "Copie refusée — ouvre l'aperçu."; }
  });
  const meMd = body.querySelector("#me_md");
  if (meMd && modeEmploi) renderMarkdown(modeEmploi).then(h => { meMd.innerHTML = h; });
  const asMd = body.querySelector("#as_md");
  if (asMd && prompt) renderMarkdown(prompt).then(h => { asMd.innerHTML = h; });
  body.querySelector("#me_copy")?.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(modeEmploi); body.querySelector("#me_st").textContent = "Copié."; }
    catch { body.querySelector("#me_st").textContent = "Copie refusée — ouvre l'aperçu."; }
  });
}

/* ---------- Comparateur (deux contrats côte à côte + tableau global) ---------- */
const COMPARE_SECTIONS = [["Garanties principales", "garanties_principales"], ["Exclusions importantes", "exclusions_importantes"],
  ["Options", "options"], ["Points de vigilance", "points_de_vigilance"], ["Fiscalité", "fiscalite"]];
async function comparateur(body, human, ctx) {
  const resume = await kb.source("contrats_resume_humain");
  const t = await kb.source("comparatif");
  const contrats = resume?.contrats || [];
  if (!contrats.length) { body.innerHTML = `<p class="warn">Données de comparaison indisponibles.</p>`; return; }
  if (!human) { body.innerHTML = `<pre>${esc(JSON.stringify({ comparatif: t, contrats: contrats.map(c => c.nom) }, null, 2).slice(0, 60000))}</pre>`; return; }
  const titles = (c, key) => (c[key] || []).map(f => typeof f === "string" ? f : (f.titre && !f.titre.startsWith("_") ? f.titre : "")).filter(Boolean);
  const opt = (sel, c) => `<option value="${esc(c.nom)}" ${sel === c.nom ? "selected" : ""}>${esc(c.nom)}</option>`;
  let a = contrats[0].nom, b = contrats[1] ? contrats[1].nom : contrats[0].nom;
  // Lien profond #/comparateur/<slugA>/<slugB> : le copilote et les fiches peuvent pré-remplir la comparaison.
  const slugc = s => String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]/g, "");
  const parSlug = w => (contrats.find(c => slugc(c.nom) === w) || contrats.find(c => slugc(c.nom).startsWith(w)))?.nom;
  if (ctx?.path?.[0]) a = parSlug(slugc(decodeURIComponent(ctx.path[0]))) || a;
  if (ctx?.path?.[1]) b = parSlug(slugc(decodeURIComponent(ctx.path[1]))) || b;

  function renderCompare() {
    const cA = contrats.find(c => c.nom === a), cB = contrats.find(c => c.nom === b);
    const sameFam = cA.famille === cB.famille;
    const sideBySide = COMPARE_SECTIONS.map(([label, key]) => {
      const ta = titles(cA, key), tb = titles(cB, key);
      if (!ta.length && !tb.length) return "";
      const setA = new Set(ta.map(x => x.toLowerCase())), setB = new Set(tb.map(x => x.toLowerCase()));
      const li = (arr, other) => arr.map(x => `<li class="${other.has(x.toLowerCase()) ? "" : "diff"}">${esc(x)}</li>`).join("") || "<li class='muted'>—</li>";
      return `<tr><td style="text-align:left"><b>${esc(label)}</b></td>
        <td style="text-align:left;white-space:normal"><ul class="hlist">${li(ta, setB)}</ul></td>
        <td style="text-align:left;white-space:normal"><ul class="hlist">${li(tb, setA)}</ul></td></tr>`;
    }).join("");
    body.querySelector("#cmp_out").innerHTML = `
      ${sameFam ? `<div class="warnbox">⚠ <b>${esc(cA.famille)}</b> — même famille : contrats <b>à ne pas confondre</b>. Vérifier garanties et exclusions propres à chacun.</div>`
        : `<p class="muted">Familles différentes : ${esc(cA.famille)} vs ${esc(cB.famille)} — usages distincts.</p>`}
      <p class="muted">Faits contractuels <b>Pack A (preuve, sourcée au contrat/PDF)</b>. En <span class="diff-lg">orange</span> : présent d'un seul côté (différence). Le raisonnement Pack B n'est jamais une preuve.</p>
      <div class="tblwrap"><table class="tbl"><thead><tr><th>Thème</th><th>${esc(cA.nom)}</th><th>${esc(cB.nom)}</th></tr></thead><tbody>${sideBySide}</tbody></table></div>`;
  }
  body.innerHTML = `<p class="lead">Compare deux contrats côte à côte. Les faits viennent du Pack A (preuve) ; la notice PDF fait foi.</p>
    <div class="row3"><label>Contrat A<select id="cmp_a">${contrats.map(c => opt(a, c)).join("")}</select></label>
      <label>Contrat B<select id="cmp_b">${contrats.map(c => opt(b, c)).join("")}</select></label></div>
    <div class="btns">${printBtnHtml("cmp_print")}</div>
    <div id="cmp_out"></div>
    ${t?.lignes ? `<details class="acc"><summary>Tableau global (nombre de faits par thème)</summary>
      <div class="tblwrap"><table class="tbl"><thead><tr>${t.colonnes.map(c => `<th>${esc(c.replace(/_/g, " "))}</th>`).join("")}</tr></thead>
      <tbody>${t.lignes.map(l => `<tr>${t.colonnes.map((c, i) => `<td ${i === 0 ? 'style="text-align:left;white-space:normal"' : ""}>${esc(l[c] ?? "—")}</td>`).join("")}</tr>`).join("")}</tbody></table></div></details>` : ""}`;
  body.querySelector("#cmp_a").onchange = e => { a = e.target.value; renderCompare(); };
  body.querySelector("#cmp_b").onchange = e => { b = e.target.value; renderCompare(); };
  body.querySelector("#cmp_print").onclick = () => printTarget(body.querySelector("#cmp_out"));
  renderCompare();
}

/* ---------- Analyse des besoins (parcours guidé — pistes, jamais de reco définitive) ---------- */
function bullets(arr) { return `<ul class="hlist">${arr.map(x => `<li>${esc(x)}</li>`).join("")}</ul>`; }
async function besoins(body) {
  const resume = await kb.source("contrats_resume_humain");
  const contrats = resume?.contrats || [];
  body.innerHTML = `
    <p class="lead">Parcours guidé : renseigne la situation, l'outil propose des <b>pistes</b> à explorer.
    <b>Ce n'est pas une recommandation :</b> le conseiller décide et vérifie au contrat.</p>
    <div class="card"><h3 style="margin:0 0 8px">Situation du client</h3>
      <div class="row3">
        <label>Âge<input id="bz_age" type="number" min="0" max="120" placeholder="ex. 35"></label>
        <label>Situation familiale<select id="bz_fam"><option value="">—</option><option>Célibataire</option><option>En couple</option><option>Avec enfants</option><option>Famille recomposée</option></select></label>
        <label>Profession<select id="bz_pro"><option value="">—</option><option>Salarié</option><option>Indépendant / TNS</option><option>Fonctionnaire</option><option>Sans activité</option><option>Retraité</option></select></label>
      </div>
      <fieldset class="perms"><legend>Objectifs (un ou plusieurs)</legend>
        ${OBJECTIFS.map((o, i) => `<label class="inline"><input type="checkbox" data-obj="${i}"> ${esc(o.label)}</label>`).join("")}</fieldset>
      <div class="row3">
        <label>Budget mensuel<select id="bz_budget"><option value="">—</option><option>&lt; 50 €</option><option>50–150 €</option><option>&gt; 150 €</option></select></label>
        <label>Horizon<select id="bz_hor"><option value="">—</option><option>Court terme</option><option>Moyen terme</option><option>Long terme</option></select></label>
        <label>Contraintes<input id="bz_contr" placeholder="ex. santé, budget serré"></label>
      </div>
      <div class="btns"><button class="btn gold" id="bz_go">🎯 Proposer des pistes</button></div>
      <div id="bz_out"></div></div>`;
  body.querySelector("#bz_go").onclick = () => {
    const objs = [...body.querySelectorAll("[data-obj]:checked")].map(c => OBJECTIFS[Number(c.dataset.obj)]);
    const out = body.querySelector("#bz_out");
    if (!objs.length) { out.innerHTML = "<p class='muted'>Coche au moins un objectif.</p>"; return; }
    const familles = [...new Set(objs.map(o => o.famille))];
    const pistes = contrats.filter(c => familles.includes(c.famille));
    const questions = [...new Set(familles.flatMap(f => (FAMILLE_META[f]?.questions) || []))];
    const age = body.querySelector("#bz_age").value, pro = body.querySelector("#bz_pro").value;
    const notes = [];
    if (pro === "Indépendant / TNS") notes.push("Statut TNS : vérifier les dispositifs dédiés (Madelin/PER) et le questionnaire médical.");
    if (age && Number(age) >= 60) notes.push("Âge ≥ 60 ans : attention aux conditions d'âge et limites de souscription selon les contrats.");
    out.innerHTML = `
      <h3 class="day-h">Pistes à explorer (à valider par le conseiller)</h3>
      <p class="muted">Familles rapprochées : ${familles.map(esc).join(", ")}</p>
      ${pistes.length ? bullets(pistes.map(c => `${c.nom} (${c.famille})`)) : "<p class='muted'>Aucun contrat de ces familles dans la base — élargir via la recherche globale.</p>"}
      <h3 class="day-h">Questions complémentaires à poser</h3>${bullets(questions)}
      ${notes.length ? `<h3 class="day-h">Points d'attention</h3>${bullets(notes)}` : ""}
      <div class="warnbox">⚖️ Ces pistes ne sont pas une recommandation. Vérifier garanties, exclusions et conditions
      dans <a href="#/contrat">la fiche contrat</a> et la notice PDF avant toute proposition. Aucun calcul fiscal définitif sans données complètes.</div>
      <div class="btns"><button class="btn" id="bz_rdv">🗓 Préparer un RDV avec ces éléments</button></div>`;
    body.querySelector("#bz_rdv").onclick = () => { location.hash = "#/rdv"; };
  };
}

/* ---------- Préparation RDV (fiche générée, exportable) ---------- */
async function rdv(body) {
  const resume = await kb.source("contrats_resume_humain");
  const contrats = resume?.contrats || [];
  body.innerHTML = `
    <p class="lead"><span class="qbadge q-beta">BÊTA</span> Aide à la préparation de rendez-vous — checklist prudente et sourçable. Aucune donnée client n'est stockée.</p>
    <div class="card"><h3 style="margin:0 0 8px">Contexte du rendez-vous</h3>
      <div class="row3">
        <label>Objectif principal<select id="rv_obj"><option value="">—</option>${OBJECTIFS.map(o => `<option value="${esc(o.famille)}">${esc(o.label)}</option>`).join("")}</select></label>
        <label>Profil client<input id="rv_profil" placeholder="ex. 40 ans, marié, 2 enfants, salarié"></label>
        <label>Contrat pressenti<select id="rv_contrat"><option value="">— (optionnel)</option>${contrats.map(c => `<option>${esc(c.nom)}</option>`).join("")}</select></label>
      </div>
      <div class="btns"><button class="btn gold" id="rv_go">🗓 Générer la fiche</button></div></div>
    <div id="rv_out"></div>`;
  body.querySelector("#rv_go").onclick = () => {
    const fam = body.querySelector("#rv_obj").value;
    const profil = body.querySelector("#rv_profil").value.trim();
    const contratNom = body.querySelector("#rv_contrat").value;
    const c = contrats.find(x => x.nom === contratNom);
    const meta = FAMILLE_META[fam];
    const contratsVerif = contratNom ? [contratNom] : contrats.filter(x => x.famille === fam).map(x => x.nom);
    const vigilance = c ? (c.points_de_vigilance || []).map(f => f.titre || f.resume_humain || f).filter(x => typeof x === "string" && !x.startsWith("_")).slice(0, 6) : [];
    const fiche = {
      titre: `Préparation RDV${profil ? " — " + profil : ""}`,
      objectifs: ["Comprendre le besoin réel du client", fam ? `Explorer la piste : ${OBJECTIFS.find(o => o.famille === fam)?.label || fam}` : "Qualifier l'objectif"],
      questions: meta?.questions || ["Situation, objectif, budget, horizon, contrats existants ?"],
      vigilance: vigilance.length ? vigilance : (meta?.erreurs || []),
      contrats_verifier: contratsVerif,
      sources: ["Notice(s) PDF du/des contrat(s) pressenti(s)", "Fiche contrat AXA Conseiller", "Sources officielles pour toute règle publique"],
      formulations: ["« Sous réserve de vérification au contrat… »", "« La notice précise que… (page X) »", "« Je reviens vers vous après vérification »"],
      objections: ["« C'est trop cher » → clarifier le besoin et les garanties réellement utiles", "« J'ai déjà un contrat » → comparer sans dénigrer, vérifier les doublons/manques"],
      etapes: ["Récapituler les besoins validés", "Remettre les documents officiels", "Fixer la prochaine étape"],
    };
    const sec = (t, arr) => `<h3 class="day-h">${t}</h3>${bullets(arr)}`;
    body.querySelector("#rv_out").innerHTML = `
      <div class="card" id="rv_card"><div class="card-h"><strong>${esc(fiche.titre)}</strong>
        <button class="btn ghost" id="rv_copy" style="min-height:30px;padding:0 10px">📋 Copier</button>
        ${printBtnHtml("rv_print")}</div>
      ${sec("🎯 Objectifs du RDV", fiche.objectifs)}
      ${sec("❓ Questions à poser", fiche.questions)}
      ${sec("⚠ Points de vigilance", fiche.vigilance)}
      ${sec("📑 Contrats à vérifier", fiche.contrats_verifier)}
      ${sec("📚 Sources à ouvrir", fiche.sources)}
      ${sec("🗣 Formulations prudentes", fiche.formulations)}
      ${sec("💬 Objections possibles — exemples à adapter", fiche.objections)}
      ${sec("➡ Prochaines étapes — trame type", fiche.etapes)}
      <div class="warnbox">⚖️ Fiche d'aide à la préparation. La réponse client s'appuie sur le contrat / la notice PDF / une source officielle. Aucun conseil définitif automatisé.</div></div>`;
    const asText = [fiche.titre, "", "OBJECTIFS", ...fiche.objectifs.map(x => "- " + x), "", "QUESTIONS", ...fiche.questions.map(x => "- " + x),
      "", "VIGILANCE", ...fiche.vigilance.map(x => "- " + x), "", "CONTRATS À VÉRIFIER", ...fiche.contrats_verifier.map(x => "- " + x),
      "", "SOURCES", ...fiche.sources.map(x => "- " + x), "", "FORMULATIONS", ...fiche.formulations.map(x => "- " + x),
      "", "OBJECTIONS", ...fiche.objections.map(x => "- " + x), "", "ÉTAPES", ...fiche.etapes.map(x => "- " + x),
      "", "Rappel : la notice PDF fait foi ; aucun conseil définitif automatisé."].join("\n");
    bindCopy(body.querySelector("#rv_copy"), () => asText);
    body.querySelector("#rv_print").onclick = () => printTarget(body.querySelector("#rv_card"));
  };
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

/* ---------- Formulaires ---------- */
async function formulaires(body) {
  const m = await kb.manifest();
  const schema = await kb.source("formulaires_schema");
  body.innerHTML = `
    <p class="lead">Recueil d'informations client. <b>Aucune donnée client n'est stockée dans le dépôt</b> —
    les formulaires exportent en local uniquement.</p>
    <div class="grid">${(m.formulaires_pages || []).map(f =>
      `<a class="tile" href="../${esc(f.path)}" target="_blank" rel="noopener"><span class="tile-i">📝</span><span class="tile-l">${esc(f.label)}</span><span class="tile-s">ouvrir dans un nouvel onglet</span></a>`).join("")}</div>
    ${(() => { // schémas : tableau OU objet {id: schema} selon les versions du master
      const raw = schema?.formulaires;
      const list = Array.isArray(raw) ? raw : (raw && typeof raw === "object" ? Object.entries(raw).map(([id, v]) => ({ id, ...(typeof v === "object" ? v : {}) })) : []);
      return list.length ? `<h3 class="day-h">Schémas disponibles</h3><ul class="hlist">${list.map(f =>
        `<li><b>${esc(f.nom || f.label || f.id)}</b>${f.description ? " — " + esc(f.description) : ""}${f.champs || f.sections ? ` <span class="muted">(${(f.champs || f.sections).length ?? ""} champs)</span>` : ""}</li>`).join("")}</ul>` : "";
    })()}`;
}

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
