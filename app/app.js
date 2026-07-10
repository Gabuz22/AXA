// Gabriel AXA — shell de l'application métier autonome (Jalon 0).
// Navigation orientée conseiller + routeur par hash + chargement de la section AXA.
// Aucune dépendance à Gabriel Virtuel : services et modules sont locaux (copiés puis élagués).
import { get, set } from "./state/store.js";

// Navigation validée (sitemap). id = clé de section du module axa.js.
const NAV = [
  { group: "Démarrer", items: [
    { id: "accueil", label: "Accueil", icon: "🏠" },
    { id: "decouvrir", label: "Découvrir Gabriel AXA", icon: "✨" },
    { id: "cas_usage", label: "Que puis-je faire ?", icon: "🎯" },
    { id: "premiers_pas", label: "Premiers pas & FAQ", icon: "🧭" },
  ]},
  { group: "Utiliser", items: [
    { id: "recherche", label: "Recherche", icon: "🔎" },
    { id: "contrat", label: "Contrats", icon: "📑" },
    { id: "comparateur", label: "Comparateur", icon: "⚖️" },
    { id: "glossaire", label: "Glossaire", icon: "📖" },
    { id: "copilote", label: "Copilote de réponse", icon: "🧠" },
    { id: "pdf", label: "Notices PDF", icon: "📄" },
  ]},
  { group: "Avec une IA", items: [
    { id: "assistants", label: "Utiliser avec une IA", icon: "🤖" },
    { id: "portail_ia", label: "Vue IA (portail)", icon: "🌐" },
  ]},
  { group: "Confiance", items: [
    { id: "sources", label: "Sources officielles", icon: "📚" },
    { id: "confiance", label: "Pourquoi faire confiance", icon: "🔒" },
    { id: "tester", label: "Tester Gabriel AXA", icon: "🧪" },
  ]},
  { group: "Outils conseiller (bêta)", items: [
    { id: "besoins", label: "Analyse des besoins", icon: "🧩", beta: true },
    { id: "rdv", label: "Préparation RDV", icon: "🗓", beta: true },
    { id: "animateur", label: "Animateur", icon: "🎓", beta: true },
  ]},
];
const INDEX = {}; NAV.forEach(g => g.items.forEach(it => INDEX[it.id] = it));

// Aide contextuelle par section (le « ? » du header). Aucune donnée, aucun réseau.
const HELP = {
  accueil: { what: "Le point de départ : la promesse de Gabriel AXA et l'accès direct à la recherche.", how: ["Tape ta question dans la barre de recherche.", "Ou ouvre une fiche contrat, le copilote ou une notice."] },
  recherche: { what: "Le cœur du produit : retrouver une garantie, une exclusion, une définition ou une condition — sourcé.", how: ["Tape en langage naturel (synonymes tolérés).", "Filtre par type ; chaque résultat porte sa source (notice/page)."] },
  contrat: { what: "Les fiches contrat, par ordre alphabétique.", how: ["Choisis un contrat ou filtre.", "Chaque fait renvoie à la notice à la bonne page."] },
  copilote: { what: "Réponse assemblée sans IA : preuves (Pack A) + raisonnement (Pack B), séparés.", how: ["Pose ta question.", "Copie le brief sourcé. La notice PDF fait foi."] },
  comparateur: { what: "Deux contrats côte à côte pour choisir.", how: ["Sélectionne deux contrats à comparer."] },
  glossaire: { what: "Les termes définis dans les notices AXA, regroupés et sourcés.", how: ["Filtre un terme pour voir ses définitions par contrat."] },
  pdf: { what: "Les notices contractuelles — la source qui fait foi.", how: ["Ouvre une notice, si possible à la bonne page."] },
  decouvrir: { what: "Ce qu'est Gabriel AXA, à qui il s'adresse et ce qu'il change — en moins de 5 minutes.", how: ["Lis la promesse et les exemples.", "Puis lance une recherche."] },
  cas_usage: { what: "Des exemples concrets et cliquables de ce que tu peux faire aujourd'hui.", how: ["Clique un exemple pour l'essayer directement."] },
  assistants: { what: "Utiliser Gabriel AXA avec une IA (ChatGPT, Claude, Gemini) : il suffit de coller l'adresse de la Vue IA.", how: ["Copie l'URL de la Vue IA.", "Colle-la dans ton assistant, puis pose ta question."] },
  portail_ia: { what: "Le portail de la Vue IA : tout ce qu'une IA peut exploiter (guide, concepts, routage, méthode, sources…).", how: ["Ouvre une brique pour comprendre à quoi elle sert.", "Copie l'URL pour la donner à une IA."] },
  confiance: { what: "D'où viennent les données et pourquoi s'y fier : documents publics, traçabilité, notice qui fait foi.", how: ["Chaque information renvoie à sa notice PDF.", "Rien n'est inventé."] },
  tester: { what: "La phase de test : ce qu'on attend de toi pour construire la prochaine version.", how: ["Note les erreurs et les manques.", "Compare avec ta pratique."] },
  sources: { what: "Quand s'appuyer sur le contrat, la notice, ou une source officielle externe.", how: ["Le contrat/notice fait foi ; les sources officielles pour la réglementation évolutive."] },
  besoins: { what: "Un questionnaire guidé pour cadrer le besoin du client.", how: ["Réponds aux questions ; oriente vers les contrats pertinents."] },
  rdv: { what: "Une trame pour préparer un rendez-vous client.", how: ["Suis la trame ; imprime si besoin."] },
  animateur: { what: "Mode formation / réunion d'équipe.", how: ["Utilise les repères pour animer une session."] },
  premiers_pas: { what: "Le tutoriel de prise en main de Gabriel AXA.", how: ["Suis les étapes ; reviens ici quand tu veux."] },
};
const DEFAULT_HELP = { what: "Gabriel AXA : la base de connaissances contractuelle AXA, sourcée, pour gagner du temps.", how: ["Utilise la recherche ou le copilote.", "La notice PDF fait toujours foi."] };

