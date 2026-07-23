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

/* ---------- projections : courbes (migrées de la section « 4. Courbes » du cockpit) ----------
   POURQUOI ELLES SURVIVENT, alors que le reste de la page legacy ne survit pas : sur 122
   sauvegardes de l'espace local, `gv_v292_etude` (périmètre d'étude), `gv_v292_scenarios` et
   `gv_v292_personnelles` (formules perso) n'apparaissent JAMAIS — ces fonctions n'ont jamais servi.
   `gv_v292_courbes`, si : 64 fois, avec une simulation réelle (40 €/mois, capital 5 000 €,
   modèle « cumul vs réduction », horizon 30 ans). On porte donc les courbes, et elles seules.
   Le tracé reste un SVG maison : aucune dépendance, aucun réseau. */
const VARS_RE = /[A-Za-zÀ-ÿ_][A-Za-zÀ-ÿ0-9_]*/g;
export const variablesDe = expr =>
  [...new Set([...String(expr).matchAll(VARS_RE)].map(m => m[0]))].filter(n => !(sansAccent(n) in FUNCS));

// Modèles de courbes : les EXPRESSIONS vivaient en dur dans le JS du cockpit (le JSON ne portait
// que les identifiants et les libellés) — elles sont reprises ici telles quelles.
const COURBE_CUMUL = { id: "cumul", nom: "Cumul des cotisations", expr: "cotisation_mensuelle * 12 * t", regime: "hypothese" };
const COURBE_CAPITAL = { id: "capital", nom: "Capital garanti estimé", expr: "capital_souscrit * (1 + taux_annuel / 100) ^ t", regime: "estimee" };
const COURBE_REDUC = { id: "reduction", nom: "Valeur de réduction estimée", expr: "capital_souscrit * taux_reduction / 100", regime: "estimee" };
const MODELES_COURBES = {
  cumul_vs_capital: [COURBE_CUMUL, COURBE_CAPITAL],
  cumul_vs_reduction: [COURBE_CUMUL, COURBE_REDUC],
  capital_vs_reduction: [COURBE_CAPITAL, COURBE_REDUC],
  evolution_cotisation: [{ id: "cotisation", nom: "Cotisation annuelle", expr: "cotisation_mensuelle * 12 * (1 + taux_annuel / 100) ^ t", regime: "hypothese" }],
  rachat_temps: [{ id: "rachat", nom: "Valeur de rachat estimée", expr: "cotisation_mensuelle * 12 * t * taux_reduction / 100", regime: "estimee" }],
  part_taxable: [{ id: "taxable", nom: "Part taxable estimée", expr: "max(0, montant_rachat - capital_verse)", regime: "estimee" }],
  comparaison_contrats: [
    { id: "contrat_a", nom: "Contrat A", expr: "capital_souscrit * (1 + taux_annuel / 100) ^ t", regime: "estimee" },
    { id: "contrat_b", nom: "Contrat B", expr: "capital_souscrit * (1 + (taux_annuel - 0.25) / 100) ^ t", regime: "estimee" },
  ],
  hypotheses_estimees: [
    { id: "basse", nom: "Hypothèse basse", expr: "capital_souscrit * (1 + (taux_annuel - 0.5) / 100) ^ t", regime: "estimee" },
    { id: "centrale", nom: "Hypothèse centrale", expr: "capital_souscrit * (1 + taux_annuel / 100) ^ t", regime: "estimee" },
    { id: "haute", nom: "Hypothèse haute", expr: "capital_souscrit * (1 + (taux_annuel + 0.5) / 100) ^ t", regime: "estimee" },
  ],
};
const PARAMS_DEFAUT = { cotisation_mensuelle: 40, capital_souscrit: 5000, taux_annuel: 1, taux_reduction: 65, montant_rachat: 6000, capital_verse: 5000 };
const CLE_COURBES = "gv_axa_courbes_v1";
const COULEURS = ["#f7931a", "#5b8def", "#5bd07a", "#e2674a", "#b78cff", "#38bdf8"];

/** Points d'une courbe sur l'horizon. Une expression fausse ne casse rien : le point vaut null. */
export function serie(courbe, params, horizon, pas) {
  const pts = [];
  for (let t = 0; t <= horizon + 1e-9; t += pas) {
    const x = Number(t.toFixed(4));
    let y = null;
    try { y = calculer(courbe.expr, { ...params, t: x }); } catch { y = null; }
    pts.push({ x, y: Number.isFinite(y) ? y : null });
  }
  return pts;
}

