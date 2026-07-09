// store — état applicatif minimal, observable, persistant (localStorage). Pas de framework.
const KEY = "gv_app_state_v1";
const listeners = new Set();
let state = load();

function load() {
  try { return { ...defaults(), ...(JSON.parse(localStorage.getItem(KEY)) || {}) }; }
  catch { return defaults(); }
}
function defaults() { return { route: "home", theme: "dark", lastQuery: "", viewMode: "human" }; }
function persist() { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch {} }

export function get(k) { return k ? state[k] : state; }

// Traçage des exports (pour le Diagnostic : « dernière exportation »).
const EXPORTS_KEY = "gv_exports_v1";
export function markExport(kind) {
  try {
    const d = JSON.parse(localStorage.getItem(EXPORTS_KEY)) || {};
    d[kind] = new Date().toISOString();
    localStorage.setItem(EXPORTS_KEY, JSON.stringify(d));
  } catch {}
}
export function getExports() { try { return JSON.parse(localStorage.getItem(EXPORTS_KEY)) || {}; } catch { return {}; } }
export function set(patch) { state = { ...state, ...patch }; persist(); listeners.forEach(fn => fn(state)); }
export function subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); }
