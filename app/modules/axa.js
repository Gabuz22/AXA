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
const SECTIONS = [
  ["accueil", "🏠 Accueil"], ["premiers_pas", "🧭 Premiers pas"], ["copilote", "🧠 Copilote réponse"], ["contrat", "📑 Recherche contrat"],
  ["recherche", "🔎 Recherche globale"], ["glossaire", "📖 Glossaire"], ["comparateur", "⚖️ Comparateur"], ["besoins", "🎯 Analyse des besoins"],
  ["rdv", "🗓 Préparation RDV"], ["animateur", "🎓 Animateur"],
  ["assistant", "🤖 Assistant IA"], ["assistants", "💬 Avec ChatGPT / Claude"],
  ["formulaires", "📝 Formulaires"], ["sources", "📚 Sources officielles"], ["pdf", "📄 PDF contractuels"],
  ["historique", "🕘 Historique"], ["parametres", "⚙ Paramètres"],
];

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
  const render = { accueil, premiers_pas, copilote, contrat, recherche, glossaire, assistant, assistants, comparateur, besoins, rdv, animateur, formulaires, sources, pdf, historique, parametres }[section] || accueil;
  try { await render(body, human); }
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
    </section>
    <h3 class="day-h">Accès rapides</h3>
    <div class="grid">
      ${tile("🧠", "Copilote de réponse", "#/copilote", "preuve (Pack A) + raisonnement (Pack B)")}
      ${tile("📑", "Contrats", "#/contrat", `${stats?.contrats ?? 9} fiches, A→Z`)}
      ${tile("⚖️", "Comparateur", "#/comparateur", "deux contrats côte à côte")}
      ${tile("📄", "Notices PDF", "#/pdf", "la source qui fait foi")}
      ${tile("🤖", "Utiliser avec une IA", "#/assistants", "Pack A / Pack B pour ChatGPT · Claude")}
      ${tile("🧭", "Premiers pas", "#/premiers_pas", "prise en main en 2 minutes")}
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

/* ---------- Premiers pas (tutoriel) ---------- */
async function premiers_pas(body) {
  body.innerHTML = `
    <p class="lead">Nouveau sur AXA Conseiller ? Ce guide explique l'essentiel en 3 minutes.
    <a href="#/assistants">→ Utiliser AXA avec ChatGPT / Claude</a></p>
    <div class="card"><div class="md" id="tuto_md">Rendu…</div></div>
    <div class="grid">
      ${tile("📑", "Ouvrir une fiche contrat", "#/contrat", "commencer par là")}
      ${tile("🗓", "Préparer un rendez-vous", "#/rdv", "fiche prudente")}
      ${tile("💬", "Prompts ChatGPT / Claude", "#/assistants", "prêts à copier")}
    </div>`;
  const md = body.querySelector("#tuto_md");
  renderMarkdown(TUTORIEL).then(h => { md.innerHTML = h; }).catch(() => { md.textContent = TUTORIEL; });
}

