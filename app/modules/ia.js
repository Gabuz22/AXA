// ia — Vue IA de Gabriel AXA (espace /ia). DESTINÉE AUX MODÈLES, PAS AUX HUMAINS.
// Objectif : restitution propre, sémantique, complète et sourcée, sans accordéons ni effets.
// HTML hiérarchique (h1/h2/h3), aucune information cachée, toutes les sources visibles.
// Données dérivées uniquement (vue humaine + fiches conseiller) ; masters jamais modifiés ;
// liens de téléchargement vers les masters bruts (Pack A / Pack B) fournis tels quels.
import * as kb from "../services/axaKnowledge.js";
import { renderMarkdown } from "../services/markdown.js";

const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const slug = s => String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

// Lien source visible et cliquable (jamais masqué).
function srcText(f) {
  const s = f && typeof f === "object" ? f.source : null;
  if (!s || !s.document_source) return "";
  const base = String(s.document_source).split("/").pop();
  const first = s.page ? String(s.page).split(",")[0].trim() : "";
  const url = (kb.fileUrl ? kb.fileUrl("00_PACKAGE_ACTIF/Contrats-AXA/" + s.document_source) : "") + (first ? "#page=" + first : "");
  return ` <a class="ia-src" href="${esc(url)}" target="_blank" rel="noopener">[Notice : ${esc(base)}${s.page ? ", p." + esc(String(s.page)) : ""}${s.section ? ", " + esc(s.section) : ""}]</a>`;
}

const factList = (items, opts = {}) => {
  const key = opts.text || (x => x.resume_humain || x.texte || "");
  const rows = (items || []).map(x => {
    if (typeof x === "string") return x.trim() ? `<li>${esc(x)}</li>` : "";
    const t = x.titre && !String(x.titre).startsWith("_") ? x.titre : (x.terme || "");
    const body = key(x);
    if (!t && !body) return "";
    return `<li>${t ? `<strong>${esc(t)}</strong>${body ? " — " : ""}` : ""}${esc(body)}${srcText(x)}</li>`;
  }).filter(Boolean);
  return rows.length ? `<ul>${rows.join("")}</ul>` : "";
};

// Restitution complète et lisible d'un contrat (Pack A dérivé + couche fiches conseiller).
function contractHTML(c, d, { h = 2 } = {}) {
  const H = n => "h" + Math.min(6, h + n);
  const sec = (label, items, opts) => { const b = factList(items, opts); return b ? `<${H(1)}>${esc(label)}</${H(1)}>${b}` : ""; };
  const meta = [c.type_contrat, c.famille, c.date_document, c.assureur].filter(Boolean).map(esc).join(" · ");
  return `<${H(0)} id="c-${slug(c.nom)}">${esc(c.nom)}</${H(0)}>
    ${meta ? `<p class="ia-meta">${meta}</p>` : ""}
    ${c.resume_neutre ? `<p>${esc(c.resume_neutre)}</p>` : ""}
    ${sec("Garanties principales", c.garanties_principales)}
    ${sec("Exclusions importantes", c.exclusions_importantes)}
    ${d?.conditions_souscription?.length ? `<${H(1)}>Conditions de souscription</${H(1)}>${factList(d.conditions_souscription, { text: x => x.texte })}` : ""}
    ${sec("Points de vigilance", c.points_de_vigilance)}
    ${sec("Options", c.options)}
    ${sec("Délais & franchises", c.delais_franchises)}
    ${sec("Cotisations & prix", c.cotisations_prix)}
    ${sec("Fiscalité", c.fiscalite)}
    ${d?.definitions?.length ? `<${H(1)}>Définitions</${H(1)}>${factList(d.definitions, { text: x => x.definition })}` : ""}`;
}

async function loadContracts() {
  const [resume, fiches] = await Promise.all([kb.source("contrats_resume_humain"), kb.source("fiches_conseiller")]);
  const contrats = (resume?.contrats || []).slice().sort((a, b) => String(a.nom).localeCompare(String(b.nom), "fr"));
  const byKey = new Map();
  for (const d of (fiches?.contrats || [])) { byKey.set(slug(d.nom), d); byKey.set(slug(d.id), d); }
  const findD = c => byKey.get(slug(c.nom)) || [...byKey.entries()].find(([k]) => k && slug(c.nom).startsWith(k))?.[1] || null;
  return { contrats, fiches, findD };
}

