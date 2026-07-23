// prospection — suivi de prospection du conseiller (Lot prospection, 2026-07-23).
//
// CONFIDENTIALITÉ — la règle du produit change ici, et c'est assumé et cadré :
// partout ailleurs Gabriel AXA ne stocke AUCUNE donnée nominative. Cet outil, lui, en stocke par
// nature (nom, téléphone, mail, adresse d'un prospect). Garde-fous appliqués :
//   • stockage EXCLUSIVEMENT dans le localStorage de CE navigateur (clé gv_axa_prospects_v1) ;
//   • JAMAIS envoyé au réseau, jamais inclus dans la Vue IA, jamais dans un pack destiné à une IA ;
//   • l'export est un geste HUMAIN explicite (bouton), jamais automatique ;
//   • aucune donnée de prospection ne doit être collée dans une IA externe (rappelé à l'écran).
// Le message type est une TRAME que le conseiller modifie ; l'essentiel est qu'il soit COPIABLE.
// L'envoi automatisé n'est volontairement PAS implémenté (décision produit ultérieure).
import { markExport } from "../state/store.js";

const LS = "gv_axa_prospects_v1";
const LS_TPL = "gv_axa_prospect_msg_v1";

const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const todayISO = () => new Date().toISOString().slice(0, 10);
const uid = () => "p_" + Date.now().toString(36) + "_" + Math.random().toString(36).slice(2, 7);

export const TYPES = [["directe", "Prospection directe"], ["prvt", "PRVT"]];
export const CATEGORIES = ["artisan", "commerçant", "profession libérale", "salarié", "retraité",
  "chef d'entreprise", "agriculteur", "demandeur d'emploi", "étudiant", "autre"];
export const STATUTS = [["a_appeler", "À appeler"], ["appele", "Appelé"], ["a_relancer", "À relancer"],
  ["rdv_pris", "RDV pris"], ["sans_suite", "Sans suite"]];

// Trame par défaut — volontairement neutre et prudente (aucune promesse commerciale, aucun chiffre).
// Le conseiller la réécrit à sa main : c'est SA parole, pas celle de l'outil.
const MSG_DEFAUT = `Bonjour {{nom}},

Je fais suite à notre échange téléphonique du {{date_appel}}.

Comme convenu, je vous recontacte pour faire le point sur votre situation
et voir si une protection adaptée pourrait vous être utile.

Seriez-vous disponible autour du {{date_relance}} ?

Bien à vous,`;

/* ---------- persistance locale ---------- */
function lire() { try { const r = JSON.parse(localStorage.getItem(LS)); return Array.isArray(r?.prospects) ? r.prospects : []; } catch { return []; } }
function ecrire(l) { try { localStorage.setItem(LS, JSON.stringify({ v: 1, prospects: l })); } catch {} }
function lireTpl() { try { return localStorage.getItem(LS_TPL) || MSG_DEFAUT; } catch { return MSG_DEFAUT; } }
function ecrireTpl(t) { try { localStorage.setItem(LS_TPL, t); } catch {} }

/* ---------- relance : en retard / aujourd'hui / à venir ---------- */
export function etatRelance(p) {
  if (!p.date_relance) return { cle: "aucune", label: "—", classe: "" };
  if (p.statut === "rdv_pris" || p.statut === "sans_suite") return { cle: "close", label: "—", classe: "" };
  const t = todayISO();
  if (p.date_relance < t) return { cle: "retard", label: "en retard", classe: "warn" };
  if (p.date_relance === t) return { cle: "aujourdhui", label: "aujourd'hui", classe: "gold" };
  return { cle: "avenir", label: p.date_relance, classe: "muted" };
}

/* ---------- message : substitution des variables ---------- */
export function composer(tpl, p) {
  const vals = {
    nom: p.nom || "", telephone: p.telephone || "", mail: p.mail || "", adresse: p.adresse || "",
    categorie: p.categorie || "", type: (TYPES.find(t => t[0] === p.type) || [, ""])[1],
    date_appel: p.date_premier_appel || "", date_relance: p.date_relance || "",
  };
  return String(tpl || "").replace(/\{\{(\w+)\}\}/g, (m, k) => (k in vals ? vals[k] : m));
}

/* ---------- export (geste humain explicite) ---------- */
function versCSV(list) {
  const cols = ["type", "nom", "telephone", "mail", "adresse", "categorie", "date_premier_appel", "date_relance", "statut", "notes"];
  const ech = v => `"${String(v ?? "").replace(/"/g, '""')}"`;
  return [cols.join(";"), ...list.map(p => cols.map(c => ech(p[c])).join(";"))].join("\r\n");
}
function telecharger(contenu, nom, mime) {
  const b = new Blob([contenu], { type: mime });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(b); a.download = nom;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1500);
}