function svgCourbes(series, horizon) {
  const W = 820, H = 340, P = 52;
  const ys = series.flatMap(s => s.points.map(p => p.y)).filter(Number.isFinite);
  if (!ys.length) return `<p class="muted">Aucune courbe traçable : vérifie les expressions et les hypothèses.</p>`;
  const min = Math.min(0, ...ys), max = Math.max(1, ...ys);
  const px = v => P + (W - P * 2) * v / (horizon || 1);
  const py = v => H - P - (H - P * 2) * (v - min) / (max - min || 1);
  const traces = series.map((s, i) => {
    const d = s.points.filter(p => Number.isFinite(p.y)).map((p, k) => `${k ? "L" : "M"}${px(p.x).toFixed(1)},${py(p.y).toFixed(1)}`).join(" ");
    return `<path d="${d}" fill="none" stroke="${COULEURS[i % COULEURS.length]}" stroke-width="2.5"/>`;
  }).join("");
  const grad = [0, 0.5, 1].map(f => {
    const v = min + (max - min) * f;
    return `<text x="${P - 8}" y="${(py(v) + 4).toFixed(1)}" text-anchor="end" fill="currentColor" opacity=".55" font-size="11">${esc(fmt(v))}</text>`;
  }).join("");
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Projection sur ${horizon} ans" style="width:100%;height:auto;color:var(--txt,#9fb0c8)">
    <line x1="${P}" y1="${H - P}" x2="${W - P}" y2="${H - P}" stroke="currentColor" opacity=".35"/>
    <line x1="${P}" y1="${P}" x2="${P}" y2="${H - P}" stroke="currentColor" opacity=".35"/>
    ${grad}${traces}
    <text x="${W - P}" y="${H - 16}" text-anchor="end" fill="currentColor" opacity=".55" font-size="11">${esc(horizon)} ans</text></svg>`;
}

/** Monte le panneau de projection. `modeles` = graphiques_modeles du JSON (id + nom lisibles). */
function monterCourbes(host, modeles) {
  const lu = (() => { try { return JSON.parse(localStorage.getItem(CLE_COURBES)) || {}; } catch { return {}; } })();
  const cfg = {
    modele: MODELES_COURBES[lu.modele] ? lu.modele : "cumul_vs_capital",
    horizon: Number(lu.horizon) > 0 ? Number(lu.horizon) : 30,
    pas: Number(lu.pas) > 0 ? Number(lu.pas) : 1,
    params: { ...PARAMS_DEFAUT, ...(lu.params || {}) },
    courbes: Array.isArray(lu.courbes) && lu.courbes.length ? lu.courbes : MODELES_COURBES.cumul_vs_capital.map(c => ({ ...c, visible: true })),
  };
  const garder = () => { try { localStorage.setItem(CLE_COURBES, JSON.stringify(cfg)); } catch {} };
  // Les paramètres affichés sont ceux dont les courbes ont besoin — pas une liste figée.
  const paramsUtiles = () => [...new Set(cfg.courbes.flatMap(c => variablesDe(c.expr)))].filter(n => n !== "t");
  const hypotheses = () => [`Modèle : ${(modeles.find(m => m.id === cfg.modele) || {}).nom || cfg.modele}`,
    `Horizon : ${cfg.horizon} ans (pas de ${cfg.pas})`,
    `Hypothèses : ${paramsUtiles().map(n => `${n} = ${cfg.params[n] ?? 0}`).join(" ; ")}`,
    `Courbes : ${cfg.courbes.map(c => `${c.nom} [${c.regime === "estimee" ? "estimée" : "hypothèse de travail"}]`).join(" ; ")}`,
    "Simulation NON CONTRACTUELLE : elle illustre les hypothèses saisies. Vérifier barèmes et conditions à la notice avant tout usage client.",
  ].join("\n");

  function peindre() {
    const utiles = paramsUtiles();
    const series = cfg.courbes.filter(c => c.visible !== false).map(c => ({ ...c, points: serie(c, cfg.params, cfg.horizon, cfg.pas) }));
    host.innerHTML = `
      <div class="warnbox">📈 Projection <b>non contractuelle</b> : elle calcule ce que tu saisis, rien d'autre.
        Les courbes « estimées » reposent sur des hypothèses de rendement ou de réduction — jamais sur un engagement AXA.</div>
      <div class="row3">
        <label>Modèle<select id="cb_modele">${modeles.filter(m => MODELES_COURBES[m.id])
          .map(m => `<option value="${esc(m.id)}"${m.id === cfg.modele ? " selected" : ""}>${esc(m.nom)}</option>`).join("")}</select></label>
        <label>Horizon (ans)<input id="cb_horizon" type="number" min="1" max="60" value="${esc(cfg.horizon)}"></label>
        <label>Pas (ans)<input id="cb_pas" type="number" min="0.25" max="10" step="0.25" value="${esc(cfg.pas)}"></label>
      </div>
      <div class="row3">${utiles.map(n => `<label>${esc(n)}<input type="number" step="any" data-cbp="${esc(n)}" value="${esc(cfg.params[n] ?? 0)}"></label>`).join("")}</div>
      <div class="card" style="margin-top:10px">${svgCourbes(series, cfg.horizon)}
        <div class="filters" style="margin-top:8px">${cfg.courbes.map((c, i) => `<button class="chip ${c.visible === false ? "" : "on"}" data-cbv="${i}">
          <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${COULEURS[i % COULEURS.length]};margin-right:6px"></span>${esc(c.nom)}
          <span style="opacity:.75"> · ${esc(c.regime === "estimee" ? "estimée" : "hypothèse")}</span></button>`).join("")}</div>
      </div>
      <details class="acc"><summary class="muted">Voir et ajuster les expressions (${cfg.courbes.length})</summary>
        ${cfg.courbes.map((c, i) => `<label style="display:block;margin:6px 0">${esc(c.nom)}
          <input type="text" data-cbe="${i}" value="${esc(c.expr)}" style="width:100%"></label>`).join("")}
        <p class="muted">Variables autorisées : les hypothèses ci-dessus, plus <code>t</code> (années écoulées). Aucune fonction hors liste.</p></details>
      <div class="btns" style="margin-top:8px">
        <button class="btn gold" id="cb_tracer">Retracer</button>
        <button class="btn" id="cb_csv">Exporter le CSV</button>
        <button class="btn" id="cb_hyp">Copier les hypothèses</button>
        <button class="btn" id="cb_reset">↺ Modèle par défaut</button>
        <span class="muted" id="cb_msg"></span>
      </div>`;

    const $ = s => host.querySelector(s);
    const lire = () => {
      cfg.horizon = Math.min(60, Math.max(1, Number($("#cb_horizon").value) || 30));
      cfg.pas = Math.min(10, Math.max(0.25, Number($("#cb_pas").value) || 1));
      host.querySelectorAll("[data-cbp]").forEach(i => cfg.params[i.dataset.cbp] = Number(i.value) || 0);
      host.querySelectorAll("[data-cbe]").forEach(i => cfg.courbes[+i.dataset.cbe].expr = i.value.trim() || cfg.courbes[+i.dataset.cbe].expr);
      garder();
    };
    $("#cb_modele").onchange = e => {
      cfg.modele = e.target.value;
      cfg.courbes = MODELES_COURBES[cfg.modele].map(c => ({ ...c, visible: true }));
      // Une variable inconnue du nouveau modèle démarre à 0 plutôt que de faire échouer le tracé.
      paramsUtiles().forEach(n => { if (!(n in cfg.params)) cfg.params[n] = /taux/.test(n) ? 1 : 0; });
      garder(); peindre();
    };
    $("#cb_tracer").onclick = () => { lire(); peindre(); };
    host.querySelectorAll("[data-cbv]").forEach(b => b.onclick = () => {
      const c = cfg.courbes[+b.dataset.cbv]; c.visible = c.visible === false; garder(); peindre();
    });
    $("#cb_reset").onclick = () => { try { localStorage.removeItem(CLE_COURBES); } catch {}
      Object.assign(cfg, { modele: "cumul_vs_capital", horizon: 30, pas: 1, params: { ...PARAMS_DEFAUT },
        courbes: MODELES_COURBES.cumul_vs_capital.map(c => ({ ...c, visible: true })) }); peindre(); };
    $("#cb_csv").onclick = () => {
      lire();
      const s = cfg.courbes.map(c => ({ nom: c.nom, points: serie(c, cfg.params, cfg.horizon, cfg.pas) }));
      const lignes = [["annee", ...s.map(x => x.nom)]];
      (s[0]?.points || []).forEach((p, i) => lignes.push([p.x, ...s.map(x => x.points[i]?.y ?? "")]));
      const csv = lignes.map(l => l.map(c => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\n");
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
      a.download = "projection_axa.csv"; a.click(); URL.revokeObjectURL(a.href);
      $("#cb_msg").textContent = "✓ CSV exporté";
    };
    $("#cb_hyp").onclick = async () => {
      lire();
      try { await navigator.clipboard.writeText(hypotheses()); $("#cb_msg").textContent = "✓ Hypothèses copiées"; }
      catch { $("#cb_msg").textContent = "⚠ copie refusée par le navigateur"; }
    };
  }
  peindre();
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

  let index, estimees, modeles;
  try {
    [index, estimees, modeles] = await Promise.all([
      fetch(BASE + "calculs_index.json", { cache: "no-store" }).then(r => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); }),
      fetch(BASE + "axa_formules_estimees_parametres.json", { cache: "no-store" }).then(r => r.ok ? r.json() : { formules: [] }).catch(() => ({ formules: [] })),
      // Absent = pas de projection, jamais d'erreur : les formules restent complètes.
      fetch(BASE + "axa_etudes_modeles.json", { cache: "no-store" }).then(r => r.ok ? r.json() : null).catch(() => null),
    ]);
  } catch (e) {
    body.innerHTML = `<div class="card"><div class="card-h"><strong>Formules indisponibles</strong></div>
      <p class="card-b">Impossible de lire <code>data/AXA/calculs/</code> (${esc(e.message)}).</p></div>`;
    return;
  }

  const formules = index.formules || [];
  const est = estimees.formules || [];
  const grafs = (modeles?.graphiques_modeles || []).filter(m => MODELES_COURBES[m.id]);
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
    ${est.length ? `<h3 class="day-h">Formules estimées (${est.length}) — hypothèses à valider</h3><div id="ca_est"></div>` : ""}
    ${grafs.length ? `<h3 class="day-h">Projection — courbes</h3><div id="ca_courbes"></div>` : ""}`;

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

  if (grafs.length) monterCourbes($("ca_courbes"), grafs);

  $("ca_q").addEventListener("input", e => { q = e.target.value; rendre(); });
  rendre();
}
