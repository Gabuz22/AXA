// markdown — rendu Markdown SÉCURISÉ (Phase 5 open-source). Marked (MIT) pour parser,
// DOMPurify (Apache-2.0/MPL) pour sanitize. Marked ne nettoie PLUS le HTML depuis la v5 :
// on ne rend JAMAIS le résultat sans passer par DOMPurify. Fallback : texte brut échappé si
// une lib manque (hors ligne) → jamais d'écran vide, jamais de HTML non nettoyé.
let _marked = null, _purify = null, _loaded = null, _ok = false;

async function load() {
  if (_ok) return true;
  // On ne met en cache QUE le succès : un échec transitoire (réseau) doit pouvoir réessayer,
  // sinon toute l'app resterait en fallback texte pour la session.
  if (!_loaded) _loaded = (async () => {
    try {
      const [m, p] = await Promise.all([import("../vendor/marked.esm.js"), import("../vendor/purify.es.mjs")]);
      _marked = m.marked; _purify = p.default;
      _ok = !!(_marked && _purify && _purify.sanitize);
    } catch { _ok = false; }
    finally { if (!_ok) _loaded = null; } // permet un nouvel essai au prochain appel
  })();
  await _loaded;
  return _ok;
}

const escapeText = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;" }[c]));

// Rendu -> HTML sûr. Si markdown indisponible : <pre> échappé (fallback texte brut fidèle).
export async function renderMarkdown(text, { inline = false } = {}) {
  if (text == null) return "";
  const ok = await load();
  if (!ok) return `<pre class="md-fallback">${escapeText(text)}</pre>`;
  try {
    const raw = inline ? _marked.parseInline(String(text)) : _marked.parse(String(text));
    const clean = _purify.sanitize(raw, {
      USE_PROFILES: { html: true },
      ALLOWED_ATTR: ["href", "title", "alt", "src", "class", "colspan", "rowspan", "align"],
      FORBID_TAGS: ["style", "script", "iframe", "object", "embed", "form", "input"],
      FORBID_ATTR: ["style", "onerror", "onload", "onclick"],
    });
    // Post-traitement : liens en nouvel onglet, rel sûr (DOMPurify a déjà retiré javascript:).
    const div = document.createElement("div");
    div.innerHTML = clean;
    div.querySelectorAll("a[href]").forEach(a => {
      const h = a.getAttribute("href") || "";
      if (/^https?:/i.test(h)) { a.target = "_blank"; a.rel = "noopener noreferrer"; }
    });
    return div.innerHTML;
  } catch {
    return `<pre class="md-fallback">${escapeText(text)}</pre>`;
  }
}

export async function markdownAvailable() { return load(); }