function renderNav() {
  const cur = currentId();
  return NAV.map(g => `<div class="nv-g"><div class="nv-gh">${g.group}</div>` +
    g.items.map(it => it.external
      ? `<a class="nv-i" href="${it.href}" target="_blank" rel="noopener"><span>${it.icon}</span> ${it.label} <span class="nv-ext">↗</span></a>`
      : `<a class="nv-i ${it.id === cur ? "on" : ""}" href="#/${it.id}"><span>${it.icon}</span> ${it.label}${it.beta ? ` <span class="nv-beta">bêta</span>` : ""}</a>`).join("") +
    `</div>`).join("");
}
function parseHash() {
  const parts = (location.hash.replace(/^#\/?/, "") || "accueil").split("/").filter(Boolean);
  return { id: INDEX[parts[0]] ? parts[0] : "accueil", path: parts.slice(1) };
}
function currentId() { return parseHash().id; }

async function route() {
  const { id, path } = parseHash(); const item = INDEX[id];
  document.querySelectorAll(".nv-i").forEach(a => a.classList.toggle("on", a.getAttribute("href") === "#/" + id));
  const view = document.getElementById("view");
  view.innerHTML = `<div class="view-head"><h1>${item.icon} ${item.label}</h1></div><div id="sectionwrap"></div>`;
  try {
    const m = await import("./modules/axa.js");
    await m.mount(document.getElementById("sectionwrap"), { section: id, path });
    document.title = `${item.label} — Gabriel AXA`;
    view.scrollTo && view.scrollTo(0, 0);
  } catch (e) {
    document.getElementById("sectionwrap").innerHTML = `<div class="view-body"><p class="warn">Erreur de chargement : ${e.message}</p></div>`;
  }
}

/* ---------- Aide contextuelle ---------- */
const li = s => `<li>${s}</li>`;
function openHelp() {
  const item = INDEX[currentId()] || { label: "Gabriel AXA", icon: "🛡" };
  const h = HELP[currentId()] || DEFAULT_HELP;
  const drawer = document.getElementById("helpDrawer");
  document.getElementById("helpTitle").textContent = `${item.icon} ${item.label}`;
  document.getElementById("helpBody").innerHTML =
    `<p class="lead">${h.what}</p>` +
    (h.how?.length ? `<h3 class="day-h">Comment faire</h3><ul>${h.how.map(li).join("")}</ul>` : "") +
    `<p class="muted" style="margin-top:14px">La notice PDF fait toujours foi. Aucune réponse client sans vérifier la source.</p>`;
  drawer.hidden = false;
  void drawer.offsetWidth; // force un reflow → la transition slide-in part de l'état fermé (indépendant de requestAnimationFrame)
  drawer.classList.add("open");
}
function closeHelp() {
  const drawer = document.getElementById("helpDrawer");
  drawer.classList.remove("open");
  setTimeout(() => { drawer.hidden = true; }, 180);
}

function boot() {
  document.documentElement.dataset.theme = get("theme") || "dark";
  document.getElementById("nav").innerHTML = renderNav();
  const gq = document.getElementById("globalSearch");
  if (gq) gq.addEventListener("keydown", e => {
    if (e.key === "Enter") {
      const q = gq.value.trim(); gq.value = "";
      set({ axaQuery: q });
      if (location.hash === "#/recherche") route(); else location.hash = "#/recherche";
    }
  });
  document.getElementById("helpBtn")?.addEventListener("click", openHelp);
  document.getElementById("helpDrawer")?.addEventListener("click", e => { if (e.target.closest("[data-help-close]")) closeHelp(); });
  document.addEventListener("keydown", e => { if (e.key === "Escape" && !document.getElementById("helpDrawer")?.hidden) closeHelp(); });
  document.getElementById("themeBtn")?.addEventListener("click", () => {
    const next = (get("theme") || "dark") === "dark" ? "light" : "dark";
    set({ theme: next }); document.documentElement.dataset.theme = next;
  });
  document.getElementById("burger")?.addEventListener("click", () => document.body.classList.toggle("nav-open"));
  window.addEventListener("hashchange", () => { document.body.classList.remove("nav-open"); closeHelp(); route(); });
  if (!location.hash) location.hash = "#/accueil";
  route();
}
document.addEventListener("DOMContentLoaded", boot);
