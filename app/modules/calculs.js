// calculs — formules contractuelles AXA, sourcées et calculables (migré du cockpit legacy, 2026-07-23).
//
// POURQUOI CE MODULE : les 22 formules de `data/AXA/calculs/` sont extraites des notices, chacune
// avec son document ET sa page. C'est de la connaissance contractuelle vérifiable — elle n'existait
// que dans le cockpit legacy de Gabriel Virtuel, jamais dans ce produit.
//
// TROIS RÉGIMES, JAMAIS CONFONDUS (c'est tout l'intérêt) :
//   • CONTRACTUELLE exécutable — calcul exact, la notice fait foi.
//   • CONTRACTUELLE non exécutable — la formule renvoie à un barème/tableau : on l'affiche avec la
//     RAISON documentée, on ne calcule pas. Ne jamais « estimer » à la place.
//   • ESTIMÉE — déduite d'un tableau, avec marge d'erreur → fourchette basse/centrale/haute et
//     validation humaine obligatoire. Jamais présentée comme contractuelle.
//
// L'évaluateur est un parseur à descente récursive : AUCUN `eval`, aucune fonction non autorisée,
// variable manquante = erreur explicite. Porté fidèlement depuis `calculs_simulations_v2.9.2.js`.
const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const fmt = v => Number(v).toLocaleString("fr-FR", { maximumFractionDigits: 2 });

const BASE = "../data/AXA/calculs/";
const PDF_BASE = "../data/AXA/00_PACKAGE_ACTIF/Contrats-AXA/";