const DL_A = () => kb.fileUrl("AXA_MASTER_DONNEES_PACK_A_STABLE.json");
const DL_B = () => kb.fileUrl("AXA_MASTER_DONNEES_PACK_B_MATRICES_EXPERIMENTAL.json");
const DL_ME = () => kb.fileUrl("AXA_MODE_EMPLOI_IA_DOUBLE_MASTER.md");

const nav = active => `<nav class="ia-nav">
  <a href="#/ia"${active === "home" ? ' aria-current="page"' : ""}>Présentation</a>
  <a href="#/ia/pack-a"${active === "a" ? ' aria-current="page"' : ""}>Pack A</a>
  <a href="#/ia/pack-b"${active === "b" ? ' aria-current="page"' : ""}>Pack B</a>
  <a href="#/ia/glossaire"${active === "g" ? ' aria-current="page"' : ""}>Glossaire</a>
  <a href="#/ia/contrats"${active === "c" ? ' aria-current="page"' : ""}>Contrats</a>
</nav>`;

/* ---------- Pages ---------- */
async function landing(el) {
  el.innerHTML = `<article class="ia-doc">
    ${nav("home")}
    <h1>Gabriel AXA — Vue IA</h1>
    <p><strong>Cet espace est destiné aux modèles d'IA</strong> (ChatGPT, Claude, etc.), pas à la lecture humaine
    confortable. Il fournit une restitution propre, complète et sourcée de la base de connaissances contractuelle AXA.</p>

    <h2>Règles</h2>
    <ul>
      <li><strong>Pack A = preuve contractuelle</strong> (ce qui fait foi, après la notice PDF).</li>
      <li><strong>Pack B = raisonnement</strong> (aide à structurer une réponse ; jamais une preuve seule).</li>
      <li><strong>La notice PDF fait toujours foi.</strong> En cas de doute, renvoyer à la notice.</li>
      <li><strong>Aucune donnée inventée.</strong> Chaque élément porte sa source (notice, page).</li>
      <li>Documents issus de <strong>sources publiques</strong> ; aucune donnée client.</li>
    </ul>

    <h2>Pages</h2>
    <ul>
      <li><a href="#/ia/pack-a">Pack A — restitution complète</a> (données contractuelles par contrat)</li>
      <li><a href="#/ia/pack-b">Pack B — raisonnement et mode d'emploi</a></li>
      <li><a href="#/ia/glossaire">Glossaire complet</a></li>
      <li><a href="#/ia/contrats">Liste des contrats</a> → version IA de chaque contrat</li>
    </ul>

    <h2>Téléchargements (fichiers bruts)</h2>
    <ul>
      <li><a href="${DL_A()}" download>Pack A (JSON master)</a></li>
      <li><a href="${DL_B()}" download>Pack B (JSON master)</a></li>
      <li><a href="${DL_ME()}" download>Mode d'emploi double master (Markdown)</a></li>
    </ul>
    <p class="ia-note">Restitution générée à partir des couches dérivées (vue humaine, fiches conseiller). Les masters ne sont pas modifiés.</p>
  </article>`;
}

async function packA(el) {
  el.innerHTML = `<article class="ia-doc">${nav("a")}<h1>Pack A — restitution complète</h1><p>Chargement…</p></article>`;
  const { contrats, findD } = await loadContracts();
  const body = contrats.map(c => `<section>${contractHTML(c, findD(c), { h: 2 })}</section>`).join("\n");
  el.innerHTML = `<article class="ia-doc">
    ${nav("a")}
    <h1>Pack A — restitution complète</h1>
    <p><strong>Pack A</strong> = données contractuelles qui font foi (après la notice PDF). ${contrats.length} contrats.
    Fichier brut : <a href="${DL_A()}" download>Pack A (JSON)</a>.</p>
    ${body}
  </article>`;
}

