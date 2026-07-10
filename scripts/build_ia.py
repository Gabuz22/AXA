#!/usr/bin/env python3
"""Génère la COUCHE IA STATIQUE EXHAUSTIVE de Gabriel AXA sous ia/.

La Vue IA est une PROJECTION des JSON (source de vérité unique). Tout est généré automatiquement ;
aucune duplication manuelle ; aucune donnée inventée ; les masters ne sont jamais modifiés ; tout
reste sourcé (notice + page) ; la notice PDF fait foi.

Sortie : pages .html + .md lisibles sans JavaScript, à URLs stables, avec IDs stables :
  index, guide-ia, manifeste, pack-a, pack-b, contrats, contrat/<slug>, garanties, exclusions,
  options, cotisations, delais, fiscalite, points-vigilance, formules, definitions, conditions,
  declencheurs, plafonds, franchises, glossaire, notices, sources, recherches, themes, themes/<slug>,
  couverture  + ai-manifest.json, sitemap-ia.xml, robots.txt, contrats.json, glossaire.json, ia.css.

Usage : python scripts/build_ia.py
"""
import io, os, sys, json, html, unicodedata, datetime, hashlib, re
from urllib.parse import quote

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
IA = "ia"
DATE = datetime.date.today().isoformat()
VERSION = "1.2.0"
SITE = "https://gabuz22.github.io/AXA"

def load(p, d=None):
    try:
        with open(p, encoding="utf-8") as f: return json.load(f)
    except Exception as e:
        print("  ! illisible:", p, e); return d

RESUME = load("data/AXA/vue_humaine/axa_contrats_resume_humain.json", {}) or {}
FICHES = load("data/AXA/derived/fiches_conseiller.json", {}) or {}
PDFIDX = load("data/AXA/ia/axa_pdf_index.json", {}) or {}
IGLOB  = load("data/AXA/ia/axa_index_global.json", {}) or {}
PACKB  = load("data/AXA/AXA_MASTER_DONNEES_PACK_B_MATRICES_EXPERIMENTAL.json", {}) or {}
SEARCH = load("data/AXA/ia/axa_search_suggestions.json", {}) or {}

def norm(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if unicodedata.category(c) != "Mn").lower()

def slug(s):
    out = "".join(c if c.isalnum() else "-" for c in norm(s))
    while "--" in out: out = out.replace("--", "-")
    return out.strip("-")