/* ---------- évaluateur arithmétique (sans eval) ---------- */
const FUNCS = {
  arrondi_superieur: a => Math.ceil(a[0]), plafond: a => Math.ceil(a[0]),
  arrondi_inferieur: a => Math.floor(a[0]), plancher: a => Math.floor(a[0]),
  arrondi: a => Math.round(a[0]), min: a => Math.min(...a), max: a => Math.max(...a),
  abs: a => Math.abs(a[0]), racine: a => Math.sqrt(a[0]),
};
// Les notices écrivent « arrondi_supérieur » (accentué) alors que la table est en ASCII. Le cockpit
// d'origine comparait sans déplier les accents : la fonction n'était JAMAIS trouvée (bug hérité,
// corrigé ici). On déplie donc l'identifiant pour CHERCHER LA FONCTION uniquement — les noms de
// VARIABLES gardent leurs accents (`jours_d_arrêt_total_indemnisés` doit rester tel quel).
const sansAccent = s => String(s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

export function calculer(expression, variables) {
  // Tolère l'écriture des notices : × ÷ – − et la virgule décimale française.
  const src = String(expression).replace(/×/g, "*").replace(/÷/g, "/").replace(/–|−/g, "-").replace(/(\d),(\d)/g, "$1.$2");
  let i = 0;
  const ws = () => { while (i < src.length && /\s/.test(src[i])) i++; };
  const peek = () => { ws(); return src[i]; };

  function expr() {
    let v = term();
    for (;;) {
      const c = peek();
      if (c === "+") { i++; v += term(); }
      else if (c === "-") { i++; v -= term(); }
      else break;
    }
    return v;
  }
  function term() {
    let v = power();
    for (;;) {
      const c = peek();
      if (c === "*") { i++; v *= power(); }
      else if (c === "/") { i++; v /= power(); }
      else break;
    }
    return v;
  }
  function power() {
    let v = unary(); ws();
    if (src[i] === "^") { i++; v = Math.pow(v, power()); }
    return v;
  }
  function unary() {
    ws();
    if (src[i] === "-") { i++; return -unary(); }
    if (src[i] === "+") { i++; return unary(); }
    return atom();
  }
  function atom() {
    ws();
    if (src[i] === "(") {
      i++; const v = expr(); ws();
      if (src[i] !== ")") throw new Error("parenthèse fermante manquante");
      i++; return v;
    }
    const nb = /^[0-9]*\.?[0-9]+/.exec(src.slice(i));
    if (nb) { i += nb[0].length; return Number(nb[0]); }
    const id = /^[A-Za-zÀ-ÿ_][A-Za-zÀ-ÿ0-9_]*/.exec(src.slice(i));
    if (!id) throw new Error(`expression invalide près de « ${src.slice(i, i + 10)} »`);
    i += id[0].length; ws();
    if (src[i] === "(") {
      i++; const args = [];
      if (peek() !== ")") { args.push(expr()); while (peek() === ",") { i++; args.push(expr()); } }
      if (src[i] !== ")") throw new Error("appel de fonction incomplet");
      i++;
      const fn = FUNCS[sansAccent(id[0])];
      if (!fn) throw new Error(`fonction non autorisée : ${id[0]}`);
      return fn(args);
    }
    if (!Object.prototype.hasOwnProperty.call(variables, id[0])) throw new Error(`variable manquante : ${id[0]}`);
    return Number(variables[id[0]]);
  }
  const r = expr(); ws();
  if (i < src.length) throw new Error(`caractères non autorisés : ${src.slice(i)}`);
  if (!Number.isFinite(r)) throw new Error("résultat non fini");
  return r;
}

/** Fourchette d'une formule ESTIMÉE : la marge est portée par la donnée, jamais inventée ici.
 *  Arrondi au centime : ce sont des montants, et le flottant IEEE donnerait 110.00000000000001. */
export function fourchette(central, margePct) {
  const m = Number(margePct) || 0;
  const r = x => Math.round(x * 100) / 100;
  return { basse: r(central * (1 - m / 100)), centrale: r(central), haute: r(central * (1 + m / 100)) };
}

/* ---------- rendu ---------- */
const REGIME = {
  exec: ["contractuelle · calculable", "good"],
  bareme: ["contractuelle · renvoie à un barème", "warn"],
  estimee: ["estimée · à valider", "warn"],
};

function lienNotice(src) {
  if (!src?.document_source) return "";
  const page = src.page ? `#page=${String(src.page).split(",")[0].trim()}` : "";
  const url = PDF_BASE + src.document_source.split("/").map(encodeURIComponent).join("/") + page;
  return `<a class="src" href="${esc(url)}" target="_blank" rel="noopener">📄 ${esc(src.document_source.split("/").pop())}${src.page ? `, p. ${esc(src.page)}` : ""}</a>`;
}

function carteFormule(f, idx) {
  const [label, ton] = f.executable ? REGIME.exec : (f.formule_estimee ? REGIME.estimee : REGIME.bareme);
  const vars = f.variables_tokens || [];
  const desc = (f.variables_desc || []).map(d => `<li>${esc(d)}</li>`).join("");
  return `<article class="card" data-f="${idx}">
    <div class="card-h">
      <strong>${esc(f.nom)}</strong>
      <span class="pill ${ton === "good" ? "exported" : "pending"}">${esc(label)}</span>
      <span class="muted">${esc(f.contrat)}${f.famille ? " · " + esc(f.famille) : ""}</span>
    </div>
    <p class="card-b"><code>${esc(f.formule)}</code></p>
    ${desc ? `<details class="acc"><summary class="muted">Variables (${vars.length || (f.variables_desc || []).length})</summary><ul class="hlist">${desc}</ul></details>` : ""}
    ${f.exemple_chiffre ? `<p class="muted">Exemple : ${esc(f.exemple_chiffre)}</p>` : ""}
    ${!f.executable ? `<p class="muted">⚠ Non calculable ici — ${esc(f.raison_non_exec || "raison non précisée")}. La notice fait foi.</p>` : `
      <div class="row3">${vars.map(v => `<label>${esc(v)}<input type="number" step="any" data-v="${esc(v)}" placeholder="0"></label>`).join("")}</div>
      <div class="btns"><button class="btn gold" data-calc="${idx}">= Calculer</button>
        <span class="muted" data-res="${idx}"></span></div>`}
    <p class="muted">${lienNotice(f.source)}${f.niveau_confiance ? ` · confiance ${f.niveau_confiance}%` : ""}</p>
  </article>`;
}

function carteEstimee(f, idx) {
  const params = f.parametres_modifiables || [];
  return `<article class="card" data-e="${idx}">
    <div class="card-h"><strong>${esc(f.nom)}</strong>
      <span class="pill pending">estimée · à valider</span>
      <span class="muted">${esc(f.contrat)}</span></div>
    <p class="card-b"><code>${esc(f.expression_base)}</code></p>
    <div class="warnbox">${esc(f.message_validation || "Formule estimée — validation humaine obligatoire.")}
      ${f.marge_pourcentage ? ` Marge retenue : ±${esc(f.marge_pourcentage)} %.` : " Marge nulle dans la zone vérifiée."}</div>
    <div class="row3">${params.map(p => `<label>${esc(p.nom)}${p.unite ? ` (${esc(p.unite)})` : ""}
      <input type="number" step="${esc(p.pas ?? "any")}" data-ev="${esc(p.nom)}" value="${esc(p.valeur_defaut ?? "")}"
        ${p.min != null ? `min="${esc(p.min)}"` : ""} ${p.max != null ? `max="${esc(p.max)}"` : ""}></label>`).join("")}</div>
    <div class="btns"><button class="btn" data-ecalc="${idx}">= Estimer</button>
      <span class="muted" data-eres="${idx}"></span></div>
    ${params.map(p => p.justification_marge ? `<p class="muted">${esc(p.nom)} : ${esc(p.justification_marge)}${p.source ? ` (${esc(p.source)})` : ""}</p>` : "").join("")}
    <p class="muted">Confiance ${esc(f.niveau_confiance ?? "—")}% · les JSON contractuels ne sont jamais modifiés.</p>
  </article>`;
}

export const title = "Formules & calculs";
export async function calculs(body) {
  body.innerHTML = `<p class="lead">Chargement des formules…</p>`;

  let index, estimees;
  try {
    [index, estimees] = await Promise.all([
      fetch(BASE + "calculs_index.json", { cache: "no-store" }).then(r => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); }),
      fetch(BASE + "axa_formules_estimees_parametres.json", { cache: "no-store" }).then(r => r.ok ? r.json() : { formules: [] }).catch(() => ({ formules: [] })),
    ]);
  } catch (e) {
    body.innerHTML = `<div class="card"><div class="card-h"><strong>Formules indisponibles</strong></div>
      <p class="card-b">Impossible de lire <code>data/AXA/calculs/</code> (${esc(e.message)}).</p></div>`;
    return;
  }

  const formules = index.formules || [];
  const est = estimees.formules || [];
  const nExec = formules.filter(f => f.executable).length;
  let filtre = "toutes", q = "";

  body.innerHTML = `
    <p class="lead">Les formules des notices AXA, <b>chacune avec son document et sa page</b>.
      ${nExec} sur ${formules.length} sont calculables ici ; les autres renvoient à un barème et
      sont affichées avec la raison — <b>on ne calcule jamais à la place d'un tableau</b>.</p>
    <div class="warnbox">⚖️ La <b>notice PDF fait foi</b>. Les formules « estimées » sont des déductions
      de tableau, à valider avant tout usage client — elles ne sont jamais contractuelles.</div>
    <div class="view-head" style="margin-top:0">
      <input class="filter" id="ca_q" placeholder="🔎 filtrer (nom, contrat, variable…)" aria-label="Filtrer les formules">
    </div>
    <div class="filters" id="ca_filters"></div>
    <div id="ca_list"></div>
    ${est.length ? `<h3 class="day-h">Formules estimées (${est.length}) — hypothèses à valider</h3><div id="ca_est"></div>` : ""}`;

  const $ = id => body.querySelector("#" + id);

  function rendre() {
    const chips = [["toutes", `toutes (${formules.length})`], ["calculables", `calculables (${nExec})`],
      ["bareme", `renvoient à un barème (${formules.length - nExec})`]];
    $("ca_filters").innerHTML = chips.map(([v, l]) => `<button class="chip ${filtre === v ? "on" : ""}" data-f="${v}">${esc(l)}</button>`).join("");
    $("ca_filters").querySelectorAll("[data-f]").forEach(b => b.onclick = () => { filtre = b.dataset.f; rendre(); });

    const ql = q.toLowerCase();
    const list = formules.filter(f => {
      if (filtre === "calculables" && !f.executable) return false;
      if (filtre === "bareme" && f.executable) return false;
      if (!ql) return true;
      return [f.nom, f.contrat, f.formule, ...(f.variables_tokens || [])].some(x => String(x || "").toLowerCase().includes(ql));
    });
    $("ca_list").innerHTML = list.length
      ? list.map(f => carteFormule(f, formules.indexOf(f))).join("")
      : `<p class="muted">Aucune formule ne correspond.</p>`;

    $("ca_list").querySelectorAll("[data-calc]").forEach(b => b.onclick = () => {
      const f = formules[+b.dataset.calc];
      const carte = b.closest("[data-f]");
      const out = carte.querySelector(`[data-res="${b.dataset.calc}"]`);
      const vars = {};
      let manque = null;
      carte.querySelectorAll("[data-v]").forEach(inp => {
        if (inp.value === "") manque = manque || inp.dataset.v;
        vars[inp.dataset.v] = Number(inp.value);
      });
      if (manque) { out.textContent = `⚠ renseigne « ${manque} »`; return; }
      try { out.innerHTML = `<b>= ${esc(fmt(calculer(f.rhs, vars)))}</b>`; }
      catch (e) { out.textContent = `⚠ ${e.message}`; }
    });
  }

  if (est.length) {
    $("ca_est").innerHTML = est.map((f, i) => carteEstimee(f, i)).join("");
    $("ca_est").querySelectorAll("[data-ecalc]").forEach(b => b.onclick = () => {
      const f = est[+b.dataset.ecalc];
      const carte = b.closest("[data-e]");
      const out = carte.querySelector(`[data-eres="${b.dataset.ecalc}"]`);
      const vars = {};
      carte.querySelectorAll("[data-ev]").forEach(inp => vars[inp.dataset.ev] = Number(inp.value));
      try {
        const c = calculer(f.expression_base, vars);
        const fk = fourchette(c, f.marge_pourcentage);
        out.innerHTML = f.marge_pourcentage
          ? `<b>≈ ${esc(fmt(fk.centrale))}</b> <span class="muted">(de ${esc(fmt(fk.basse))} à ${esc(fmt(fk.haute))})</span>`
          : `<b>≈ ${esc(fmt(fk.centrale))}</b>`;
      } catch (e) { out.textContent = `⚠ ${e.message}`; }
    });
  }

  $("ca_q").addEventListener("input", e => { q = e.target.value; rendre(); });
  rendre();
}