async function packB(el) {
  el.innerHTML = `<article class="ia-doc">${nav("b")}<h1>Pack B — raisonnement</h1><p>Chargement…</p></article>`;
  let me = "";
  try { me = await kb.source("mode_emploi_ia"); } catch { me = ""; }
  const md = me ? await renderMarkdown(me) : "";
  el.innerHTML = `<article class="ia-doc">
    ${nav("b")}
    <h1>Pack B — raisonnement (matrices)</h1>
    <p><strong>Pack B</strong> aide à structurer une réponse (arbres de décision, modèles de réponse, garde-fous).
    <strong>Ce n'est jamais une preuve seule</strong> : la preuve reste le Pack A et la notice PDF.</p>
    <p>Fichier brut : <a href="${DL_B()}" download>Pack B (JSON master)</a> — volumineux, destiné à être fourni à un modèle en contexte.</p>
    <h2>Mode d'emploi (double master)</h2>
    ${md ? `<div class="ia-md">${md}</div>` : `<p><a href="${DL_ME()}" download>Télécharger le mode d'emploi (Markdown)</a></p>`}
  </article>`;
}

async function glossaire(el) {
  el.innerHTML = `<article class="ia-doc">${nav("g")}<h1>Glossaire</h1><p>Chargement…</p></article>`;
  const fiches = await kb.source("fiches_conseiller");
  const gloss = fiches?.glossaire || [];
  const body = gloss.map(g => `<h2>${esc(g.terme)}</h2><ul>${(g.entrees || []).map(e =>
    `<li><strong>${esc(e.contrat)}</strong> : ${esc(e.definition)}${srcText({ source: e.source })}</li>`).join("")}</ul>`).join("");
  el.innerHTML = `<article class="ia-doc">
    ${nav("g")}
    <h1>Glossaire complet</h1>
    <p>${gloss.length} termes définis dans les notices AXA (sourcés).</p>
    ${body || "<p>Glossaire indisponible.</p>"}
  </article>`;
}

async function contrats(el) {
  el.innerHTML = `<article class="ia-doc">${nav("c")}<h1>Contrats</h1><p>Chargement…</p></article>`;
  const { contrats } = await loadContracts();
  const items = contrats.map(c => `<li><a href="#/ia/contrat/${slug(c.nom)}">${esc(c.nom)}</a>${c.famille ? ` — ${esc(c.famille)}` : ""}</li>`).join("");
  el.innerHTML = `<article class="ia-doc">
    ${nav("c")}
    <h1>Liste des contrats</h1>
    <p>${contrats.length} contrats. Cliquer pour la version IA complète.</p>
    <ul>${items}</ul>
  </article>`;
}

async function contratOne(el, wanted) {
  el.innerHTML = `<article class="ia-doc">${nav("c")}<p>Chargement…</p></article>`;
  const { contrats, findD } = await loadContracts();
  const c = contrats.find(x => slug(x.nom) === wanted);
  if (!c) {
    el.innerHTML = `<article class="ia-doc">${nav("c")}<h1>Contrat introuvable</h1>
      <p><a href="#/ia/contrats">← liste des contrats</a></p></article>`;
    return;
  }
  el.innerHTML = `<article class="ia-doc">
    ${nav("c")}
    <p><a href="#/ia/contrats">← tous les contrats</a></p>
    ${contractHTML(c, findD(c), { h: 1 })}
    <p class="ia-note">Restitution dérivée. La notice PDF fait foi.</p>
  </article>`;
}

export const title = "Vue IA";
export async function mount(el, ctx) {
  const path = ctx?.path || [];
  const sub = path[0] || "";
  try {
    if (sub === "pack-a") return await packA(el);
    if (sub === "pack-b") return await packB(el);
    if (sub === "glossaire") return await glossaire(el);
    if (sub === "contrats") return await contrats(el);
    if (sub === "contrat") return await contratOne(el, path[1] || "");
    return await landing(el);
  } catch (e) {
    el.innerHTML = `<article class="ia-doc"><h1>Vue IA</h1><p>Erreur : ${esc(e.message)}</p></article>`;
  }
}