/* ---------- Utiliser AXA avec ChatGPT / Claude (prompts copiables) ---------- */
async function assistants(body) {
  const manifest = await kb.manifest();
  const masters = ["master_pack_a", "master_pack_b", "mode_emploi_ia"].filter(r => manifest.sources?.[r]);
  body.innerHTML = `
    <p class="lead">L'app ne branche aucune IA. Pour te faire assister, tu utilises <b>ChatGPT ou Claude</b>
    en leur fournissant la base de connaissances, puis un prompt cadré. La preuve reste le contrat / PDF.</p>

    <div class="card"><h3 style="margin:0 0 8px">1. Quels fichiers fournir à l'assistant</h3>
      <ul class="hlist">
        <li><b>Pack A stable</b> — la référence contractuelle (fait foi).</li>
        <li><b>Pack B matrices</b> — uniquement pour le raisonnement complexe (jamais une preuve).</li>
        <li><b>Mode d'emploi IA</b> — explique le routage Pack A / Pack B.</li>
      </ul>
      <div class="btns">${masters.map(r => `<a class="btn ghost" href="${esc(kb.fileUrl(manifest.sources[r].path))}" target="_blank" rel="noopener">⬇ ${esc(r.replace(/_/g, " "))}</a>`).join("")}
        <a class="btn" href="#/assistants">📦 Générer un pack de contexte</a></div>
      <p class="muted">Astuce : pour une question ciblée, un extrait de la fiche contrat suffit souvent (plus léger qu'un master entier).</p></div>

    <div class="card"><h3 style="margin:0 0 8px">2. Comment poser une question (méthode)</h3>
      <ul class="hlist">
        <li>Colle d'abord le <b>prompt de base</b> (ci-dessous), puis pose ta question.</li>
        <li>Demande toujours une <b>réponse sourcée</b> (« cite la notice PDF et la page »).</li>
        <li>Pour comparer : demande de <b>séparer Pack A (preuve) et Pack B (raisonnement)</b>.</li>
        <li><b>Refuse</b> toute réponse sans source, tout calcul fiscal définitif, toute matrice présentée comme preuve.</li>
        <li>Ne <b>sur-interprète pas Pack B</b> : c'est une aide au raisonnement, pas une garantie contractuelle.</li>
      </ul></div>

    <h3 class="day-h">3. Prompts prêts à copier</h3>
    <div class="btns"><button class="btn" id="pr_all">📋 Copier les 7 prompts</button><span class="muted" id="pr_allst"></span></div>
    ${PROMPTS.map(p => `<article class="card">
      <div class="card-h"><strong>${esc(p.titre)}</strong><span class="muted">${esc(p.description)}</span>
        <button class="btn ghost" data-copy="${esc(p.id)}" style="min-height:30px;padding:0 10px">📋 Copier</button></div>
      <pre class="prompt" style="white-space:pre-wrap;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:10px;font-size:12.5px">${esc(p.texte)}</pre>
    </article>`).join("")}
    <p class="muted">Rappels : Pack A = preuve · Pack B = raisonnement, jamais une preuve · réponse client =
    contrat / PDF / source officielle · aucun conseil définitif automatisé.</p>`;

  PROMPTS.forEach(p => bindCopy(body.querySelector(`[data-copy="${p.id}"]`), () => p.texte));
  bindCopy(body.querySelector("#pr_all"), () => PROMPTS.map(p => `### ${p.titre}\n${p.texte}`).join("\n\n"), "✓ 7 prompts copiés");
}