def sid(*parts):  # id stable court, déterministe
    return hashlib.md5("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:10]

CONTRATS = sorted((RESUME.get("contrats") or []), key=lambda c: norm(c.get("nom")))
DERIVED = {}
for d in (FICHES.get("contrats") or []):
    DERIVED[slug(d.get("nom"))] = d; DERIVED[slug(d.get("id"))] = d
def find_derived(c):
    k = slug(c.get("nom"))
    if k in DERIVED: return DERIVED[k]
    for dk, d in DERIVED.items():
        if dk and (k.startswith(dk) or dk.startswith(k)): return d
    return None

# ------------------------------------------------------------------ liens & sources
def data_pref(depth): return "../" * (depth + 1)   # ia/<depth> -> racine dépôt
def int_pref(depth):  return "../" * depth          # entre pages ia/

def pdf_href(document_source, page, depth):
    if not document_source: return None
    p = "data/AXA/00_PACKAGE_ACTIF/Contrats-AXA/" + str(document_source)
    first = str(page).split(",")[0].strip() if page else ""
    return data_pref(depth) + quote(p) + ("#page=" + first if first else "")

def src_label(src):
    base = str(src.get("document_source")).split("/")[-1]
    return "Notice : %s%s%s" % (base, ", p." + str(src["page"]) if src.get("page") else "", ", " + str(src["section"]) if src.get("section") else "")

def cite_md(src, depth):
    if not src or not src.get("document_source"): return ""
    return " [%s](%s)" % (src_label(src), pdf_href(src["document_source"], src.get("page"), depth))
def cite_html(src, depth):
    if not src or not src.get("document_source"): return ""
    return ' <a class="src" href="%s" target="_blank" rel="noopener">[%s]</a>' % (html.escape(pdf_href(src["document_source"], src.get("page"), depth) or ""), html.escape(src_label(src)))

# ------------------------------------------------------------------ MODÈLE NORMALISÉ (projection JSON)
# Catégories issues de la vue humaine (résumé humain court).
RH_CATS = [
    ("garanties", "Garanties", "garanties_principales"),
    ("exclusions", "Exclusions", "exclusions_importantes"),
    ("options", "Options", "options"),
    ("cotisations", "Cotisations & prix", "cotisations_prix"),
    ("delais", "Délais & franchises", "delais_franchises"),
    ("fiscalite", "Fiscalité", "fiscalite"),
    ("points-vigilance", "Points de vigilance", "points_de_vigilance"),
    ("formules", "Formules", "formules"),
]
ELEMENTS = {k: [] for k, _, _ in RH_CATS}
ELEMENTS.update({"definitions": [], "conditions": [], "faits": [], "declencheurs": [], "plafonds": [], "franchises": []})
CONTRACT_META = []

def txt_of(f):
    return f.get("resume_humain") or f.get("texte") or f.get("description") or ""

for c in CONTRATS:
    csl = slug(c.get("nom"))
    CONTRACT_META.append({"id": c.get("id") or ("contrat-" + csl), "slug": csl, "nom": c.get("nom"),
                          "famille": c.get("famille"), "type": c.get("type_contrat"), "date": c.get("date_document"),
                          "assureur": c.get("assureur"), "resume": c.get("resume_neutre"), "minimal": c.get("_minimal")})
    for k, _, jkey in RH_CATS:
        for i, f in enumerate(c.get(jkey) or []):
            if isinstance(f, str):
                if f.strip(): ELEMENTS[k].append({"id": csl + ":" + k + ":" + sid(f, i), "contrat": c.get("nom"), "cslug": csl, "titre": "", "texte": f, "cond": [], "lim": [], "src": None})
                continue
            t = f.get("titre") or f.get("nom") or ""
            if str(t).startswith("_"): t = ""
            body = txt_of(f)
            if not body and k == "formules":  # les formules ont nom/usage/formule (pas resume_humain)
                body = " · ".join(str(x) for x in [f.get("usage"), f.get("formule"),
                        ("ex : " + str(f.get("exemple_chiffre"))) if f.get("exemple_chiffre") else "",
                        ("justification : " + str(f.get("justification"))) if f.get("justification") else ""] if x)
            if not t and not body: continue
            ELEMENTS[k].append({"id": f.get("id") or (csl + ":" + k + ":" + sid(t, body, i)), "contrat": c.get("nom"), "cslug": csl,
                                "titre": t, "texte": body, "cond": [x for x in (f.get("conditions_importantes") or []) if x],
                                "lim": [x for x in (f.get("limites_exclusions") or []) if x], "src": f.get("source")})
    d = find_derived(c)
    if d:
        for x in (d.get("definitions") or []):
            if x.get("terme"): ELEMENTS["definitions"].append({"id": x.get("id") or (csl + ":def:" + sid(x.get("terme"))), "contrat": c.get("nom"), "cslug": csl, "titre": x.get("terme"), "texte": x.get("definition") or "", "cond": [], "lim": [], "src": x.get("source")})
        for x in (d.get("conditions_souscription") or []):
            if x.get("texte"): ELEMENTS["conditions"].append({"id": x.get("id") or (csl + ":cond:" + sid(x.get("texte"))), "contrat": c.get("nom"), "cslug": csl, "titre": "", "texte": x.get("texte"), "cond": [], "lim": [], "src": x.get("source")})
        for fi, f in enumerate(d.get("faits") or []):
            fid = f.get("id") or (csl + ":fait:" + sid(f.get("titre"), fi))
            ELEMENTS["faits"].append({"id": fid, "contrat": c.get("nom"), "cslug": csl, "titre": f.get("titre") or "", "texte": f.get("description") or "", "categorie": f.get("categorie") or "", "src": f.get("source"),
                                      "declencheurs": f.get("declencheurs") or [], "plafonds": f.get("plafonds") or [], "franchises": f.get("franchises") or []})
            for tkey in ("declencheurs", "plafonds", "franchises"):
                for i, v in enumerate(f.get(tkey) or []):
                    ELEMENTS[tkey].append({"id": fid + ":" + tkey[:-1] + ":" + str(i), "contrat": c.get("nom"), "cslug": csl, "titre": f.get("titre") or "", "texte": v, "cond": [], "lim": [], "src": f.get("source")})

GLOSSAIRE = FICHES.get("glossaire") or []
PDFS = PDFIDX.get("pdfs") or []

# Sources distinctes (document_source + page) sur tous les éléments.
SOURCES = {}
def add_src(src, ref):
    if not src or not src.get("document_source"): return
    key = (str(src["document_source"]), str(src.get("page") or ""))
    SOURCES.setdefault(key, {"document_source": src["document_source"], "page": src.get("page"), "refs": []})["refs"].append(ref)
for k in ELEMENTS:
    for e in ELEMENTS[k]:
        add_src(e.get("src"), (e["contrat"], k))
for g in GLOSSAIRE:
    for en in (g.get("entrees") or []): add_src(en.get("source"), (en.get("contrat"), "definition"))

# ------------------------------------------------------------------ gabarit HTML / MD
CATS_NAV = [("index", "Index"), ("guide-ia", "Guide IA"), ("contrats", "Contrats"), ("garanties", "Garanties"),
            ("exclusions", "Exclusions"), ("definitions", "Définitions"), ("conditions", "Conditions"),
            ("declencheurs", "Déclencheurs"), ("plafonds", "Plafonds"), ("franchises", "Franchises"),
            ("glossaire", "Glossaire"), ("themes", "Thèmes"), ("notices", "Notices"), ("sources", "Sources"),
            ("pack-a", "Pack A"), ("pack-b", "Pack B"), ("couverture", "Couverture")]
def nav_html(depth):
    ip = int_pref(depth)
    return '<nav class="ianav">' + " · ".join('<a href="%s%s.html">%s</a>' % (ip, k, l) for k, l in CATS_NAV) + '</nav>'

def page_html(title, body, depth, canonical):
    ip = int_pref(depth)
    return ('<!doctype html>\n<html lang="fr"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>%s — Gabriel AXA (Vue IA)</title>'
            '<meta name="description" content="Vue IA de Gabriel AXA — projection statique, sourcée, lisible sans JavaScript.">'
            '<link rel="canonical" href="%s"><link rel="stylesheet" href="%sia.css"></head>\n<body>\n%s\n<main>\n%s\n</main>\n'
            '<footer><p>Gabriel AXA — Vue IA v%s (%s). Projection des JSON (source de vérité) ; masters non modifiés ; '
            'données de sources publiques. La notice PDF fait foi. <a href="%s../">← Application</a></p></footer>\n</body></html>\n') % (
            html.escape(title), html.escape(canonical), ip, nav_html(depth), body, VERSION, DATE, ip)

HDR = {
    "regles": "Pack A = preuve contractuelle. Pack B = raisonnement (jamais une preuve seule). Toujours citer la source (notice, page). Ne jamais inventer ; si une information est absente, le dire. La notice PDF fait foi.",
    "limites": "Certains tableaux chiffrés (valeurs de rachat, barèmes) sont à vérifier dans la notice. La notice PDF reste la seule source qui fait foi.",
}
def md_hdr(title, objectif):
    return "\n".join(["# %s" % title, "",
        "> **Vue IA de Gabriel AXA** — projection statique des JSON, lisible sans JavaScript. Générée le %s (v%s)." % (DATE, VERSION),
        "> Masters non modifiés ; données de sources publiques ; **la notice PDF fait foi.**", "",
        "**Objectif.** %s" % objectif, "", "**Règles.** %s" % HDR["regles"], "", "**Limites.** %s" % HDR["limites"], ""])

def write(rel, content):
    full = os.path.join(IA, rel); os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f: f.write(content)

# ------------------------------------------------------------------ rendu d'éléments
def notice_href_for(cslug, depth):
    for p in PDFS:
        if slug(p.get("nom_contrat")) == cslug and str(p.get("path", "")).startswith("data/"):
            return data_pref(depth) + quote(p["path"])
    return None

def el_md(e, depth, with_contract=False):
    head = ("**%s** — %s" % (e["titre"], e["texte"])) if e.get("titre") and e["texte"] else (e.get("titre") or e["texte"] or "")
    pre = ("[%s] " % e["contrat"]) if with_contract and e.get("contrat") else ""
    line = "- %s%s%s `#%s`" % (pre, head.strip(), cite_md(e.get("src"), depth), e["id"])
    subs = ["  - Condition : " + str(x) for x in e.get("cond", [])] + ["  - Limite : " + str(x) for x in e.get("lim", [])]
    return "\n".join([line] + subs)
def el_html(e, depth, with_contract=False):
    head = ("<strong>%s</strong> — %s" % (html.escape(e["titre"]), html.escape(e["texte"]))) if e.get("titre") and e["texte"] else html.escape(e.get("titre") or e["texte"] or "")
    pre = ('<a href="%scontrat/%s.html">%s</a> : ' % (int_pref(depth), e["cslug"], html.escape(e["contrat"]))) if with_contract and e.get("contrat") else ""
    sub = ""
    if e.get("cond") or e.get("lim"):
        sub = "<ul>" + "".join("<li>Condition : %s</li>" % html.escape(str(x)) for x in e.get("cond", [])) + "".join("<li>Limite : %s</li>" % html.escape(str(x)) for x in e.get("lim", [])) + "</ul>"
    return '<li id="%s">%s%s%s%s</li>' % (html.escape(e["id"]), pre, head, cite_html(e.get("src"), depth), sub)

# ------------------------------------------------------------------ PAGES
def build_contract_pages():
    for cm in CONTRACT_META:
        c = next(x for x in CONTRATS if slug(x.get("nom")) == cm["slug"])
        d = find_derived(c)
        depth = 1
        meta = " · ".join(x for x in [cm["type"], cm["famille"], cm["date"], cm["assureur"]] if x)
        # MD
        md = [md_hdr(cm["nom"], "Fiche IA complète et sourcée du contrat « %s »." % cm["nom"]),
              "_ID : `%s`_  ·  _Famille : %s_" % (cm["id"], cm["famille"] or "—"), ""]
        if meta: md.append("_%s_\n" % meta)
        if cm["resume"]: md += ["## Résumé", "", cm["resume"], ""]
        blocks = [(lbl, [e for e in ELEMENTS[k] if e["cslug"] == cm["slug"]]) for k, lbl, _ in RH_CATS]
        blocks += [("Définitions", [e for e in ELEMENTS["definitions"] if e["cslug"] == cm["slug"]]),
                   ("Conditions de souscription", [e for e in ELEMENTS["conditions"] if e["cslug"] == cm["slug"]])]
        if cm["minimal"] or not any(items for _, items in blocks):
            md.append("> ⚠ Données limitées pour ce contrat dans la base dérivée ; se référer à la notice PDF. Aucune information n'est comblée.\n")
        for lbl, items in blocks:
            if items: md += ["## %s (%d)" % (lbl, len(items)), "", "\n".join(el_md(e, depth) for e in items), ""]
        faits = [e for e in ELEMENTS["faits"] if e["cslug"] == cm["slug"]]
        if faits:
            md += ["## Faits détaillés — résumé IA complet (%d)" % len(faits), ""]
            for f in faits:
                md.append("- **%s** (%s) — %s%s `#%s`" % (f["titre"], f.get("categorie", ""), f["texte"], cite_md(f.get("src"), depth), f["id"]))
                for tk, tl in [("declencheurs", "Déclencheurs"), ("plafonds", "Plafonds"), ("franchises", "Franchises")]:
                    if f.get(tk): md.append("  - %s : %s" % (tl, " · ".join(f[tk])))
            md.append("")
        nu = notice_href_for(cm["slug"], depth)
        if nu: md += ["## Notice", "", "**Notice PDF (fait foi) :** [%s](%s)" % (cm["nom"], nu), ""]
        md += ["## Navigation", "", "- [← Contrats](%scontrats.md)  ·  [Garanties](%sgaranties.md)  ·  [Exclusions](%sexclusions.md)  ·  [Définitions](%sdefinitions.md)  ·  [Thèmes](%sthemes.md)  ·  [Notices](%snotices.md)" % ((int_pref(depth),) * 6)]
        write("contrat/%s.md" % cm["slug"], "\n".join(md))
        # HTML
        H = []
        H.append('<h1 id="%s">%s</h1>' % (html.escape(cm["id"]), html.escape(cm["nom"])))
        H.append('<p class="meta">ID : <code>%s</code> · Famille : %s%s</p>' % (html.escape(cm["id"]), html.escape(cm["famille"] or "—"), (" · " + html.escape(meta)) if meta else ""))
        if cm["resume"]: H.append("<h2>Résumé</h2><p>%s</p>" % html.escape(cm["resume"]))
        if cm["minimal"] or not any(items for _, items in blocks):
            H.append('<p class="warn">⚠ Données limitées pour ce contrat ; se référer à la notice PDF. Aucune information n\'est comblée.</p>')
        for lbl, items in blocks:
            if items: H.append("<h2>%s (%d)</h2><ul>%s</ul>" % (html.escape(lbl), len(items), "".join(el_html(e, depth) for e in items)))
        if faits:
            H.append("<h2>Faits détaillés — résumé IA complet (%d)</h2><ul>" % len(faits))
            for f in faits:
                extra = "".join("<li>%s : %s</li>" % (tl, html.escape(" · ".join(f[tk]))) for tk, tl in [("declencheurs", "Déclencheurs"), ("plafonds", "Plafonds"), ("franchises", "Franchises")] if f.get(tk))
                H.append('<li id="%s"><strong>%s</strong> (%s) — %s%s%s</li>' % (html.escape(f["id"]), html.escape(f["titre"]), html.escape(f.get("categorie", "")), html.escape(f["texte"]), cite_html(f.get("src"), depth), ("<ul>" + extra + "</ul>") if extra else ""))
            H.append("</ul>")
        if nu: H.append('<h2>Notice</h2><p><strong>Notice PDF (fait foi) :</strong> <a href="%s" target="_blank" rel="noopener">%s</a></p>' % (html.escape(nu), html.escape(cm["nom"])))
        ip = int_pref(depth)
        H.append('<h2>Navigation</h2><p><a href="%scontrats.html">← Contrats</a> · <a href="%sgaranties.html">Garanties</a> · <a href="%sexclusions.html">Exclusions</a> · <a href="%sdefinitions.html">Définitions</a> · <a href="%sthemes.html">Thèmes</a> · <a href="%snotices.html">Notices</a></p>' % ((ip,) * 6))
        write("contrat/%s.html" % cm["slug"], page_html(cm["nom"], "\n".join(H), depth, SITE + "/ia/contrat/%s.html" % cm["slug"]))

def build_category(key, label, objectif):
    items = ELEMENTS[key]; depth = 0
    md = [md_hdr("%s — toutes (%d)" % (label, len(items)), objectif), ""]
    hb = ['<h1>%s — toutes (%d)</h1><p>%s</p>' % (html.escape(label), len(items), html.escape(objectif))]
    by = {}
    for e in items: by.setdefault(e["contrat"], []).append(e)
    for contrat in sorted(by, key=norm):
        cslug = slug(contrat)
        md += ["## %s (%d)" % (contrat, len(by[contrat])), "", "\n".join(el_md(e, depth) for e in by[contrat]), ""]
        hb.append('<h2><a href="contrat/%s.html">%s</a> (%d)</h2><ul>%s</ul>' % (cslug, html.escape(contrat), len(by[contrat]), "".join(el_html(e, depth) for e in by[contrat])))
    write("%s.md" % key, "\n".join(md)); write("%s.html" % key, page_html(label, "".join(hb), depth, SITE + "/ia/%s.html" % key))

def build_glossaire():
    depth = 0
    md = [md_hdr("Glossaire complet (%d termes)" % len(GLOSSAIRE), "Tous les termes définis dans les notices AXA, regroupés et sourcés.")]
    hb = ['<h1>Glossaire complet (%d termes)</h1>' % len(GLOSSAIRE)]
    for g in GLOSSAIRE:
        gid = "gloss-" + slug(g.get("terme"))
        md += ["## %s" % g.get("terme", ""), ""]
        hb.append('<h2 id="%s">%s</h2><ul>' % (html.escape(gid), html.escape(g.get("terme", ""))))
        for e in (g.get("entrees") or []):
            md.append("- **%s** : %s%s" % (e.get("contrat", ""), e.get("definition", ""), cite_md(e.get("source"), depth)))
            hb.append('<li><a href="contrat/%s.html">%s</a> : %s%s</li>' % (slug(e.get("contrat")), html.escape(e.get("contrat", "")), html.escape(e.get("definition", "")), cite_html(e.get("source"), depth)))
        md.append(""); hb.append("</ul>")
    write("glossaire.md", "\n".join(md)); write("glossaire.html", page_html("Glossaire", "".join(hb), depth, SITE + "/ia/glossaire.html"))

def build_notices():
    depth = 0
    md = [md_hdr("Notices contractuelles (%d)" % len(PDFS), "Toutes les notices PDF — la source qui fait foi.")]
    hb = ['<h1>Notices contractuelles (%d)</h1><p>Documents qui font foi.</p><ul>' % len(PDFS)]
    for p in PDFS:
        u = data_pref(depth) + quote(p["path"]) if str(p.get("path", "")).startswith("data/") else None
        nom = p.get("nom_contrat") or ""; fich = p.get("nom_fichier") or str(p.get("path", "")).split("/")[-1]
        pages = (" · %s p." % p["pages"]) if p.get("pages") else ""
        md.append("- **%s** — %s%s%s" % (nom, fich, pages, (" [ouvrir](%s)" % u) if u else ""))
        hb.append('<li><strong>%s</strong> — %s%s%s</li>' % (html.escape(nom), html.escape(fich), html.escape(pages), (' — <a href="%s" target="_blank" rel="noopener">ouvrir</a>' % html.escape(u)) if u else ""))
    write("notices.md", "\n".join(md)); write("notices.html", page_html("Notices", "".join(hb) + "</ul>", depth, SITE + "/ia/notices.html"))

def build_sources():
    depth = 0; items = sorted(SOURCES.values(), key=lambda s: (str(s["document_source"]), str(s.get("page") or "")))
    md = [md_hdr("Sources (%d références distinctes)" % len(items), "Toutes les sources citées (notice + page) et les contenus qui s'y rattachent.")]
    hb = ['<h1>Sources (%d références distinctes)</h1>' % len(items) + "<ul>"]
    for s in items:
        base = str(s["document_source"]).split("/")[-1]
        u = pdf_href(s["document_source"], s.get("page"), depth)
        cnt = len(s["refs"])
        md.append("- **%s**%s — %d élément(s) [ouvrir](%s)" % (base, ", p." + str(s["page"]) if s.get("page") else "", cnt, u))
        hb.append('<li><strong>%s</strong>%s — %d élément(s) — <a href="%s" target="_blank" rel="noopener">ouvrir</a></li>' % (html.escape(base), (", p." + html.escape(str(s["page"]))) if s.get("page") else "", cnt, html.escape(u)))
    write("sources.md", "\n".join(md)); write("sources.html", page_html("Sources", "".join(hb) + "</ul>", depth, SITE + "/ia/sources.html"))

def build_recherches():
    depth = 0; sugg = SEARCH.get("suggestions") or SEARCH.get("items") or []
    def label(x): return x if isinstance(x, str) else (x.get("texte") or x.get("label") or x.get("q") or x.get("requete") or json.dumps(x, ensure_ascii=False))
    md = [md_hdr("Recherches suggérées (%d)" % len(sugg), "Exemples de recherches courantes des conseillers (suggestions). Aide à formuler une requête.")]
    hb = ['<h1>Recherches suggérées (%d)</h1><ul>' % len(sugg)]
    for x in sugg:
        md.append("- %s" % label(x)); hb.append("<li>%s</li>" % html.escape(str(label(x))))
    write("recherches.md", "\n".join(md)); write("recherches.html", page_html("Recherches", "".join(hb) + "</ul>", depth, SITE + "/ia/recherches.html"))

THEMES = [
    ("invalidite", "Invalidité", ["invalidit", "ipt", "ipp", "ptia", "incapacit"]),
    ("deces", "Décès", ["deces", "décès", "mortalit", "capital deces"]),
    ("hospitalisation", "Hospitalisation", ["hospitalis"]),
    ("rachat", "Rachat", ["rachat", "valeur de rachat", "mise en reduction", "reduction"]),
    ("souscription", "Souscription", ["souscription", "adhesion", "adherer", "formalite", "age a l", "questionnaire"]),
    ("fiscalite", "Fiscalité", ["fiscal", "990 i", "757 b", "impot", "succession", "abattement", "cgi"]),
    ("association", "Association", ["association", "anpere", "gestion paritaire", "adherent"]),
    ("anpere", "ANPERE", ["anpere"]),
]
def build_themes():
    depth0 = 0
    all_el = []
    for k in ELEMENTS:
        for e in ELEMENTS[k]: all_el.append((k, e))
    # index thèmes
    md = [md_hdr("Thèmes — index transversal", "Vues transversales agrégeant automatiquement l'information de tous les contrats par thème.")]
    hb = ['<h1>Thèmes — index transversal</h1><ul>']
    counts = {}
    for tk, tl, kws in THEMES:
        matches = [(k, e) for k, e in all_el if any(w in norm(e.get("titre", "") + " " + e.get("texte", "")) for w in kws)]
        counts[tk] = len(matches)
        md.append("- [%s](themes/%s.md) — %d éléments" % (tl, tk, len(matches)))
        hb.append('<li><a href="themes/%s.html">%s</a> — %d éléments</li>' % (tk, html.escape(tl), len(matches)))
        # page thème
        depth = 1
        mmd = [md_hdr("Thème : %s" % tl, "Toutes les informations liées à « %s » agrégées depuis les contrats." % tl)]
        by = {}
        for k, e in matches: by.setdefault(e["contrat"], []).append((k, e))
        for contrat in sorted(by, key=norm):
            mmd += ["## %s (%d)" % (contrat, len(by[contrat])), "", "\n".join(el_md(e, depth) + "  _(%s)_" % k for k, e in by[contrat]), ""]
        mmd += ["## Navigation", "", "- [← Thèmes](%sthemes.md) · [Contrats](%scontrats.md) · [Garanties](%sgaranties.md)" % ((int_pref(depth),) * 3)]
        write("themes/%s.md" % tk, "\n".join(mmd))
        HB = ['<h1>Thème : %s</h1><p>Agrégation automatique depuis les contrats (%d éléments).</p>' % (html.escape(tl), len(matches))]
        for contrat in sorted(by, key=norm):
            HB.append('<h2><a href="%scontrat/%s.html">%s</a> (%d)</h2><ul>%s</ul>' % (int_pref(depth), slug(contrat), html.escape(contrat), len(by[contrat]), "".join(el_html(e, depth, ) for k, e in by[contrat])))
        HB.append('<h2>Navigation</h2><p><a href="%sthemes.html">← Thèmes</a> · <a href="%scontrats.html">Contrats</a></p>' % (int_pref(depth), int_pref(depth)))
        write("themes/%s.html" % tk, page_html("Thème : " + tl, "".join(HB), depth, SITE + "/ia/themes/%s.html" % tk))
    write("themes.md", "\n".join(md)); write("themes.html", page_html("Thèmes", "".join(hb) + "</ul>", depth0, SITE + "/ia/themes.html"))
    return counts

def build_contrats_list():
    depth = 0
    md = [md_hdr("Contrats (%d)" % len(CONTRACT_META), "Liste complète et accès à la fiche IA de chaque contrat.")]
    hb = ['<h1>Contrats (%d)</h1><ul>' % len(CONTRACT_META)]
    for cm in CONTRACT_META:
        md.append("- [%s](contrat/%s.md) — %s `#%s`" % (cm["nom"], cm["slug"], cm["famille"] or "", cm["id"]))
        hb.append('<li><a href="contrat/%s.html">%s</a>%s — <a href="contrat/%s.md">.md</a></li>' % (cm["slug"], html.escape(cm["nom"]), (" (%s)" % html.escape(cm["famille"])) if cm["famille"] else "", cm["slug"]))
    write("contrats.md", "\n".join(md)); write("contrats.html", page_html("Contrats", "".join(hb) + "</ul>", depth, SITE + "/ia/contrats.html"))
    write("contrats.json", json.dumps({"meta": {"produit": "Gabriel AXA", "version": VERSION, "genere_le": DATE, "contrats": len(CONTRATS), "note": "Projection dérivée ; masters non modifiés ; la notice PDF fait foi."}, "contrats": CONTRATS}, ensure_ascii=False, indent=1))
    write("glossaire.json", json.dumps({"meta": {"version": VERSION, "genere_le": DATE, "termes": len(GLOSSAIRE)}, "glossaire": GLOSSAIRE}, ensure_ascii=False, indent=1))

def build_packs():
    depth = 0
    # Pack A = toutes les fiches contrat (résumé + rubriques), en une page.
    parts_md, parts_html = [], []
    for cm in CONTRACT_META:
        d = find_derived(next(x for x in CONTRATS if slug(x.get("nom")) == cm["slug"]))
        parts_md.append("## %s" % cm["nom"])
        if cm["resume"]: parts_md.append("\n" + cm["resume"])
        for k, lbl, _ in RH_CATS + [("definitions", "Définitions", ""), ("conditions", "Conditions de souscription", "")]:
            its = [e for e in ELEMENTS[k] if e["cslug"] == cm["slug"]]
            if its: parts_md.append("\n### %s (%d)\n\n%s" % (lbl, len(its), "\n".join(el_md(e, depth) for e in its)))
        parts_html.append("<section><h2>%s</h2>%s%s</section>" % (html.escape(cm["nom"]), ("<p>%s</p>" % html.escape(cm["resume"])) if cm["resume"] else "",
            "".join("<h3>%s (%d)</h3><ul>%s</ul>" % (html.escape(lbl), len([e for e in ELEMENTS[k] if e["cslug"] == cm["slug"]]), "".join(el_html(e, depth) for e in ELEMENTS[k] if e["cslug"] == cm["slug"]))
                    for k, lbl, _ in RH_CATS + [("definitions", "Définitions", ""), ("conditions", "Conditions de souscription", "")] if [e for e in ELEMENTS[k] if e["cslug"] == cm["slug"]])))
    write("pack-a.md", md_hdr("Pack A — restitution complète", "Toutes les données contractuelles (Pack A) de tous les contrats, sourcées.") + "\nFichier brut : [Pack A JSON](%sdata/AXA/AXA_MASTER_DONNEES_PACK_A_STABLE.json)\n\n" % data_pref(depth) + "\n\n".join(parts_md))
    write("pack-a.html", page_html("Pack A", '<h1>Pack A — restitution complète</h1><p>Toutes les données contractuelles, sourcées. Brut : <a href="%sdata/AXA/AXA_MASTER_DONNEES_PACK_A_STABLE.json" download>Pack A JSON</a> · <a href="pack-a.md">pack-a.md</a></p>%s' % (data_pref(depth), "".join(parts_html)), depth, SITE + "/ia/pack-a.html"))
    # Pack B = Pack A + raisonnement (branches lisibles du master B ; JSON brut fait foi si tronqué).
    B_BRANCHES = ["mode_navigation_ia", "arbres_decision", "regles_transverses_et_garde_fous", "modeles_reponse_par_question",
                  "modeles_reponse_client_v2_6", "raisonnements_complexes", "matrices_croisement_avance", "profils_reponse",
                  "tests_minimum_et_criteres_eliminatoires", "trous_connus_et_limites"]
    def wmd(v, dep=0, cnt=[0]):
        if cnt[0] > 12000: return ""
        pad = "  " * dep; out = []
        if isinstance(v, dict):
            for k, val in v.items():
                if isinstance(val, (dict, list)): out.append("%s- **%s** :" % (pad, k)); out.append(wmd(val, dep + 1, cnt))
                else: cnt[0] += 1; out.append("%s- **%s** : %s" % (pad, k, val))
        elif isinstance(v, list):
            for it in v: out.append(wmd(it, dep, cnt) if isinstance(it, (dict, list)) else (cnt.__setitem__(0, cnt[0] + 1) or "%s- %s" % (pad, it)))
        return "\n".join(x for x in out if x)
    def whtml(v, cnt=[0]):
        if cnt[0] > 12000: return ""
        if isinstance(v, dict): return "<ul>" + "".join("<li><strong>%s</strong>%s</li>" % (html.escape(str(k)), (" : " + html.escape(str(val))) if not isinstance(val, (dict, list)) else whtml(val, cnt)) for k, val in v.items()) + "</ul>"
        if isinstance(v, list): return "<ul>" + "".join("<li>%s</li>" % (html.escape(str(it)) if not isinstance(it, (dict, list)) else whtml(it, cnt)) for it in v) + "</ul>"
        return html.escape(str(v))
    bmd = "\n\n".join("### %s\n\n%s" % (br, wmd(PACKB[br], 0, [0])) for br in B_BRANCHES if br in PACKB)
    bhtml = "".join("<h3>%s</h3>%s" % (html.escape(br), whtml(PACKB[br], [0])) for br in B_BRANCHES if br in PACKB)
    write("pack-b.md", md_hdr("Pack B — restitution exhaustive", "Pack A + couches de raisonnement (Pack B). JSON brut fait foi pour l'intégralité.") +
          "\n> Pack B = Pack A + raisonnement. JSON brut : [Pack B](%sdata/AXA/AXA_MASTER_DONNEES_PACK_B_MATRICES_EXPERIMENTAL.json).\n\n## 1. Pack A\n\n" % data_pref(depth) + "\n\n".join(parts_md) + "\n\n## 2. Raisonnement (Pack B)\n\n" + bmd)
    write("pack-b.html", page_html("Pack B", '<h1>Pack B — restitution exhaustive</h1><blockquote>Pack B = Pack A + raisonnement. Brut : <a href="%sdata/AXA/AXA_MASTER_DONNEES_PACK_B_MATRICES_EXPERIMENTAL.json" download>Pack B JSON</a> (fait foi) · <a href="pack-b.md">pack-b.md</a></blockquote><h2>1. Pack A</h2>%s<h2>2. Raisonnement (Pack B)</h2>%s' % (data_pref(depth), "".join(parts_html), bhtml), depth, SITE + "/ia/pack-b.html"))

GUIDE_MD = """# Guide IA — comment utiliser Gabriel AXA

> Page destinée à une IA ou un agent. Explique comment travailler à partir de la Vue IA seule.

## Comment utiliser Gabriel AXA
La Vue IA est la **projection complète et sourcée** de la base contractuelle AXA. Tu peux travailler
**uniquement** depuis ces pages (HTML/Markdown) sans les JSON. Chaque affirmation contractuelle porte
sa source (notice + page).

## Comment répondre
- Réponds **uniquement** à partir des contenus présents, **avec leur source** (notice, page).
- **Pack A = preuve** ; **Pack B = raisonnement** (jamais cité seul comme preuve).
- Sépare clairement ce qui est **contractuel** (Pack A / notice) de ce qui est **raisonnement** (Pack B).
- Termine en renvoyant à la **notice PDF**, qui fait foi.

## Comment rechercher
1. Par contrat : `/ia/contrats.html` → `/ia/contrat/<slug>.html`.
2. Par catégorie : `/ia/garanties.html`, `/ia/exclusions.html`, `/ia/definitions.html`, `/ia/conditions.html`,
   `/ia/declencheurs.html`, `/ia/plafonds.html`, `/ia/franchises.html`.
3. Par thème : `/ia/themes.html` (invalidité, décès, hospitalisation, rachat, souscription, fiscalité, association, ANPERE).
4. Glossaire : `/ia/glossaire.html`. Sources : `/ia/sources.html`. Notices : `/ia/notices.html`.

## Quand citer
**Toujours**, dès qu'une information est contractuelle. Format : `[Notice : <fichier>, p.<page>]` (lien vers le PDF).
Chaque élément possède aussi un **identifiant stable** (`#<id>`) réutilisable pour référencer précisément.

## Comment arbitrer entre plusieurs contrats
Compare via les pages catégorie ou thème (qui agrègent tous les contrats). Ne mélange jamais les garanties
d'un contrat avec un autre : chaque élément indique son contrat. En cas de doute, ouvre les deux fiches contrat.

## Comment gérer une absence d'information
Si l'information n'apparaît pas dans la Vue IA : dis-le explicitement (« non présent dans la base Gabriel AXA »),
propose la notice PDF du contrat, **n'invente pas**.

## Comment utiliser les liens
- Contrat → ses garanties/définitions (mêmes pages, ancres `#id`) → **notice** → **page PDF** exacte (`#page=`).
- Catégorie/Thème → lien vers le contrat concerné → retour thème.
Suis la hiérarchie : **Index → Contrat/Catégorie/Thème → Élément → Notice → Page PDF**.

## Hiérarchie d'autorité
1. **Notice PDF** (fait foi). 2. **Pack A** (donnée contractuelle dérivée, à citer). 3. **Glossaire** (définitions sourcées).
4. **Pack B** (raisonnement ; jamais une preuve seule).

## Exemple de BONNE réponse
« Pour MasterLife, le décès accidentel double le capital (Notice MasterLife, p.6). À confirmer sur la notice. »

## Exemple de MAUVAISE réponse
« Oui, remboursé à 100 %. » — aucune source, non vérifiable, invention possible.
"""

def build_static_pages(theme_counts):
    depth = 0
    write("guide-ia.md", GUIDE_MD)
    write("guide-ia.html", page_html("Guide IA", renderish(GUIDE_MD), depth, SITE + "/ia/guide-ia.html"))
    # Manifeste lisible + ai-manifest.json
    pages = ["index", "guide-ia", "manifeste", "pack-a", "pack-b", "contrats", "garanties", "exclusions", "options",
             "cotisations", "delais", "fiscalite", "points-vigilance", "formules", "definitions", "conditions",
             "declencheurs", "plafonds", "franchises", "glossaire", "notices", "sources", "recherches", "themes", "couverture"]
    manifest = {
        "name": "Gabriel AXA — Vue IA", "version": VERSION, "generated": DATE, "base_url": SITE + "/ia/",
        "authority": "La notice PDF fait foi. Ordre : notice PDF > Pack A > glossaire > Pack B.",
        "organisation": "Projection statique des JSON (source de vérité). Une page par contrat, une page par catégorie "
                        "(garanties, exclusions, définitions, conditions, déclencheurs, plafonds, franchises…), des vues "
                        "thématiques transversales, glossaire, notices, sources. Rien n'est dupliqué manuellement.",
        "how_to_cite": "[Notice : <fichier>, p.<page>](<url PDF>). Chaque élément a un id stable réutilisable (#<id>).",
        "hierarchy": ["index", "contrat|categorie|theme", "element (#id)", "notice", "page PDF (#page=)"],
        "rules": ["Pack A = preuve", "Pack B = raisonnement (jamais une preuve seule)", "Toujours citer la source",
                  "Ne jamais inventer ; signaler l'absence", "La notice PDF fait foi"],
        "data_origin": "Documents publics (notices / CG AXA). Aucune donnée client. Couches dérivées ; masters non modifiés.",
        "entry_point": SITE + "/ia/guide-ia.html",
        "pages": [{"id": p, "html": SITE + "/ia/%s.html" % p, "md": SITE + "/ia/%s.md" % p} for p in pages if p != "manifeste"],
        "contracts": [{"slug": cm["slug"], "id": cm["id"], "nom": cm["nom"], "famille": cm["famille"],
                       "html": SITE + "/ia/contrat/%s.html" % cm["slug"], "md": SITE + "/ia/contrat/%s.md" % cm["slug"]} for cm in CONTRACT_META],
        "themes": [{"slug": tk, "nom": tl, "html": SITE + "/ia/themes/%s.html" % tk} for tk, tl, _ in THEMES],
        "raw_data": {"pack_a": SITE + "/data/AXA/AXA_MASTER_DONNEES_PACK_A_STABLE.json",
                     "pack_b": SITE + "/data/AXA/AXA_MASTER_DONNEES_PACK_B_MATRICES_EXPERIMENTAL.json",
                     "contrats": SITE + "/ia/contrats.json", "glossaire": SITE + "/ia/glossaire.json"},
        "conventions": {"slug": "minuscules, sans accents, séparateur '-' ; stable entre versions",
                        "id": "id JSON d'origine si présent, sinon dérivé déterministe (stable)",
                        "citation": "[Notice : <fichier>, p.<page>]"},
        "sitemap": SITE + "/ia/sitemap-ia.xml", "coverage": SITE + "/ia/couverture.html",
    }
    write("ai-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1))
    man_md = md_hdr("Manifeste IA", "Comment la base est organisée, quelles pages existent, comment citer, quelle hiérarchie suivre, quelle page fait autorité.") + """
## Organisation
%s

## Autorité
%s

## Comment citer
%s

## Hiérarchie de navigation
Index → (Contrat | Catégorie | Thème) → Élément `#id` → Notice → Page PDF `#page=`.

## Pages disponibles
%s

## Fichiers machine
- [ai-manifest.json](ai-manifest.json) · [sitemap-ia.xml](sitemap-ia.xml) · [robots.txt](robots.txt)
- [contrats.json](contrats.json) · [glossaire.json](glossaire.json)
- Masters bruts : [Pack A](../data/AXA/AXA_MASTER_DONNEES_PACK_A_STABLE.json) · [Pack B](../data/AXA/AXA_MASTER_DONNEES_PACK_B_MATRICES_EXPERIMENTAL.json)
""" % (manifest["organisation"], manifest["authority"], manifest["how_to_cite"],
       "\n".join("- [%s](%s.html) · [.md](%s.md)" % (p, p, p) for p in pages if p != "manifeste"))
    write("manifeste.md", man_md)
    write("manifeste.html", page_html("Manifeste IA", renderish(man_md), depth, SITE + "/ia/manifeste.html"))
    # sitemap + robots
    urls = [SITE + "/ia/%s.html" % p for p in pages] + [SITE + "/ia/%s.md" % p for p in pages if p != "manifeste"]
    urls += [SITE + "/ia/contrat/%s.html" % cm["slug"] for cm in CONTRACT_META] + [SITE + "/ia/contrat/%s.md" % cm["slug"] for cm in CONTRACT_META]
    urls += [SITE + "/ia/themes/%s.html" % tk for tk, _, _ in THEMES]
    urls += [SITE + "/ia/ai-manifest.json", SITE + "/ia/contrats.json", SITE + "/ia/glossaire.json"]
    write("sitemap-ia.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
          "".join("<url><loc>%s</loc><lastmod>%s</lastmod></url>\n" % (html.escape(u), DATE) for u in urls) + "</urlset>\n")
    write("robots.txt", "User-agent: *\nAllow: /\nSitemap: %s/ia/sitemap-ia.xml\n" % SITE)
    # index global
    idx_md = md_hdr("Gabriel AXA — Vue IA", "Point d'entrée de la couche IA : commencer ici, puis naviguer.") + """
## Commencer (pour une IA)
- **[Guide IA](guide-ia.html)** — comment utiliser Gabriel AXA (règles, arbitrage, absence, liens).
- **[Manifeste IA](manifeste.html)** — organisation, citation, hiérarchie, autorité.

## Données
- [Contrats](contrats.html) (%(nc)d) · [Pack A](pack-a.html) · [Pack B](pack-b.html)
- Catégories : [Garanties](garanties.html) · [Exclusions](exclusions.html) · [Options](options.html) ·
  [Définitions](definitions.html) · [Conditions](conditions.html) · [Déclencheurs](declencheurs.html) ·
  [Plafonds](plafonds.html) · [Franchises](franchises.html) · [Cotisations](cotisations.html) ·
  [Délais](delais.html) · [Fiscalité](fiscalite.html) · [Points de vigilance](points-vigilance.html) · [Formules](formules.html)
- Transversal : [Thèmes](themes.html) · [Glossaire](glossaire.html) · [Notices](notices.html) · [Sources](sources.html) · [Recherches](recherches.html)

## Qualité
- [Rapport de couverture](couverture.html) — Vue IA vs JSON.

_La notice PDF fait toujours foi. Projection des JSON ; masters non modifiés ; documents de sources publiques._
""" % {"nc": len(CONTRACT_META)}
    write("index.md", idx_md)
    write("index.html", page_html("Vue IA", renderish(idx_md), depth, SITE + "/ia/index.html"))
    # ia.css
    write("ia.css", """*{box-sizing:border-box}body{max-width:900px;margin:0 auto;padding:16px;font:16px/1.6 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#1a1d24;background:#fff}
@media(prefers-color-scheme:dark){body{color:#e6e9ef;background:#0c0d10}a{color:#7ea0ff}code{background:#1a1d24}.warn{background:#3a2a0033}}
h1{font-size:1.7rem;margin:.2em 0 .4em}h2{font-size:1.3rem;margin:1.3em 0 .3em;border-top:1px solid #8883;padding-top:.5em}h3{font-size:1.05rem;margin:1em 0 .2em}
ul{margin:.3em 0 .3em 0;padding-left:1.4em}li{margin:.25em 0}a{color:#2f54d9}code{background:#eef;padding:0 .3em;border-radius:3px;font-size:.9em}
.meta{color:#6b7280;font-size:.85rem;font-family:ui-monospace,Consolas,monospace}.src{color:#6b7280;font-size:.8rem;font-family:ui-monospace,Consolas,monospace}
.warn{border-left:3px solid #d08700;background:#d0870012;padding:.5em .8em;border-radius:4px}
.ianav{font-size:.82rem;border-bottom:1px solid #8883;padding-bottom:.6em;margin-bottom:1em;line-height:2}
footer{margin-top:2em;border-top:1px solid #8883;padding-top:.8em;font-size:.8rem;color:#6b7280}
table{border-collapse:collapse;width:100%}td,th{border:1px solid #8884;padding:4px 8px;text-align:left}""")

# ------------------------------------------------------------------ RAPPORT DE COUVERTURE (Vue IA vs JSON)
def coverage():
    # Corpus = tous les .md générés.
    corpus = []
    for r, _, fs in os.walk(IA):
        for f in fs:
            if f.endswith(".md"):
                corpus.append(open(os.path.join(r, f), encoding="utf-8").read())
    cn = re.sub(r"\s+", " ", norm("\n".join(corpus)))
    def present(text):
        t = re.sub(r"\s+", " ", norm(text)).strip()
        if not t: return False
        probe = t[:80] if len(t) >= 8 else t   # corps rendu verbatim dans le corpus
        return probe in cn
    def body(e): return e.get("texte") or e.get("titre") or ""
    rows = []
    rn = [c.get("resume_neutre") for c in CONTRATS if c.get("resume_neutre")]
    rows.append(("Résumé humain (resume_neutre)", len(rn), sum(1 for x in rn if present(x))))
    fdesc = [e["texte"] for e in ELEMENTS["faits"] if e["texte"]]
    rows.append(("Résumé IA (descriptions faits)", len(fdesc), sum(1 for x in fdesc if present(x))))
    for k, lbl in [("garanties", "Garanties"), ("exclusions", "Exclusions"), ("options", "Options"),
                   ("cotisations", "Cotisations & prix"), ("delais", "Délais & franchises"), ("fiscalite", "Fiscalité"),
                   ("points-vigilance", "Points de vigilance"), ("formules", "Formules"),
                   ("definitions", "Définitions"), ("conditions", "Conditions"),
                   ("declencheurs", "Déclencheurs"), ("plafonds", "Plafonds"), ("franchises", "Franchises")]:
        items = ELEMENTS[k]
        rows.append((lbl, len(items), sum(1 for e in items if present(body(e)))))
    gl = [e.get("definition") for g in GLOSSAIRE for e in (g.get("entrees") or [])]
    rows.append(("Glossaire (définitions)", len(gl), sum(1 for d in gl if present(d))))
    rows.append(("Notices (PDF)", len(PDFS), sum(1 for p in PDFS if present((p.get("nom_fichier") or str(p.get("path", "")).split("/")[-1]) or ""))))
    rows.append(("Sources (références)", len(SOURCES), sum(1 for s in SOURCES.values() if present(str(s["document_source"]).split("/")[-1]))))
    rows.append(("Contrats", len(CONTRATS), sum(1 for c in CONTRATS if present(c.get("nom")))))
    return rows

def build_coverage(rows):
    depth = 0
    def pct(ok, tot): return 100.0 if tot == 0 else round(100.0 * ok / tot, 1)
    md = [md_hdr("Rapport de couverture — Vue IA vs JSON", "Comparaison automatique : chaque catégorie des JSON est-elle présente dans la Vue IA générée ?"), ""]
    md.append("| Catégorie | JSON | Vue IA | Couverture |")
    md.append("|---|--:|--:|--:|")
    hb = ['<h1>Rapport de couverture — Vue IA vs JSON</h1><p>Comparaison automatique générée le %s. Chaque élément des JSON est recherché dans les pages IA générées.</p>' % DATE]
    hb.append('<table><tr><th>Catégorie</th><th>JSON</th><th>Vue IA</th><th>Couverture</th></tr>')
    allok = True
    for lbl, tot, ok in rows:
        p = pct(ok, tot); ps = "%g" % p
        if p < 100.0: allok = False
        md.append("| %s | %d | %d | %s %% |" % (lbl, tot, ok, ps))
        hb.append("<tr><td>%s</td><td>%d</td><td>%d</td><td>%s %%</td></tr>" % (html.escape(lbl), tot, ok, ps))
    hb.append("</table>")
    verdict = "✅ Couverture complète : aucune information exploitable perdue." if allok else "⚠ Couverture partielle sur certaines catégories (voir ci-dessus)."
    md += ["", "**Verdict.** " + verdict, "", "_Méthode : le texte de chaque élément JSON est recherché (normalisé) dans le corpus Markdown généré. La Vue IA étant une projection déterministe des JSON, la couverture attendue est de 100 %._"]
    hb.append("<p><strong>Verdict.</strong> %s</p><p class='meta'>Méthode : le texte de chaque élément JSON est recherché (normalisé) dans le corpus Markdown généré.</p>" % html.escape(verdict))
    write("couverture.md", "\n".join(md))
    write("couverture.html", page_html("Couverture", "".join(hb), depth, SITE + "/ia/couverture.html"))
    return rows, allok

# ------------------------------------------------------------------ mini Markdown -> HTML (index/guide/manifeste)
def renderish(md):
    out, in_ul = [], False
    for line in md.split("\n"):
        l = line.rstrip()
        def inline(t):
            t = html.escape(t)
            t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
            t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
            t = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', t)
            return t
        if l.startswith("|"):  # tableau simple (couverture)
            if not in_ul: pass
        if l.startswith("- "):
            if not in_ul: out.append("<ul>"); in_ul = True
            out.append("<li>%s</li>" % inline(l[2:])); continue
        if in_ul: out.append("</ul>"); in_ul = False
        if l.startswith("### "): out.append("<h3>%s</h3>" % inline(l[4:]))
        elif l.startswith("## "): out.append("<h2>%s</h2>" % inline(l[3:]))
        elif l.startswith("# "): out.append("<h1>%s</h1>" % inline(l[2:]))
        elif l.startswith("> "): out.append("<blockquote>%s</blockquote>" % inline(l[2:]))
        elif l.strip() == "": out.append("")
        else: out.append("<p>%s</p>" % inline(l))
    if in_ul: out.append("</ul>")
    return "\n".join(out)

def build():
    os.makedirs(IA, exist_ok=True)
    build_contrats_list()
    build_contract_pages()
    CATOBJ = {"garanties": "Toutes les garanties de tous les contrats.", "exclusions": "Toutes les exclusions.",
              "options": "Toutes les options.", "cotisations": "Toutes les cotisations & prix.", "delais": "Tous les délais & franchises.",
              "fiscalite": "Toute la fiscalité.", "points-vigilance": "Tous les points de vigilance.", "formules": "Toutes les formules.",
              "definitions": "Toutes les définitions.", "conditions": "Toutes les conditions de souscription.",
              "declencheurs": "Tous les déclencheurs.", "plafonds": "Tous les plafonds.", "franchises": "Toutes les franchises."}
    LABELS = {"garanties": "Garanties", "exclusions": "Exclusions", "options": "Options", "cotisations": "Cotisations & prix",
              "delais": "Délais & franchises", "fiscalite": "Fiscalité", "points-vigilance": "Points de vigilance",
              "formules": "Formules", "definitions": "Définitions", "conditions": "Conditions de souscription",
              "declencheurs": "Déclencheurs", "plafonds": "Plafonds", "franchises": "Franchises"}
    for k in LABELS:
        build_category(k, LABELS[k], CATOBJ[k])
    build_glossaire(); build_notices(); build_sources(); build_recherches(); build_packs()
    tc = build_themes()
    build_static_pages(tc)
    rows, allok = build_coverage(coverage())
    nfiles = sum(len(fs) for _, _, fs in os.walk(IA))
    print("✅ Vue IA exhaustive générée : %d fichiers, %d contrats, %d thèmes." % (nfiles, len(CONTRATS), len(THEMES)))
    print("Couverture :")
    for lbl, tot, ok in rows:
        print("  %-34s %3d/%-3d  %s%%" % (lbl, ok, tot, "100" if tot == 0 or ok == tot else round(100 * ok / tot, 1)))
    print("Verdict :", "✅ 100% (aucune info perdue)" if allok else "⚠ partielle")

if __name__ == "__main__":
    build()