/* ---------- section ---------- */
export async function prospection(body) {
  let filtre = "tous", edition = null, q = "";

  body.innerHTML = `
    <p class="lead">Suis tes prospects : qui appeler, quand relancer, et avec quel message.
      Le message est une <b>trame que tu modifies</b> — l'outil ne parle jamais à ta place.</p>
    <div class="warnbox">🔒 <b>Ces informations restent dans ce navigateur</b> — jamais envoyées, jamais transmises
      à une IA, jamais publiées. Elles ne sont sauvegardées nulle part ailleurs : pense à
      <b>exporter</b> régulièrement. Ne colle jamais ces données dans une IA externe.</div>

    <div class="card">
      <div class="card-h"><strong id="pr_ftitre">➕ Nouveau prospect</strong></div>
      <div class="row3">
        <label>Origine<select id="pr_type">${TYPES.map(([v, l]) => `<option value="${v}">${l}</option>`).join("")}</select></label>
        <label>Nom<input id="pr_nom" placeholder="Nom et prénom" autocomplete="off"></label>
        <label>Téléphone<input id="pr_tel" placeholder="06…" inputmode="tel" autocomplete="off"></label>
      </div>
      <div class="row3">
        <label>Mail<input id="pr_mail" placeholder="nom@exemple.fr" inputmode="email" autocomplete="off"></label>
        <label>Catégorie<select id="pr_cat"><option value="">—</option>${CATEGORIES.map(c => `<option>${c}</option>`).join("")}</select></label>
        <label>Statut<select id="pr_statut">${STATUTS.map(([v, l]) => `<option value="${v}">${l}</option>`).join("")}</select></label>
      </div>
      <div class="row3">
        <label>Adresse<input id="pr_adr" placeholder="Adresse" autocomplete="off"></label>
        <label>1er appel<input id="pr_d1" type="date"></label>
        <label>Relance prévue<input id="pr_d2" type="date"></label>
      </div>
      <label>Notes<textarea id="pr_notes" rows="2" placeholder="Contexte, objection, information utile…"></textarea></label>
      <div class="btns">
        <button class="btn gold" id="pr_add">➕ Ajouter</button>
        <button class="btn ghost" id="pr_cancel" hidden>Annuler</button>
        <span class="muted" id="pr_msg"></span>
      </div>
    </div>

    <div class="card">
      <div class="card-h"><strong>✉️ Message type</strong><span class="muted">modifiable — variables : {{nom}} {{date_appel}} {{date_relance}} {{categorie}}</span></div>
      <textarea id="pr_tpl" rows="8" spellcheck="true"></textarea>
      <div class="btns">
        <button class="btn" id="pr_tpl_save">💾 Enregistrer la trame</button>
        <button class="btn ghost" id="pr_tpl_reset">↺ Trame par défaut</button>
        <span class="muted" id="pr_tpl_msg"></span>
      </div>
    </div>

    <div class="view-head" style="margin-top:0">
      <input class="filter" id="pr_q" placeholder="🔎 filtrer (nom, téléphone, mail, catégorie…)" aria-label="Filtrer les prospects">
    </div>
    <div class="filters" id="pr_filters"></div>
    <div id="pr_list"></div>

    <div class="btns" style="margin-top:12px">
      <button class="btn ghost" id="pr_exp_csv">⬇ Exporter en CSV (tableur)</button>
      <button class="btn ghost" id="pr_exp_json">⬇ Exporter en JSON (sauvegarde)</button>
      <span class="muted" id="pr_exp_msg"></span>
    </div>`;

  const $ = id => body.querySelector("#" + id);
  const champs = () => ({
    type: $("pr_type").value, nom: $("pr_nom").value.trim(), telephone: $("pr_tel").value.trim(),
    mail: $("pr_mail").value.trim(), adresse: $("pr_adr").value.trim(), categorie: $("pr_cat").value,
    statut: $("pr_statut").value, date_premier_appel: $("pr_d1").value, date_relance: $("pr_d2").value,
    notes: $("pr_notes").value.trim(),
  });
  const vider = () => {
    ["pr_nom", "pr_tel", "pr_mail", "pr_adr", "pr_notes"].forEach(i => $(i).value = "");
    $("pr_cat").value = ""; $("pr_type").value = "directe"; $("pr_statut").value = "a_appeler";
    $("pr_d1").value = todayISO(); $("pr_d2").value = "";
    edition = null; $("pr_add").textContent = "➕ Ajouter";
    $("pr_ftitre").textContent = "➕ Nouveau prospect"; $("pr_cancel").hidden = true;
  };

  function compteurs(l) {
    const c = { tous: l.length, retard: 0, aujourdhui: 0 };
    l.forEach(p => { const e = etatRelance(p); if (e.cle === "retard") c.retard++; if (e.cle === "aujourdhui") c.aujourdhui++; });
    STATUTS.forEach(([v]) => c[v] = l.filter(p => p.statut === v).length);
    return c;
  }

  function carte(p) {
    const rel = etatRelance(p);
    const stat = (STATUTS.find(s => s[0] === p.statut) || [, p.statut])[1];
    const typ = (TYPES.find(t => t[0] === p.type) || [, p.type])[1];
    const contact = [
      p.telephone ? `<a href="tel:${esc(p.telephone.replace(/\s/g, ""))}">📞 ${esc(p.telephone)}</a>` : "",
      p.mail ? `<a href="mailto:${esc(p.mail)}">✉️ ${esc(p.mail)}</a>` : "",
    ].filter(Boolean).join(" · ");
    return `<article class="card">
      <div class="card-h">
        <span class="pill">${esc(typ)}</span><strong>${esc(p.nom || "(sans nom)")}</strong>
        <span class="muted">${esc(stat)}${p.categorie ? " · " + esc(p.categorie) : ""}</span>
        ${rel.cle === "retard" ? `<span class="pill" style="color:var(--warn)">relance en retard (${esc(p.date_relance)})</span>`
          : rel.cle === "aujourdhui" ? `<span class="pill" style="color:var(--gold)">à relancer aujourd'hui</span>` : ""}
      </div>
      <p class="card-b">${contact || "<span class='muted'>aucun contact renseigné</span>"}
        ${p.adresse ? `<br><span class="muted">📍 ${esc(p.adresse)}</span>` : ""}
        <br><span class="muted">1er appel : ${esc(p.date_premier_appel || "—")} · relance : ${esc(p.date_relance || "—")}</span>
        ${p.notes ? `<br>${esc(p.notes)}` : ""}</p>
      <details class="acc"><summary>✉️ Message à envoyer — modifiable puis copiable</summary>
        <textarea rows="9" data-msg="${p.id}">${esc(composer(lireTpl(), p))}</textarea>
        <div class="btns">
          <button class="btn gold" data-copy="${p.id}">📋 Copier le message</button>
          ${p.mail ? `<a class="btn ghost" data-mailto="${p.id}" href="#">✉️ Ouvrir dans le mail</a>` : ""}
        </div></details>
      <div class="btns">
        <button class="btn ghost" data-edit="${p.id}">✏️ Modifier</button>
        <button class="btn ghost" data-next="${p.id}">📅 Relance +7 j</button>
        <button class="btn danger" data-del="${p.id}">🗑 Supprimer</button>
      </div></article>`;
  }

  function rendre() {
    const tous = lire();
    const c = compteurs(tous);
    const chips = [["tous", `tous (${c.tous})`], ["retard", `⚠ en retard (${c.retard})`], ["aujourdhui", `aujourd'hui (${c.aujourdhui})`],
      ...STATUTS.map(([v, l]) => [v, `${l} (${c[v]})`])];
    $("pr_filters").innerHTML = chips.map(([v, l]) => `<button class="chip ${filtre === v ? "on" : ""}" data-f="${v}">${esc(l)}</button>`).join("");
    $("pr_filters").querySelectorAll("[data-f]").forEach(b => b.onclick = () => { filtre = b.dataset.f; rendre(); });

    const ql = q.toLowerCase();
    let list = tous.filter(p => {
      if (filtre === "retard" && etatRelance(p).cle !== "retard") return false;
      if (filtre === "aujourdhui" && etatRelance(p).cle !== "aujourdhui") return false;
      if (STATUTS.some(s => s[0] === filtre) && p.statut !== filtre) return false;
      if (!ql) return true;
      return [p.nom, p.telephone, p.mail, p.categorie, p.adresse, p.notes].some(v => String(v || "").toLowerCase().includes(ql));
    });
    // Les relances qui pressent d'abord : en retard, puis aujourd'hui, puis par date de relance.
    const rang = p => ({ retard: 0, aujourdhui: 1 }[etatRelance(p).cle] ?? 2);
    list.sort((a, b) => rang(a) - rang(b) || String(a.date_relance || "9999").localeCompare(String(b.date_relance || "9999")));

    $("pr_list").innerHTML = list.length ? list.map(carte).join("")
      : `<p class="muted">${tous.length ? "Aucun prospect ne correspond à ce filtre." : "Aucun prospect pour l'instant — ajoute le premier ci-dessus."}</p>`;

    $("pr_list").querySelectorAll("[data-copy]").forEach(b => b.onclick = async () => {
      const ta = $("pr_list").querySelector(`[data-msg="${b.dataset.copy}"]`);
      try { await navigator.clipboard.writeText(ta.value); const t = b.textContent; b.textContent = "✓ Copié"; setTimeout(() => b.textContent = t, 1500); }
      catch { b.textContent = "⚠ copie refusée"; }
    });
    $("pr_list").querySelectorAll("[data-mailto]").forEach(a => a.onclick = e => {
      e.preventDefault();
      const p = lire().find(x => x.id === a.dataset.mailto); if (!p) return;
      const ta = $("pr_list").querySelector(`[data-msg="${p.id}"]`);
      location.href = `mailto:${encodeURIComponent(p.mail)}?body=${encodeURIComponent(ta.value)}`;
    });
    $("pr_list").querySelectorAll("[data-edit]").forEach(b => b.onclick = () => {
      const p = lire().find(x => x.id === b.dataset.edit); if (!p) return;
      $("pr_type").value = p.type; $("pr_nom").value = p.nom || ""; $("pr_tel").value = p.telephone || "";
      $("pr_mail").value = p.mail || ""; $("pr_adr").value = p.adresse || ""; $("pr_cat").value = p.categorie || "";
      $("pr_statut").value = p.statut; $("pr_d1").value = p.date_premier_appel || ""; $("pr_d2").value = p.date_relance || "";
      $("pr_notes").value = p.notes || "";
      edition = p.id; $("pr_add").textContent = "💾 Enregistrer";
      $("pr_ftitre").textContent = "✏️ Modifier « " + (p.nom || "sans nom") + " »"; $("pr_cancel").hidden = false;
      window.scrollTo(0, 0);
    });
    $("pr_list").querySelectorAll("[data-next]").forEach(b => b.onclick = () => {
      const l = lire(); const p = l.find(x => x.id === b.dataset.next); if (!p) return;
      const base = p.date_relance && p.date_relance > todayISO() ? new Date(p.date_relance) : new Date();
      base.setDate(base.getDate() + 7);
      p.date_relance = base.toISOString().slice(0, 10);
      if (p.statut === "a_appeler") p.statut = "a_relancer";
      p.maj_le = new Date().toISOString(); ecrire(l); rendre();
    });
    $("pr_list").querySelectorAll("[data-del]").forEach(b => b.onclick = () => {
      const p = lire().find(x => x.id === b.dataset.del);
      if (!confirm(`Supprimer « ${p?.nom || "ce prospect"} » ? Cette action est définitive.`)) return;
      ecrire(lire().filter(x => x.id !== b.dataset.del)); rendre();
    });
  }

  /* ---- formulaire ---- */
  $("pr_add").onclick = () => {
    const d = champs();
    if (!d.nom && !d.telephone && !d.mail) { $("pr_msg").textContent = "⚠ Renseigne au moins un nom, un téléphone ou un mail."; return; }
    const l = lire();
    if (edition) {
      const p = l.find(x => x.id === edition);
      if (p) { Object.assign(p, d, { maj_le: new Date().toISOString() }); $("pr_msg").textContent = "✏️ Modifié."; }
    } else {
      l.push({ id: uid(), ...d, cree_le: new Date().toISOString(), maj_le: new Date().toISOString() });
      $("pr_msg").textContent = "✅ Ajouté.";
    }
    ecrire(l); vider(); rendre();
  };
  $("pr_cancel").onclick = () => { vider(); $("pr_msg").textContent = ""; };
  $("pr_q").addEventListener("input", e => { q = e.target.value; rendre(); });

  /* ---- trame de message ---- */
  $("pr_tpl").value = lireTpl();
  $("pr_tpl_save").onclick = () => { ecrireTpl($("pr_tpl").value); $("pr_tpl_msg").textContent = "💾 Trame enregistrée."; rendre(); };
  $("pr_tpl_reset").onclick = () => { $("pr_tpl").value = MSG_DEFAUT; ecrireTpl(MSG_DEFAUT); $("pr_tpl_msg").textContent = "↺ Trame par défaut restaurée."; rendre(); };

  /* ---- exports (gestes humains explicites) ---- */
  $("pr_exp_csv").onclick = () => {
    const l = lire(); if (!l.length) { $("pr_exp_msg").textContent = "Rien à exporter."; return; }
    telecharger("﻿" + versCSV(l), `prospection_${todayISO()}.csv`, "text/csv;charset=utf-8");
    markExport("prospection"); $("pr_exp_msg").textContent = `⬇ ${l.length} prospect(s) exporté(s).`;
  };
  $("pr_exp_json").onclick = () => {
    const l = lire(); if (!l.length) { $("pr_exp_msg").textContent = "Rien à exporter."; return; }
    telecharger(JSON.stringify({ v: 1, exporte_le: new Date().toISOString(), prospects: l }, null, 2),
      `prospection_${todayISO()}.json`, "application/json");
    markExport("prospection"); $("pr_exp_msg").textContent = `⬇ ${l.length} prospect(s) sauvegardé(s).`;
  };

  vider();
  rendre();
}