/* ---------- Recherche contrat (vue conseiller par contrat) ---------- */
const CONTRACT_SECTIONS = [
  ["Garanties principales", "garanties_principales"], ["Exclusions importantes", "exclusions_importantes"],
  ["Options", "options"], ["Cotisations & prix", "cotisations_prix"], ["Délais & franchises", "delais_franchises"],
  ["Fiscalité", "fiscalite"], ["Points de vigilance", "points_de_vigilance"], ["Formules", "formules"],
];
// Sections ouvertes par défaut dans la fiche (quick win 2) : les 2 gestes les plus fréquents.
const OPEN_BY_DEFAULT = new Set(["garanties_principales", "exclusions_importantes"]);
async function contrat(body, human) {
  const resume = await kb.source("contrats_resume_humain");
  const contrats = resume?.contrats || [];
  if (!contrats.length) { body.innerHTML = `<p class="warn">Résumé humain des contrats indisponible (voir manifeste).</p>`; return; }
  if (!human) { body.innerHTML = `<pre>${esc(JSON.stringify(resume, null, 2).slice(0, 200000))}</pre>`; return; }
  const familles = [...new Set(contrats.map(c => c.famille).filter(Boolean))].sort();
  let fam = "all", selected = null; // selected = nom du contrat ouvert (null = sélecteur)
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
  const sourceLink = f => {
    const s = f && typeof f === "object" ? f.source : null;
    if (!s || !s.document_source) return "";
    const base = String(s.document_source).split("/").pop();
    const url = pdfByName.get(base) || ("../data/AXA/00_PACKAGE_ACTIF/Contrats-AXA/" + s.document_source);
    const href = url + (s.page ? "#page=" + s.page : "");
    const titre = "Ouvrir la notice" + (s.page ? " page " + s.page : "") + (s.section ? " — " + s.section : "");
    return ` <a class="src-link" href="${esc(href)}" target="_blank" rel="noopener" title="${esc(titre)}">📄 notice${s.page ? " p." + s.page : ""}</a>`;
  };
  const factLine = f => {
    if (typeof f === "string") return isEmpty(f) ? "" : `<li>${esc(f)}</li>`;
    const t = f.titre && !f.titre.startsWith("_") ? f.titre : "", x = f.resume_humain || f.texte || "";
    return isEmpty(t) && isEmpty(x) ? "" : `<li>${t ? `<b>${esc(t)}</b>` : ""}${t && x ? " — " : ""}${esc(x)}${sourceLink(f)}</li>`;
  };
  const pdfsFor = c => (c.pdfs || []).map(p => typeof p === "string" ? p : (p.nom_fichier || p.fichier || "")).filter(Boolean);
  const meta = c => FAMILLE_META[c.famille] || null;
  const confusablesFor = c => contrats.filter(x => x.famille === c.famille && x.nom !== c.nom).map(x => x.nom);
  const bullets = arr => `<ul class="hlist">${arr.map(x => `<li>${esc(x)}</li>`).join("")}</ul>`;

  const card = c => {
    const secs = CONTRACT_SECTIONS.map(([label, key]) => {
      const items = (c[key] || []).map(factLine).filter(Boolean);
      return items.length ? `<details class="acc"${OPEN_BY_DEFAULT.has(key) ? " open" : ""}><summary>${esc(label)} <span class="muted">(${items.length})</span></summary><ul class="hlist">${items.join("")}</ul></details>` : "";
    }).join("");
    const r = c.resume_neutre || "";
    const m = meta(c), conf = confusablesFor(c), pdfs = pdfsFor(c);
    // Repères conseiller méthodologiques (génériques par famille) — clairement étiquetés.
    const reperes = m ? `<details class="acc"><summary>🧭 Repères conseiller <span class="muted">(méthodologiques — vérifier au contrat)</span></summary>
      <p class="card-x"><span class="xlabel">Cible</span> ${esc(m.cible)}</p>
      <div class="card-x"><span class="xlabel">Questions à poser</span>${bullets(m.questions)}</div>
      <div class="card-x"><span class="xlabel">Cas d'usage</span>${bullets(m.cas_usage)}</div>
      <div class="card-x"><span class="xlabel">Erreurs fréquentes</span>${bullets([...m.erreurs, ...ERREURS_TRANSVERSES])}</div></details>` : "";
    const neConfond = conf.length ? `<details class="acc"><summary>⚠ À ne pas confondre <span class="muted">(même famille : ${esc(c.famille)})</span></summary>${bullets(conf)}
      <p class="muted">Contrats proches — vérifier les garanties/exclusions propres à chacun avant toute réponse.</p></details>` : "";
    const pdfSec = pdfs.length ? `<details class="acc"><summary>📄 Documents PDF liés <span class="muted">(${pdfs.length} — font foi)</span></summary>${bullets(pdfs)}
      <p class="muted"><a href="#/pdf">→ ouvrir les PDF contractuels</a></p></details>` : "";
    // Sections issues de l'index dérivé Pack A (évolution ①) — chaque item porte sa source PDF.
    const d = findDerived(c);
    const defSec = d?.definitions?.length ? `<details class="acc"><summary>📖 Définitions <span class="muted">(${d.definitions.length})</span></summary>
      <ul class="hlist">${d.definitions.map(x => `<li><b>${esc(x.terme)}</b> — ${esc(x.definition)}${sourceLink(x)}</li>`).join("")}</ul></details>` : "";
    const condSec = d?.conditions_souscription?.length ? `<details class="acc"><summary>📌 Conditions de souscription <span class="muted">(${d.conditions_souscription.length} — âge, adhésion, médical…)</span></summary>
      <ul class="hlist">${d.conditions_souscription.map(x => `<li>${esc(x.texte)}${sourceLink(x)}</li>`).join("")}</ul></details>` : "";
    const enriched = (d?.faits || []).filter(f => f.declencheurs.length || f.plafonds.length || f.franchises.length);
    const enrSec = enriched.length ? `<details class="acc"><summary>🎯 Déclencheurs, plafonds & franchises <span class="muted">(${enriched.length})</span></summary>
      ${enriched.map(f => `<div class="kvgroup"><div class="kv"><strong>${esc(f.titre)}</strong>${sourceLink(f)}</div>
        ${f.declencheurs.length ? `<div class="kv"><span class="xlabel">Déclencheurs</span> ${esc(f.declencheurs.join(" · "))}</div>` : ""}
        ${f.plafonds.length ? `<div class="kv"><span class="xlabel">Plafonds</span> ${esc(f.plafonds.join(" · "))}</div>` : ""}
        ${f.franchises.length ? `<div class="kv"><span class="xlabel">Franchises</span> ${esc(f.franchises.join(" · "))}</div>` : ""}</div>`).join("")}
      <p class="muted">Extraits contractuels sourcés — vérifier la notice pour le cas précis.</p></details>` : "";
    return `<article class="card"><div class="card-h"><strong>${esc(c.nom)}</strong><span class="tag t-themes">${esc(c.famille || "")}</span>${c.date_document ? `<span class="muted">${esc(c.date_document)}</span>` : ""}<button class="btn ghost" data-print style="min-height:28px;padding:0 9px;margin-left:auto">🖨</button></div>
      ${c.assureur ? `<p class="card-x"><span class="xlabel">Assureur</span> ${esc(c.assureur)}</p>` : ""}
      ${c._minimal ? `<div class="warnbox">⚠ Données limitées pour ce contrat dans le projet — se référer à la notice PDF (ci-dessous). Fiche minimale.</div>` : ""}
      ${r ? (r.length > 380 ? `<details class="fold"><summary class="card-b">${esc(r.slice(0, 380))}…</summary><p class="card-b">${esc(r.slice(380))}</p></details>` : `<p class="card-b">${esc(r)}</p>`) : ""}
      ${reperes}${secs}${enrSec}${defSec}${condSec}${neConfond}${pdfSec}
      <p class="muted">⚖️ Limites : repères génériques ; pour le cas précis, la notice PDF fait foi. Aucune réponse client sans vérification de la source.</p></article>`;
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
  function paint() {
    const shown = lastHits.filter(h => matchFilter(FILTERS.find(f => f.id === active), h));
    filtersEl.innerHTML = FILTERS.map(f => {
      const n = f.id === "all" ? lastHits.length : lastHits.filter(h => matchFilter(f, h)).length;
      return n || f.id === "all" ? `<button class="chip ${active === f.id ? "on" : ""}" data-fid="${f.id}">${esc(f.label)}${f.id === "all" ? "" : ` (${n})`}</button>` : "";
    }).join("");
    filtersEl.querySelectorAll("[data-fid]").forEach(b => b.onclick = () => { active = b.dataset.fid; paint(); });
    const terms = (input.value.trim().toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").match(/[a-z0-9]{2,}/g)) || [];
    res.innerHTML = shown.length ? `<p class="muted">${shown.length} résultat(s)${active !== "all" ? " · filtre : " + esc(FILTERS.find(f => f.id === active).label) : ""}</p>` + shown.map(h => `
      <article class="card"><div class="card-h"><span class="pill">${esc(h.type)}</span><strong>${esc(h.label || "(sans titre)")}</strong><span class="muted">${esc(h.contrat || "")}</span></div>
      <p class="card-b">${highlight(h.text, terms)}</p>
      <p class="muted"><a href="${h.ref}">→ ouvrir la section</a></p></article>`).join("")
      : "<p class='muted'>Aucun résultat pour ce filtre.</p>";
  }
  let t;
  async function run(q) {
    q = (q || "").trim();
    if (q.length < 2) { lastHits = []; filtersEl.innerHTML = ""; res.innerHTML = "<p class='muted'>Tape au moins 2 caractères.</p>"; return; }
    res.innerHTML = "<p class='muted'>Recherche…</p>";
    lastHits = await kb.searchAll(q);
    paint();
  }
  input.addEventListener("input", e => { clearTimeout(t); t = setTimeout(() => run(e.target.value), 250); });
  // Requête transportée depuis la barre du bandeau (recherche contextuelle AXA).
  const carried = (get("axaQuery") || "").trim();
  if (carried.length >= 2) { input.value = carried; run(carried); }
}

/* ---------- Copilote de réponse (Phase 6, SANS IA) ----------
   Doctrine (mode d'emploi double master) : Pack A = preuve contractuelle (fait foi) ;
   Pack B = raisonnement (jamais cité seul comme preuve). Le copilote rassemble les deux,
   sourcés et séparés, et laisse le conseiller formuler — la notice PDF fait toujours foi. */
const COPILOTE_EXEMPLES = ["décès accidentel couvert ?", "délai de carence", "rachat possible", "exclusions décès", "invalidité IPT", "bénéficiaire"];
async function copilote(body) {
  body.innerHTML = `
    <p class="lead">Copilote de réponse <b>sans IA</b> : pose une question, il rassemble les
    <b>preuves contractuelles (Pack A — font foi)</b> et le <b>raisonnement (Pack B — aide à décider, jamais une preuve)</b>,
    puis te laisse formuler la réponse. <b>La notice PDF fait toujours foi.</b></p>
    <div class="view-head" style="margin-top:0">
      <input class="filter" id="cop_q" placeholder="Ex : le décès accidentel est-il couvert par MasterLife ?" aria-label="Question au copilote" autofocus>
    </div>
    <div class="filters" id="cop_ex">${COPILOTE_EXEMPLES.map(x => `<button class="chip" data-ex="${esc(x)}">${esc(x)}</button>`).join("")}</div>
    <div id="cop_res"><p class="muted">Tape une question (≥ 2 caractères) ou choisis un exemple. Aucune donnée client n'est stockée.</p></div>`;
  const input = body.querySelector("#cop_q");
  const res = body.querySelector("#cop_res");

  const norm = s => String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  const highlight = (text, terms) => {
    let out = esc(String(text).slice(0, 320));
    for (const t of terms) { if (t.length < 2) continue; out = out.replace(new RegExp("(" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi"), "<mark>$1</mark>"); }
    return out;
  };

  // Brief sourcé, copiable (note de RDV ou base d'un prompt IA) — la doctrine est rappelée en clair.
  function briefText(q, preuves, reasoning) {
    const L = ["QUESTION : " + q, "", "PREUVES CONTRACTUELLES (Pack A — à vérifier sur la notice PDF, qui fait foi) :"];
    if (preuves.length) preuves.forEach(h => L.push(`- [${h.contrat || "—"}] ${(h.label ? h.label + " : " : "")}${h.text}`));
    else L.push("- (aucune preuve trouvée — ne pas répondre sans vérifier la notice)");
    L.push("", "RAISONNEMENT (Pack B — aide à la décision, NON contractuel) :");
    if (reasoning.length) reasoning.forEach(r => L.push(`- [${r.branchLabel}] ${r.text}`));
    else L.push("- (aucun élément de raisonnement)");
    L.push("", "RÈGLE : la notice PDF fait foi. Vérifier avant toute réponse au client.");
    return L.join("\n");
  }

  function render(q, preuves, reasoning) {
    const terms = norm(q).match(/[a-z0-9]{2,}/g) || [];
    const preuvesHtml = preuves.length ? preuves.map(h => `
      <article class="card"><div class="card-h"><span class="pill integrated">preuve</span><span class="pill">${esc(h.type)}</span>
        <strong>${esc(h.label || "(sans titre)")}</strong><span class="muted">${esc(h.contrat || "")}</span></div>
      <p class="card-b">${highlight(h.text, terms)}</p>
      <p class="muted"><a href="${h.ref}">→ ouvrir la fiche</a> · <a href="#/pdf">📄 notice (fait foi)</a></p></article>`).join("")
      : `<div class="card"><p class="warn">⚠ Aucune preuve contractuelle trouvée pour ces mots-clés.
        Ne réponds pas au client sans vérifier la notice — reformule ta question ou <a href="#/pdf">ouvre le PDF</a>.</p></div>`;
    const reasoningHtml = reasoning.length ? reasoning.map(r => `
      <article class="card"><div class="card-h"><span class="pill pending">raisonnement · non contractuel</span>
        <span class="muted">${esc(r.branchLabel)}</span></div>
      <p class="card-b">${highlight(r.text, terms)}</p></article>`).join("")
      : `<p class="muted">Aucun élément de raisonnement Pack B pour cette question.</p>`;

    res.innerHTML = `
      <h3 class="day-h">① Preuves contractuelles <span class="pill integrated">Pack A · font foi</span></h3>
      ${preuvesHtml}
      <h3 class="day-h">② Raisonnement <span class="pill pending">Pack B · jamais une preuve</span></h3>
      ${reasoningHtml}
      <h3 class="day-h">③ Réponse à formuler</h3>
      <div class="card">
        <p>Pars des preuves Pack A, <b>vérifie la notice PDF</b> (elle fait foi), puis reformule au client.
        Le raisonnement Pack B t'aide à structurer mais ne se cite jamais seul.</p>
        <div class="btns"><button class="btn gold" id="cop_copy">📋 Copier le brief sourcé</button>
          <a class="btn ghost" href="#/pdf">📄 Ouvrir un PDF</a>
          <a class="btn ghost" href="#/assistants">📦 Pack de contexte IA</a></div>
      </div>`;
    bindCopy(res.querySelector("#cop_copy"), () => briefText(q, preuves, reasoning));
  }

  let t;
  async function run(q) {
    q = (q || "").trim();
    if (q.length < 2) { res.innerHTML = `<p class="muted">Tape une question (≥ 2 caractères) ou choisis un exemple.</p>`; return; }
    res.innerHTML = `<p class="muted">Recherche dans la base (preuves + raisonnement)…</p>`;
    // includeMaster:false → searchAll ne remonte que des faits contractuels (Pack A) ; Pack B est traité à part.
    const [preuves, reasoning] = await Promise.all([kb.searchAll(q, { includeMaster: false }), kb.reasoningB(q)]);
    render(q, preuves.slice(0, 12), reasoning);
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
async function comparateur(body, human) {
  const resume = await kb.source("contrats_resume_humain");
  const t = await kb.source("comparatif");
  const contrats = resume?.contrats || [];
  if (!contrats.length) { body.innerHTML = `<p class="warn">Données de comparaison indisponibles.</p>`; return; }
  if (!human) { body.innerHTML = `<pre>${esc(JSON.stringify({ comparatif: t, contrats: contrats.map(c => c.nom) }, null, 2).slice(0, 60000))}</pre>`; return; }
  const titles = (c, key) => (c[key] || []).map(f => typeof f === "string" ? f : (f.titre && !f.titre.startsWith("_") ? f.titre : "")).filter(Boolean);
  const opt = (sel, c) => `<option value="${esc(c.nom)}" ${sel === c.nom ? "selected" : ""}>${esc(c.nom)}</option>`;
  let a = contrats[0].nom, b = contrats[1] ? contrats[1].nom : contrats[0].nom;

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

/* ---------- Sources officielles ---------- */
async function sources(body) {
  const m = await kb.manifest();
  const entries = Object.entries(m.sources || {});
  const checks = await Promise.all(entries.map(async ([role]) => [role, (await kb.source(role)) != null]));
  const ok = Object.fromEntries(checks);
  body.innerHTML = `
    <p class="lead">Manifeste des masters de connaissances (<code>data/AXA/workspace_manifest.json</code>) :
    pour brancher une nouvelle version, il suffit d'y changer un chemin — le module s'adapte.</p>
    <div class="tblwrap"><table class="tbl"><thead><tr><th>Rôle</th><th>Fichier</th><th>Description</th><th>État</th></tr></thead><tbody>
      ${entries.map(([role, d]) => `<tr><td style="text-align:left"><code>${esc(role)}</code></td>
        <td style="text-align:left"><code>${esc(d.path)}</code></td>
        <td style="text-align:left;white-space:normal">${esc(d.description || "")}</td>
        <td>${ok[role] ? '<span class="up">✓ chargé</span>' : '<span class="down">absent</span>'}</td></tr>`).join("")}
    </tbody></table></div>`;
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
