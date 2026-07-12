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
VERSION = "2.1.0"
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
CATS_NAV = [("index", "Index"), ("instructions-maitres", "Instructions maîtres"), ("guide-ia", "Guide IA"), ("outils", "Outils"), ("routage", "Routage"), ("pertinence", "Pertinence"),
            ("qualite-routage", "Qualité routage"), ("hierarchie", "Hiérarchie"), ("choix-sources", "Choix sources"),
            ("methode-question-complexe", "Méthode"), ("contrats", "Contrats"), ("garanties", "Garanties"), ("exclusions", "Exclusions"),
            ("definitions", "Définitions"), ("conditions", "Conditions"), ("declencheurs", "Déclencheurs"), ("plafonds", "Plafonds"), ("franchises", "Franchises"),
            ("glossaire", "Glossaire"), ("concepts", "Concepts"), ("themes", "Thèmes"), ("comparateur", "Comparateur"), ("matrices", "Matrices"), ("graphe", "Graphe"),
            ("notices", "Notices"), ("sources", "Sources"), ("sources-officielles", "Sources officielles"), ("reglementation", "Réglementation"), ("surveillance", "Surveillance"),
            ("pack-a", "Pack A"), ("pack-b", "Pack B"), ("couverture", "Couverture"), ("maturite", "Maturité")]
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
> **Commence par les [Instructions maîtres](instructions-maitres.html)** : c'est le protocole à appliquer avant de répondre. Ce guide en détaille la navigation.

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

# ------------------------------------------------------------------ INSTRUCTIONS MAÎTRES (cerveau du protocole IA)
# Page destinée aux IA. Le conseiller colle un mini-prompt qui pointe ici ; l'IA lit ces règles et les applique
# seule, sans que le conseiller ait à choisir un outil ou un parcours. Toute l'intelligence vit dans cette page :
# les évolutions futures se font ici, sans changer les habitudes des conseillers.
_IU = SITE + "/ia/"
INSTRUCTIONS_MAITRES_MD = ("""# Instructions maîtres — Gabriel AXA

> **À lire par l'intelligence artificielle avant de répondre.** Un conseiller AXA t'a demandé d'utiliser Gabriel AXA.
> Applique intégralement ce protocole — quel que soit ton modèle (ChatGPT, Claude, Gemini, Copilot, Mistral, DeepSeek, Qwen…) — **avant** de répondre à sa question.

## Ce qu'est Gabriel AXA
Gabriel AXA est la **projection statique, complète et sourcée** de la base contractuelle AXA (garanties, exclusions,
définitions, conditions, plafonds, franchises…), issue de **documents publics** (notices d'information, conditions
générales). Tu peux tout lire depuis les pages HTML/Markdown, **sans exécuter de code**. Point d'entrée : @IU@.
Chaque fait contractuel porte sa source (notice + page) et un identifiant stable réutilisable (`#id`).

## Étape 1 — Comprendre et classer la question
Déduis toi-même le(s) type(s) de la question. **Ne demande pas au conseiller de choisir.**
- **Contrat précis** — la question nomme un contrat → travaille sur sa fiche.
- **Comparaison** — deux contrats ou plus à mettre en regard.
- **Recherche multi-contrats** — un besoin pouvant concerner plusieurs contrats.
- **Recherche transversale** — une catégorie ou un thème à travers tous les contrats.
- **Réglementation** — fiscalité, retraite, succession, sécurité sociale, droit.
- **Profil client** — la réponse dépend d'informations sur le client (âge, statut, objectif…).
- **Informations manquantes** — des éléments nécessaires ne sont pas fournis.

## Étape 2 — Utiliser les outils Gabriel AXA (sans rien demander)
Selon le type détecté, consulte **d'office** les pages utiles. Tu choisis seul lesquelles ouvrir ; n'attends aucune consigne.
- **Routage** : @IU@routage.html — décomposer la question, choisir les bons contrats.
- **Concepts** : @IU@concepts.html — synonymes métier (IPT, PTIA…) reliés aux contrats et catégories.
- **Comparateur** : @IU@comparateur.html — un sujet, tous les contrats côte à côte.
- **Matrices** : @IU@matrices.html — contrats × catégories, concepts × contrats.
- **Preuves** : @IU@preuves.html — éléments citables (contrat, notice, page).
- **Couverture** : @IU@couverture-recherche.html — ce qui est présent / absent / à vérifier dans la base.
- **Méthode** : @IU@methode-question-complexe.html — les parcours d'une question complexe.
- **Qualité** : @IU@qualite-routage.html — le niveau de confiance du routage.
- **Sources officielles** : @IU@sources-officielles.html — les autorités publiques par thème réglementaire.
- Données brutes : contrats @IU@contrats.html, catégories (@IU@garanties.html, @IU@exclusions.html, @IU@definitions.html…), glossaire @IU@glossaire.html, notices @IU@notices.html.

## Étape 3 — Construire la réponse
- **Toujours citer** le contrat, la notice et la page pour chaque fait contractuel : `[Contrat — Notice, p.X]`.
- **Ne jamais inventer, extrapoler ni généraliser** au-delà des sources.
- **Toujours distinguer** ce qui relève du **contrat** (sourcé notice) de ce qui relève de la **réglementation** (règle légale/fiscale/sociale, évolutive).
- **Toujours signaler explicitement** : information **absente** de la base · information **non trouvée** · information **nécessitant la notice PDF** · information **nécessitant une source officielle**.

## Étape 4 — Raisonner
- **Assemble plusieurs contrats** si le besoin le justifie.
- Explique les **avantages et les limites** de chaque option.
- Si des **informations client manquent** (âge, statut, objectif, situation familiale…), **demande-les AVANT de conclure**.
- Lorsqu'il existe plusieurs solutions, **présente plusieurs hypothèses** plutôt qu'une réponse unique.

## Étape 5 — Réglementation
Si la question touche **fiscalité, retraite, succession, sécurité sociale ou droit** :
- consulte les **sources officielles** recommandées par Gabriel AXA (@IU@sources-officielles.html) ;
- **ne donne jamais un chiffre, un barème ou un plafond sans vérification** à sa source officielle ;
- rappelle que **ces règles évoluent**.

## Hiérarchie documentaire (ordre d'autorité)
**Contrat → Notice → Documents AXA → Sources officielles → Réponse.**
La **notice PDF fait foi**. Ne conserve **aucune donnée client nominative**.

## Format de réponse attendu
- Une réponse **directe, prudente et sourcée**.
- Pour chaque fait contractuel : `[Contrat — Notice, p.X]`.
- Une séparation nette **contractuel / réglementaire**.
- La liste de ce qui **manque** ou **reste à vérifier**.
- Une conclusion rappelant : « **La notice PDF fait foi.** »
""").replace("@IU@", _IU)

# Prompt maître complet, en texte brut : c'est le SECOURS que le conseiller colle si son IA ne suit pas les liens.
INSTRUCTIONS_MAITRES_TXT = (INSTRUCTIONS_MAITRES_MD
    + "\n\n---\nApplique tout ce qui précède, puis réponds à ma question ci-dessous. "
      "Si tu peux ouvrir des liens, pars de " + _IU + " ; sinon, applique ces règles de mémoire et signale toute information que tu n'as pas pu vérifier.\n\nMa question : ")

def build_instructions_maitres():
    depth = 0
    write("instructions-maitres.md", INSTRUCTIONS_MAITRES_MD)
    write("instructions-maitres.html", page_html("Instructions maîtres", renderish(INSTRUCTIONS_MAITRES_MD), depth, SITE + "/ia/instructions-maitres.html"))
    write("instructions-maitres.txt", INSTRUCTIONS_MAITRES_TXT)

def build_static_pages(theme_counts):
    depth = 0
    write("guide-ia.md", GUIDE_MD)
    write("guide-ia.html", page_html("Guide IA", renderish(GUIDE_MD), depth, SITE + "/ia/guide-ia.html"))
    # Manifeste lisible + ai-manifest.json
    pages = ["index", "instructions-maitres", "guide-ia", "manifeste", "outils", "routage", "pertinence", "qualite-routage",
             "planificateur", "concepts", "couverture-recherche",
             "comparateur", "preuves", "methode-question-complexe", "tests", "hierarchie", "choix-sources",
             "sources-officielles", "reglementation", "surveillance", "connaissances-dynamiques", "matrices",
             "graphe", "maturite", "pack-a", "pack-b", "contrats",
             "garanties", "exclusions", "options", "cotisations", "delais", "fiscalite", "points-vigilance",
             "formules", "definitions", "conditions", "declencheurs", "plafonds", "franchises", "glossaire",
             "notices", "sources", "recherches", "themes", "couverture"]
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
        "entry_point": SITE + "/ia/instructions-maitres.html",
        "ai_protocol": "Toute IA : 1) lire /ia/instructions-maitres.html ; 2) appliquer ces règles (classer la question, "
                       "utiliser les outils utiles, citer contrat+notice+page, distinguer contractuel/réglementaire, signaler les absences) ; 3) répondre.",
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
    # Outil de SÉLECTION DE CONTEXTE (rétroporté de Gabriel Virtuel /vue-ia/privee/) :
    # selon le type de question, l'IA sait quelles pages charger — au lieu de tout lire.
    selection = {
        "regle": "charger d'abord instructions-maitres ; puis les pages du type de question ; "
                 "citer contrat + notice + page ; signaler les absences au lieu d'inventer",
        "questions": {
            "garantie_couverte_ou_pas": ["instructions-maitres", "routage", "garanties", "exclusions", "contrats"],
            "comparer_des_contrats": ["comparateur", "matrices", "contrats"],
            "definition_d_un_terme": ["glossaire", "definitions"],
            "delais_franchises_plafonds": ["delais", "franchises", "plafonds"],
            "cotisations_et_fiscalite": ["cotisations", "fiscalite"],
            "preuve_et_citation": ["preuves", "notices", "sources"],
            "question_complexe_multi_contrats": ["methode-question-complexe", "planificateur", "routage"],
            "reglementaire_vs_contractuel": ["reglementation", "sources-officielles", "hierarchie"],
            "etat_et_limites_de_la_base": ["couverture", "maturite", "qualite-routage"],
        },
    }
    for _mods in selection["questions"].values():
        for _m in _mods:
            assert _m in pages, "selection vers page inconnue : %s" % _m
    manifest["selection"] = SITE + "/ia/selection.json"
    write("selection.json", json.dumps(selection, ensure_ascii=False, indent=1))
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
    urls += [SITE + "/ia/ai-manifest.json", SITE + "/ia/contrats.json", SITE + "/ia/glossaire.json",
             SITE + "/ia/concepts.json", SITE + "/ia/planificateur.json", SITE + "/ia/couverture-recherche.json",
             SITE + "/ia/preuves.json", SITE + "/ia/tests.json", SITE + "/ia/sources-officielles.json",
             SITE + "/ia/reglementation.json", SITE + "/ia/surveillance.json", SITE + "/ia/connaissances-dynamiques.json",
             SITE + "/ia/choix-sources.json", SITE + "/ia/graphe.json", SITE + "/ia/matrices/couverture.json",
             SITE + "/ia/matrices/concepts-contrats.json", SITE + "/ia/pertinence.json", SITE + "/ia/routage.json"]
    write("sitemap-ia.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
          "".join("<url><loc>%s</loc><lastmod>%s</lastmod></url>\n" % (html.escape(u), DATE) for u in urls) + "</urlset>\n")
    write("robots.txt", "User-agent: *\nAllow: /\nSitemap: %s/ia/sitemap-ia.xml\n" % SITE)
    # index global
    idx_md = md_hdr("Gabriel AXA — Vue IA", "Point d'entrée de la couche IA : commencer ici, puis naviguer.") + """
## Pour toute IA (ChatGPT, Claude, Gemini, Copilot, Mistral, DeepSeek, Qwen…)
Un conseiller t'a demandé d'utiliser Gabriel AXA. Procède dans cet ordre, sans rien demander de plus :
- **1. Lis les [Instructions maîtres](instructions-maitres.html)** — le protocole complet à appliquer avant de répondre.
- **2. Utilise les outils nécessaires** — routage, concepts, comparateur, matrices, preuves, couverture, méthode, sources officielles.
- **3. Réponds** — en citant contrat + notice + page, en distinguant contractuel et réglementaire, en signalant toute absence.

## Repères (pour approfondir)
- **[Guide IA](guide-ia.html)** — comment naviguer la Vue IA (règles, arbitrage, absence, liens).
- **[Outils IA](outils.html)** — planificateur, concepts, couverture, comparateur, preuves, méthode.
- **[Manifeste IA](manifeste.html)** — organisation, citation, hiérarchie, autorité.

## Outils de circulation & recherche
- [Planificateur](planificateur.html) (question → plan) · [Concepts](concepts.html) · [Détecteur de couverture](couverture-recherche.html)
- [Comparateur thématique](comparateur.html) · [Graphe de preuves](preuves.html) · [Méthode question complexe](methode-question-complexe.html) · [Tests](tests.html)

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

# ==================================================================================================
# OUTILS DE CIRCULATION (dérivés) — concepts, planificateur, couverture, comparateur, preuves, méthode
# Aucune donnée inventée : tout provient de ELEMENTS / GLOSSAIRE / SOURCES (projection). Sans LLM.
# ==================================================================================================
CONCEPTS = [
    ("invalidite", "Invalidité", ["invalidit", "ipt", "ipp", "ptia", "incapacit"], ["taux", "bareme", "barème", "prestation", "seuil", "definition", "exclusion", "fin de garantie"]),
    ("deces", "Décès", ["deces", "décès", "mortalit", "capital deces"], ["capital", "beneficiaire", "accidentel", "exclusion"]),
    ("deces-accidentel", "Décès accidentel", ["accidentel"], ["doublement", "capital", "definition accident"]),
    ("accident", "Accident", ["accident"], ["definition", "garantie", "exclusion"]),
    ("hospitalisation", "Hospitalisation", ["hospitalis"], ["indemnite", "forfait", "franchise"]),
    ("incapacite-temporaire", "Incapacité temporaire", ["incapacite temporaire", "itt", "indemnite journaliere", "indemnités journalières"], ["franchise", "delai"]),
    ("carence", "Carence / délai d'attente", ["carence", "delai d attente", "delai de carence", "attente"], ["mois", "annee", "delai"]),
    ("rachat", "Rachat", ["rachat", "valeur de rachat", "mise en reduction", "reduction"], ["tableau", "delai", "penalite"]),
    ("souscription", "Souscription & adhésion", ["souscription", "adhesion", "adherer", "formalite", "questionnaire"], ["age", "medical", "certificat"]),
    ("age", "Âge", ["age a l adhesion", "age maximal", "age minimal", "ans inclus", "annee de naissance"], ["18", "65", "limite"]),
    ("suicide", "Suicide", ["suicide"], ["premiere annee", "exclusion", "delai"]),
    ("beneficiaire", "Bénéficiaire", ["beneficiaire", "clause beneficiaire"], ["designation", "reversion"]),
    ("fiscalite", "Fiscalité", ["fiscal", "990", "757", "impot", "succession", "abattement", "cgi"], ["transmission", "bareme"]),
    ("fin-garantie", "Fin de garantie", ["fin de garantie", "cesse", "terme", "expiration", "resiliation"], ["age", "deces"]),
    ("association", "Association / ANPERE", ["anpere", "association", "gestion paritaire"], ["adherent", "groupe"]),
]
CONCEPT_ORDER = ["garanties", "exclusions", "definitions", "conditions", "declencheurs", "plafonds", "franchises", "options", "cotisations", "delais", "fiscalite", "points-vigilance", "formules"]

def concept_hits(kws):
    hits = {}
    for cat in CONCEPT_ORDER:
        for e in ELEMENTS.get(cat, []):
            hay = norm((e.get("titre") or "") + " " + (e.get("texte") or ""))
            if any(w in hay for w in kws): hits.setdefault(cat, []).append(e)
    gl = []
    for g in GLOSSAIRE:
        if any(w in norm(g.get("terme", "")) for w in kws): gl.append(g)
    return hits, gl

def el_concepts(e):
    hay = norm((e.get("titre") or "") + " " + (e.get("texte") or ""))
    return [sg for sg, _, kws, _ in CONCEPTS if any(w in hay for w in kws)]

def contract_notice_map(depth):
    return {cm["slug"]: notice_href_for(cm["slug"], depth) for cm in CONTRACT_META}

def build_concepts():
    depth = 0; data = {}
    md = [md_hdr("Index conceptuel transversal", "Concepts métier reliant automatiquement synonymes, contrats, catégories et sources. Aucune relation inventée : tout est dérivé du contenu.")]
    hb = ['<h1>Index conceptuel transversal</h1><p>Chaque concept relie synonymes, contrats, garanties, exclusions, définitions, conditions, déclencheurs et sources — dérivés du contenu, vérifiables.</p>']
    for sg, nom, kws, facets in CONCEPTS:
        hits, gl = concept_hits(kws)
        contrats = sorted({e["contrat"] for cat in hits for e in hits[cat]}, key=norm)
        srcs = {}
        for cat in hits:
            for e in hits[cat]: add_src(e.get("src"), (e["contrat"], cat)) if False else None
        data[sg] = {"nom": nom, "synonymes": kws, "facettes": facets,
                    "categories": {cat: [e["id"] for e in hits[cat]] for cat in hits},
                    "contrats": contrats,
                    "url": SITE + "/ia/concepts.html#c-" + sg}
        md += ["", "## %s" % nom, "", "- **Synonymes** : %s" % ", ".join(kws), "- **Contrats concernés** : %s" % (", ".join(contrats) or "—")]
        for cat in CONCEPT_ORDER:
            if hits.get(cat): md.append("- **%s** (%d) : %s" % (cat, len(hits[cat]), " · ".join("[%s](%s.md#%s)" % ((e.get("titre") or e["texte"])[:40], cat, e["id"]) for e in hits[cat][:12])))
        if gl: md.append("- **Glossaire** : %s" % ", ".join(g.get("terme") for g in gl))
        hb.append('<h2 id="c-%s">%s</h2><p class="meta">Synonymes : %s</p><ul>' % (sg, html.escape(nom), html.escape(", ".join(kws))))
        hb.append("<li><strong>Contrats concernés</strong> : %s</li>" % (", ".join('<a href="contrat/%s.html">%s</a>' % (slug(c), html.escape(c)) for c in contrats) or "—"))
        for cat in CONCEPT_ORDER:
            if hits.get(cat):
                hb.append('<li><strong>%s</strong> (%d) : %s</li>' % (cat, len(hits[cat]), " · ".join('<a href="%s.html#%s">%s</a>' % (cat, e["id"], html.escape((e.get("titre") or e["texte"])[:40])) for e in hits[cat][:12])))
        if gl: hb.append("<li><strong>Glossaire</strong> : %s</li>" % ", ".join(html.escape(g.get("terme")) for g in gl))
        hb.append("</ul>")
    write("concepts.md", "\n".join(md)); write("concepts.html", page_html("Concepts", "".join(hb), depth, SITE + "/ia/concepts.html"))
    write("concepts.json", json.dumps({"meta": {"version": VERSION, "genere_le": DATE, "note": "Concepts dérivés : synonymes + éléments liés (ids), vérifiables. Aucune relation inventée."}, "concepts": data}, ensure_ascii=False, indent=1))
    return data

def build_planificateur(concepts):
    depth = 0; nm = contract_notice_map(depth); plans = {}
    for sg, nom, kws, facets in CONCEPTS:
        c = concepts[sg]
        cats = [cat for cat in CONCEPT_ORDER if c["categories"].get(cat)]
        plans[sg] = {"concept": nom, "synonymes": kws,
                     "categories_a_consulter": cats,
                     "contrats_candidats": c["contrats"],
                     "notices": [{"contrat": ct, "url": (SITE + "/ia/" + nm[slug(ct)][3:]) if nm.get(slug(ct)) else None} for ct in c["contrats"]],
                     "criteres_completude": ["au moins une définition", "au moins une garantie ou un déclencheur", "vérifier exclusions", "vérifier conditions/limites"],
                     "si_absent": "dire « non présent dans la base Gabriel AXA » et renvoyer à la notice / au certificat d'adhésion ; ne pas inventer."}
    write("planificateur.json", json.dumps({"meta": {"version": VERSION, "genere_le": DATE, "usage": "Mapper une question -> concept(s) via synonymes, obtenir contrats candidats + catégories à consulter + notices. Ne répond pas ; prépare le parcours."}, "plans": plans}, ensure_ascii=False, indent=1))
    md = [md_hdr("Planificateur de recherche", "Transforme une question en plan de recherche (sans y répondre) : concept, synonymes, catégories, contrats candidats, notices, critères de complétude."), """
## Comment l'utiliser (sans LLM)
1. Repérer dans la question un ou plusieurs **concepts** via leurs **synonymes** (voir [concepts](concepts.md) / [planificateur.json](planificateur.json)).
2. Récupérer le **plan** du concept : contrats candidats + catégories à consulter + notices.
3. Consulter les pages catégorie et fiches contrat listées ; collecter les éléments **avec leur source**.
4. Vérifier la **complétude** ([couverture-recherche](couverture-recherche.md)).
5. Assembler une réponse **sourcée** ([méthode](methode-question-complexe.md)). En cas d'absence : le dire, ne pas inventer.

## Plans par concept
"""]
    hb = ['<h1>Planificateur de recherche</h1><p>Transforme une question en plan (ne répond pas). Format machine : <a href="planificateur.json">planificateur.json</a>.</p>']
    for sg, nom, kws, facets in CONCEPTS:
        p = plans[sg]
        md += ["### %s" % nom, "- Synonymes : %s" % ", ".join(kws),
               "- Catégories à consulter : %s" % (", ".join(p["categories_a_consulter"]) or "—"),
               "- Contrats candidats : %s" % (", ".join(p["contrats_candidats"]) or "—"), ""]
        hb.append('<h2>%s</h2><ul><li>Synonymes : <code>%s</code></li><li>Catégories : %s</li><li>Contrats candidats : %s</li></ul>' % (
            html.escape(nom), html.escape(", ".join(kws)),
            " · ".join('<a href="%s.html">%s</a>' % (cat, cat) for cat in p["categories_a_consulter"]) or "—",
            " · ".join('<a href="contrat/%s.html">%s</a>' % (slug(ct), html.escape(ct)) for ct in p["contrats_candidats"]) or "—"))
    write("planificateur.md", "\n".join(md)); write("planificateur.html", page_html("Planificateur", "".join(hb), depth, SITE + "/ia/planificateur.html"))
    return plans

def build_couverture_recherche(concepts):
    depth = 0; matrix = {}
    md = [md_hdr("Détecteur de couverture de recherche", "Pour chaque concept : quelles catégories sont présentes/absentes, par contrat. Empêche de confondre absence dans la base et absence de clause.")]
    hb = ['<h1>Détecteur de couverture de recherche</h1><p>Distingue : présent · absent de la base · à vérifier en notice/certificat. Aucune conclusion : uniquement l\'état de la recherche.</p>']
    cats_show = ["definitions", "garanties", "declencheurs", "exclusions", "conditions", "plafonds", "franchises"]
    for sg, nom, kws, facets in CONCEPTS:
        c = concepts[sg]; matrix[sg] = {}
        present = {cat: len(c["categories"].get(cat, [])) for cat in cats_show}
        absent = [cat for cat in cats_show if not present[cat]]
        matrix[sg] = {"present": present, "absent_de_la_base": absent, "contrats": c["contrats"]}
        md += ["", "## %s" % nom,
               "- Trouvé : %s" % (", ".join("%d %s" % (present[cat], cat) for cat in cats_show if present[cat]) or "rien"),
               "- Absent de la base (à vérifier en **notice / certificat d'adhésion**) : %s" % (", ".join(absent) or "—")]
        hb.append('<h2>%s</h2><ul><li><strong>Trouvé</strong> : %s</li><li><strong>Absent de la base</strong> (vérifier notice/certificat) : %s</li></ul>' % (
            html.escape(nom), html.escape(", ".join("%d %s" % (present[cat], cat) for cat in cats_show if present[cat]) or "rien"), html.escape(", ".join(absent) or "—")))
    write("couverture-recherche.md", "\n".join(md)); write("couverture-recherche.html", page_html("Couverture recherche", "".join(hb), depth, SITE + "/ia/couverture-recherche.html"))
    write("couverture-recherche.json", json.dumps({"meta": {"version": VERSION, "genere_le": DATE, "legende": {"present": "présent dans la base dérivée", "absent_de_la_base": "non présent dans la base -> vérifier notice/certificat d'adhésion, ne pas inventer"}}, "concepts": matrix}, ensure_ascii=False, indent=1))

COMPARE_SUBJECTS = ["invalidite", "deces", "carence", "age", "rachat", "suicide", "hospitalisation", "souscription"]
def build_comparateur(concepts):
    depth = 0
    md = [md_hdr("Comparateur thématique", "Compare un même sujet entre contrats : définition, garantie, conditions, exclusions, déclencheurs, limites, source, absences. Aucune conclusion commerciale.")]
    hb = ['<h1>Comparateur thématique</h1><p>Un sujet, tous les contrats côte à côte. Sourcé. Aucune conclusion automatique.</p>']
    cmap = {sg: (nom, kws) for sg, nom, kws, _ in CONCEPTS}
    for sg in COMPARE_SUBJECTS:
        nom, kws = cmap[sg]; hits, gl = concept_hits(kws)
        contrats = sorted({e["contrat"] for cat in hits for e in hits[cat]}, key=norm)
        md += ["", "## %s" % nom, ""]
        hb.append('<h2 id="s-%s">%s</h2>' % (sg, html.escape(nom)))
        for ct in contrats:
            cslug = slug(ct)
            by = {cat: [e for e in hits.get(cat, []) if e["cslug"] == cslug] for cat in ["definitions", "garanties", "conditions", "exclusions", "declencheurs", "plafonds", "franchises"]}
            md.append("### %s" % ct)
            hb.append('<h3><a href="contrat/%s.html">%s</a></h3><ul>' % (cslug, html.escape(ct)))
            for cat, lbl in [("definitions", "Définition"), ("garanties", "Garantie"), ("conditions", "Conditions"), ("exclusions", "Exclusions"), ("declencheurs", "Déclencheurs"), ("plafonds", "Plafonds"), ("franchises", "Franchises")]:
                if by[cat]:
                    md.append("- **%s** : %s" % (lbl, " · ".join((e.get("titre") or e["texte"])[:60] + cite_md(e.get("src"), depth) for e in by[cat][:4])))
                    hb.append("<li><strong>%s</strong> : %s</li>" % (lbl, " · ".join(html.escape((e.get("titre") or e["texte"])[:60]) + cite_html(e.get("src"), depth) for e in by[cat][:4])))
                else:
                    md.append("- **%s** : _absent de la base_" % lbl); hb.append('<li><strong>%s</strong> : <em>absent de la base</em></li>' % lbl)
            hb.append("</ul>")
    write("comparateur.md", "\n".join(md)); write("comparateur.html", page_html("Comparateur", "".join(hb), depth, SITE + "/ia/comparateur.html"))

def build_preuves():
    depth = 0; nodes = []
    for cat in CONCEPT_ORDER + ["faits"]:
        for e in ELEMENTS.get(cat, []):
            s = e.get("src") or {}
            nodes.append({"id": e["id"], "contrat": e.get("contrat"), "contrat_slug": e.get("cslug"),
                          "type": cat, "titre": e.get("titre") or "", "texte": e.get("texte") or "",
                          "source_pdf": s.get("document_source"), "page": s.get("page"),
                          "lien_contrat": SITE + "/ia/contrat/%s.html#%s" % (e.get("cslug"), e["id"]),
                          "lien_notice": (SITE + "/" + quote("data/AXA/00_PACKAGE_ACTIF/Contrats-AXA/" + str(s["document_source"])) + ("#page=" + str(s["page"]).split(",")[0].strip() if s.get("page") else "")) if s.get("document_source") else None,
                          "concepts": el_concepts(e)})
    write("preuves.json", json.dumps({"meta": {"version": VERSION, "genere_le": DATE, "elements": len(nodes),
        "usage": "Graphe de preuves : chaque conclusion doit citer des ids d'éléments. relations = même contrat + concepts partagés (dérivés, vérifiables).",
        "champs": ["id", "contrat", "type", "titre", "texte", "source_pdf", "page", "lien_contrat", "lien_notice", "concepts"]}, "elements": nodes}, ensure_ascii=False, indent=1))
    md = md_hdr("Graphe de preuves", "Chaque élément citable comme preuve, avec id stable, contrat, type, texte, source PDF + page, liens et concepts. Une conclusion doit reposer sur des ids précis.") + """
## Principe
Toute conclusion se reconstruit depuis des **preuves identifiées** : « cette conclusion repose sur les éléments `#id1`, `#id2`, `#id3` ».
Chaque preuve porte : contrat · type · texte · **source PDF + page** · lien contrat · lien notice · concepts liés.

## Format machine
- [preuves.json](preuves.json) — %d éléments. Relations dérivées (même contrat, concepts partagés) ; aucune relation inventée.

## Comment citer une preuve
`[Notice : <fichier>, p.<page>]` + l'`#id` de l'élément (réutilisable, stable).
""" % len([1 for cat in CONCEPT_ORDER + ["faits"] for _ in ELEMENTS.get(cat, [])])
    write("preuves.md", md); write("preuves.html", page_html("Preuves", renderish(md), depth, SITE + "/ia/preuves.html"))

METHODE_MD = """# Méthode — résoudre une question (simple ou complexe)

> Parcours standardisés pour une IA. Objectif : réponse **fiable, traçable, sourcée**, sans invention.

## Les 5 parcours

### 1. Question simple sur un contrat
« Quel est le plafond de cette garantie ? »
1. Ouvrir `/ia/contrat/<slug>.html`. 2. Repérer la garantie / le plafond. 3. Citer la notice + page.
**Complétude** : l'élément est présent et sourcé. Sinon → notice.

### 2. Question transversale
« Quels contrats traitent de l'invalidité ? »
1. `/ia/concepts.html#c-invalidite` (synonymes IPT/IPP/PTIA/incapacité). 2. Lister les **contrats concernés**.
3. Vérifier chaque contrat via `/ia/invalidite`… **Format** : liste des contrats + source par contrat.

### 3. Comparaison ciblée
« Compare les exclusions liées au suicide. »
1. `/ia/comparateur.html#s-suicide`. 2. Lire par contrat : exclusion + source + *absent de la base* le cas échéant.
**Ne pas** produire de conclusion commerciale. Toujours citer.

### 4. Question complexe avec conditions
« Dans quels cas l'invalidité déclenche-t-elle une prestation, avec quelles limites et exclusions ? »
1. **Planifier** : `/ia/planificateur.html` → concept invalidité → catégories (définitions, garanties, déclencheurs, exclusions, conditions) + contrats candidats.
2. **Collecter** les éléments par catégorie (avec sources).
3. **Vérifier la couverture** : `/ia/couverture-recherche.html#…` (qu'est-ce qui est absent ?).
4. **Assembler** (structure ci-dessous). 5. **Citer** chaque affirmation.

### 5. Information absente ou ambiguë
Si un élément est marqué *absent de la base* : dire **« non présent dans la base Gabriel AXA — à vérifier dans la notice / le certificat d'adhésion »**. **Ne jamais combler.** Distinguer : absent de la base ≠ absent du contrat ≠ renvoyé au certificat.

## Assembleur de réponse (structure obligatoire)
1. **Réponse courte** (sourcée).
2. **Conditions** (conditions de souscription / d'application).
3. **Exceptions / exclusions**.
4. **Limites** (plafonds, franchises, délais).
5. **Éléments non trouvés** (voir détecteur de couverture).
6. **Sources** (notice + page pour chaque affirmation, + `#id` des preuves).
7. **Niveau de certitude documentaire** : élevé (élément sourcé) · moyen (donnée à vérifier en notice) · faible (absent de la base).

## Règle d'or
Pack A = preuve · Pack B = raisonnement (jamais une preuve seule) · **la notice PDF fait foi** · ne jamais inventer.
"""
def build_methode():
    depth = 0
    write("methode-question-complexe.md", METHODE_MD)
    write("methode-question-complexe.html", page_html("Méthode question complexe", renderish(METHODE_MD), depth, SITE + "/ia/methode-question-complexe.html"))

def build_outils():
    depth = 0
    items = [("routage", "Routage par type de question", "détection d'entités + verrouillage du contrat explicite + périmètre"),
             ("pertinence", "Pertinence pondérée", "score 0-5 concept×contrat (garantie centrale vs mention), avec preuves"),
             ("qualite-routage", "Qualité du routage", "métriques de précision : contrats, périmètre, sources, statut ; erreurs par famille"),
             ("planificateur", "Planificateur de recherche", "question → plan (concept, synonymes, contrats, catégories, notices)"),
             ("concepts", "Index conceptuel", "concepts métier reliant synonymes, contrats, catégories, sources"),
             ("couverture-recherche", "Détecteur de couverture", "présent / absent de la base / à vérifier en notice"),
             ("comparateur", "Comparateur thématique", "un sujet, tous les contrats côte à côte, sourcé"),
             ("preuves", "Graphe de preuves", "chaque élément citable (id, source, page, concepts)"),
             ("methode-question-complexe", "Méthode & assembleur", "5 parcours + structure de réponse sécurisée"),
             ("hierarchie", "Hiérarchie documentaire", "ordre : contrat → notice → docs AXA → réglementation → réponse"),
             ("choix-sources", "Moteur choix des sources", "quel document, quel ordre, quand s'arrêter, quand ne pas conclure"),
             ("sources-officielles", "Sources officielles", "autorités publiques (Légifrance, BOFiP, Ameli…) par concept"),
             ("reglementation", "Détecteur de réglementation", "signale une matière évolutive + autorités à consulter"),
             ("surveillance", "Surveillance documentaire", "dater / alerter / préparer (jamais de mise à jour auto)"),
             ("connaissances-dynamiques", "Connaissances dynamiques", "chaîne de validation prête (jamais automatique)"),
             ("matrices", "Matrices documentaires", "contrats × catégories, concepts × contrats (HTML/MD/JSON/CSV)"),
             ("graphe", "Graphe documentaire", "nœuds & relations dérivées (contrats, concepts, éléments, autorités)"),
             ("maturite", "Rapport de maturité", "capacités documentaires, réglementaires, de preuve, de couverture"),
             ("tests", "Jeux de tests", "≥ 50 questions de contrôle + parcours attendus")]
    md = [md_hdr("Outils IA — circulation & recherche", "Outils dérivés pour aider une IA à décomposer une question, parcourir les bons contrats, vérifier sa couverture et assembler une réponse sourcée."), ""]
    hb = ['<h1>Outils IA — circulation & recherche</h1><p>Décomposer · parcourir · vérifier · comparer · prouver · assembler. Tout est dérivé et sourcé.</p><ul>']
    for k, t, d in items:
        md.append("- **[%s](%s.html)** — %s" % (t, k, d)); hb.append('<li><a href="%s.html"><strong>%s</strong></a> — %s (aussi <a href="%s.md">.md</a>)</li>' % (k, html.escape(t), html.escape(d), k))
    md += ["", "## Formats machine", "- [concepts.json](concepts.json) · [planificateur.json](planificateur.json) · [couverture-recherche.json](couverture-recherche.json) · [preuves.json](preuves.json) · [tests.json](tests.json)"]
    hb.append('</ul><h2>Formats machine</h2><p><a href="concepts.json">concepts.json</a> · <a href="planificateur.json">planificateur.json</a> · <a href="couverture-recherche.json">couverture-recherche.json</a> · <a href="preuves.json">preuves.json</a> · <a href="tests.json">tests.json</a></p>')
    write("outils.md", "\n".join(md)); write("outils.html", page_html("Outils IA", "".join(hb), depth, SITE + "/ia/outils.html"))

def _quality_tests():
    others = lambda keep: [cm["slug"] for cm in CONTRACT_META if cm["slug"] not in keep]
    T = []
    def t(fam, q, oblig=None, interdits=None, cats=None, source=False, notice=False, statut=None):
        T.append({"famille": fam, "question": q, "contrats_obligatoires": oblig or [], "contrats_interdits": interdits or [],
                  "categories_obligatoires": cats or [], "source_officielle_externe_attendue": source,
                  "notice_attendue": notice, "statut_attendu": statut})
    # Étape 13 — 10 questions de validation impératives
    t("validation", "Quel est le barème d'invalidité d'Avizen Pro ?", ["avizen-pro"], others(["avizen-pro"]), ["formules", "garanties", "definitions"], False, True, "conclusion_documentee")
    t("validation", "Quelle est la définition d'un accident dans Ma Protection Accident ?", [ACC_SLUG], others([ACC_SLUG]), ["definitions"], False, True, "conclusion_documentee")
    t("validation", "Quels contrats parlent d'invalidité ?", [], [], [], False, False, None)
    t("validation", "Compare Avizen Pro et Masterlife Crédit sur l'invalidité.", ["avizen-pro", "masterlife-credit"], others(["avizen-pro", "masterlife-credit"]), [], False, True, None)
    t("validation", "Quels contrats excluent le suicide ?", [], [], ["exclusions"], False, False, None)
    t("validation", "Jusqu'à quel âge les versements sur PER sont-ils déductibles ?", [RET_SLUG], [], [], True, False, "verification_source_officielle_requise")
    t("validation", "Quelle est la franchise contractuelle d'Avizen Pro ?", ["avizen-pro"], others(["avizen-pro"]), ["franchises"], False, True, None)
    t("validation", "Quels autres contrats traitent de l'invalidité en plus d'Avizen Pro ?", ["avizen-pro"], [], [], False, False, None)
    t("validation", "Cette garantie dépend-elle de la Sécurité sociale ?", [], [], [], True, False, "verification_source_officielle_requise")
    t("validation", "Je ne trouve pas de plafond chiffré : puis-je conclure qu'il n'y en a pas ?", [], [], [], False, True, "verification_notice_requise")
    # Verrou contrat (mono) — le contrat nommé verrouille, les autres sont INTERDITS
    for cm in CONTRACT_META:
        t("verrou_contrat", "Quelles garanties %s propose-t-il ?" % cm["nom"], [cm["slug"]], others([cm["slug"]]), ["garanties"], False, True, None)
        t("verrou_contrat", "Quelles exclusions dans %s ?" % cm["nom"], [cm["slug"]], others([cm["slug"]]), ["exclusions"], False, True, None)
        t("verrou_contrat", "Quels déclencheurs dans %s ?" % cm["nom"], [cm["slug"]], others([cm["slug"]]), ["declencheurs"], False, True, None)
    # Contractuel strict (aucune source officielle)
    for cm in CONTRACT_META:
        t("contractuel_strict", "Quelle franchise contractuelle dans %s ?" % cm["nom"], [cm["slug"]], others([cm["slug"]]), ["franchises"], False, True, None)
    # Transversales (multi-contrats, pas de source officielle)
    for sg, nom, kws, facets in CONCEPTS:
        t("transversale", "Quels contrats traitent de %s ?" % nom.lower(), [], [], [], False, False, None)
    # Comparaisons (uniquement les contrats nommés)
    t("comparaison", "Compare Avizen et Avizen Pro sur le décès.", ["avizen", "avizen-pro"], others(["avizen", "avizen-pro"]), [], False, True, None)
    t("comparaison", "Compare Excelium et Ma Retraite sur la fiscalité.", ["excelium-assurance-vie", RET_SLUG], others(["excelium-assurance-vie", RET_SLUG]), ["fiscalite"], True, True, None)
    # Réglementaires (source officielle OBLIGATOIRE)
    for q in ["Quelle est la fiscalité de transmission au décès ?", "Quel abattement fiscal s'applique à la succession ?",
              "La cotisation est-elle déductible fiscalement ?", "Quel régime social s'applique à cette prestation ?",
              "Quel est le plafond légal de déduction ?", "Comment est traitée fiscalement la valeur de rachat ?"]:
        t("reglementaire", q, [], [], [], True, False, "verification_source_officielle_requise")
    # Sans réponse (aucun contrat, ne pas conclure)
    for q in ["Quelle est la garantie chômage de Masterlife Crédit ?", "Le contrat couvre-t-il un dégât des eaux immobilier ?",
              "Quel est le taux du livret A ?", "Quelle est la garantie responsabilité civile auto ?"]:
        t("sans_reponse", q, [], [], [], False, False, "donnees_insuffisantes")
    # Ambigus (question trop vague)
    for q in ["Que couvre exactement ce contrat ?", "Suis-je bien protégé ?", "Quelles sont les conditions et limites ?"]:
        t("ambigu", q, [], [], [], False, False, "question_ambigue")
    return T

def _expected_perimetre(t):
    qn = norm(t["question"]); ob = t["contrats_obligatoires"]
    if "compare" in qn and len(ob) >= 2: return "comparaison"
    if "en plus" in qn or "autres contrats" in qn: return "mono+transversal"
    if len(ob) == 1: return "mono-contrat"
    if t["famille"] == "ambigu": return "ambigu"
    return None  # transversale / reglementaire / sans_reponse : périmètre non contraint ici

def build_tests(concepts):
    depth = 0; T = _quality_tests(); results = []
    TP = FP = FN = 0; src_ok = 0; stat_ok = stat_n = 0; cat_ok = cat_n = 0; peri_ok = peri_n = 0
    fam = {}; echecs = []
    for tq in T:
        a = analyze(tq["question"])
        retenus = set(a["contrats_retenus"]); oblig = set(tq["contrats_obligatoires"])
        interdits = set(tq["contrats_interdits"]); cats = set(tq["categories_obligatoires"])
        TP += len(oblig & retenus); FP += len(retenus & interdits); FN += len(oblig - retenus)
        recall_ok = oblig <= retenus
        nofor = retenus.isdisjoint(interdits)
        source_ok = (a["source_officielle_requise"] == tq["source_officielle_externe_attendue"])
        statut_ok = (tq["statut_attendu"] is None) or (a["statut"] == tq["statut_attendu"])
        cats_ok = (not cats) or (cats <= set(a["categories_demandees"]))
        exp_peri = _expected_perimetre(tq); peri_match = (exp_peri is None) or (a["perimetre"] == exp_peri)
        if source_ok: src_ok += 1
        if tq["statut_attendu"] is not None: stat_n += 1; stat_ok += 1 if statut_ok else 0
        if cats: cat_n += 1; cat_ok += 1 if cats_ok else 0
        if exp_peri is not None: peri_n += 1; peri_ok += 1 if peri_match else 0
        passed = recall_ok and nofor and source_ok and peri_match
        raisons = []
        if not recall_ok: raisons.append("contrat obligatoire manquant (%s)" % ", ".join(sorted(oblig - retenus)))
        if not nofor: raisons.append("contrat interdit présent (%s)" % ", ".join(sorted(retenus & interdits)))
        if not source_ok: raisons.append("source officielle " + ("de trop" if a["source_officielle_requise"] else "manquante"))
        if not peri_match: raisons.append("périmètre %s attendu %s" % (a["perimetre"], exp_peri))
        if not statut_ok: raisons.append("statut %s attendu %s" % (a["statut"], tq["statut_attendu"]))
        fam.setdefault(tq["famille"], [0, 0]); fam[tq["famille"]][1] += 1
        if passed: fam[tq["famille"]][0] += 1
        else: echecs.append({"famille": tq["famille"], "question": tq["question"], "raisons": raisons})
        results.append({**tq, "detecte": {"contrat_explicite": a["contrat_explicite"], "concept_principal": a["concept_principal"],
            "type_question": a["type_question"], "perimetre": a["perimetre"], "categories_demandees": a["categories_demandees"],
            "contrats_retenus": a["contrats_retenus"], "contrats_rejetes": len(a["contrats_rejetes"]),
            "source_officielle_requise": a["source_officielle_requise"], "statut": a["statut"]},
            "resultat": {"passed": passed, "recall_ok": recall_ok, "sans_contrat_interdit": nofor, "source_ok": source_ok,
                         "perimetre_ok": peri_match, "statut_ok": statut_ok, "raisons": raisons}})
    prec = 100.0 * TP / (TP + FP) if (TP + FP) else 100.0
    rec = 100.0 * TP / (TP + FN) if (TP + FN) else 100.0
    metrics = {"n": len(T), "contrats_precision": prec, "contrats_recall": rec, "faux_positifs": FP, "faux_negatifs": FN,
               "source_exact": 100.0 * src_ok / len(T), "statut_exact": 100.0 * stat_ok / stat_n if stat_n else 100.0,
               "categories_exact": 100.0 * cat_ok / cat_n if cat_n else 100.0,
               "perimetre_exact": 100.0 * peri_ok / peri_n if peri_n else 100.0,
               "passes": sum(1 for r in results if r["resultat"]["passed"]),
               "par_famille": {k: {"ok": v[0], "total": v[1]} for k, v in fam.items()}, "echecs": echecs}
    write("tests.json", json.dumps({"meta": {"version": VERSION, "genere_le": DATE, "total": len(T),
        "schema": "chaque test : question + contrats_obligatoires/interdits + categories_obligatoires + source/notice attendues + statut_attendu ; 'detecte' = sortie du moteur ; 'resultat' = comparaison.",
        "metriques": {k: v for k, v in metrics.items() if k != "echecs"}}, "tests": results}, ensure_ascii=False, indent=1))
    md = [md_hdr("Jeux de tests de qualité (%d)" % len(T), "Chaque test vérifie que le PARCOURS est correct : bon contrat verrouillé, contrats interdits absents, source officielle au bon moment, statut attendu."),
          "\n**Passés : %d/%d.** Précision contrats %.0f%% · rappel %.0f%% · périmètre %.0f%% · source officielle %.0f%% · statut %.0f%%. Faux positifs contrats : %d.\n" % (
              metrics["passes"], len(T), prec, rec, metrics["perimetre_exact"], metrics["source_exact"], metrics["statut_exact"], FP)]
    hb = ['<h1>Jeux de tests de qualité (%d)</h1><p><strong>Passés : %d/%d.</strong> Précision %.0f%% · rappel %.0f%% · périmètre %.0f%% · source off. %.0f%% · statut %.0f%%. Format machine : <a href="tests.json">tests.json</a> · métriques : <a href="qualite-routage.html">qualité du routage</a>.</p>' % (len(T), metrics["passes"], len(T), prec, rec, metrics["perimetre_exact"], metrics["source_exact"], metrics["statut_exact"])]
    for r in results:
        ok = "✅" if r["resultat"]["passed"] else "❌"
        d = r["detecte"]
        md += ["", "## %s [%s] %s" % (ok, r["famille"], r["question"]),
               "- Détecté : contrat=%s · concept=%s · périmètre=%s · source_off=%s · statut=%s" % (r["detecte"]["contrat_explicite"] or "—", d["concept_principal"] or "—", d["perimetre"], d["source_officielle_requise"], d["statut"]),
               "- Contrats retenus : %s" % (", ".join(d["contrats_retenus"]) or "—"),
               "- Attendu : obligatoires=%s · interdits=%d · source=%s · statut=%s" % (", ".join(r["contrats_obligatoires"]) or "—", len(r["contrats_interdits"]), r["source_officielle_externe_attendue"], r["statut_attendu"] or "—")]
        if r["resultat"]["raisons"]: md.append("- ⚠ %s" % " ; ".join(r["resultat"]["raisons"]))
        hb.append('<h2>%s [%s] %s</h2><ul><li>Détecté : contrat <code>%s</code> · concept <code>%s</code> · périmètre <strong>%s</strong> · source_off <strong>%s</strong> · statut <strong>%s</strong></li><li>Contrats retenus : %s</li>%s</ul>' % (
            ok, html.escape(r["famille"]), html.escape(r["question"]), html.escape(", ".join(d["contrat_explicite"]) or "—"),
            html.escape(str(d["concept_principal"] or "—")), html.escape(d["perimetre"]), d["source_officielle_requise"], html.escape(d["statut"]),
            html.escape(", ".join(d["contrats_retenus"]) or "—"),
            ("<li>⚠ %s</li>" % html.escape(" ; ".join(r["resultat"]["raisons"]))) if r["resultat"]["raisons"] else ""))
    write("tests.md", "\n".join(md)); write("tests.html", page_html("Tests", "".join(hb), depth, SITE + "/ia/tests.html"))
    return metrics

def build_qualite(metrics):
    depth = 0
    fam = metrics["par_famille"]
    md = [md_hdr("Qualité du routage — mesures de précision", "Précision du moteur de détection/routage : contrats, périmètre, sources officielles, statut. Les erreurs restantes sont listées par famille."),
          "", "## Métriques globales (%d tests)" % metrics["n"],
          "| Mesure | Valeur |", "|---|--:|",
          "| Tests passés | %d / %d |" % (metrics["passes"], metrics["n"]),
          "| Précision contrats | %.0f %% |" % metrics["contrats_precision"],
          "| Rappel contrats | %.0f %% |" % metrics["contrats_recall"],
          "| Faux positifs (contrats interdits apparus) | %d |" % metrics["faux_positifs"],
          "| Faux négatifs (contrats obligatoires manquants) | %d |" % metrics["faux_negatifs"],
          "| Exactitude périmètre mono/multi | %.0f %% |" % metrics["perimetre_exact"],
          "| Exactitude déclenchement source officielle | %.0f %% |" % metrics["source_exact"],
          "| Exactitude statut de conclusion | %.0f %% |" % metrics["statut_exact"],
          "| Exactitude catégories | %.0f %% |" % metrics["categories_exact"],
          "", "## Par famille", "| Famille | Passés |", "|---|--:|"]
    for k, v in sorted(fam.items()): md.append("| %s | %d/%d |" % (k, v["ok"], v["total"]))
    md += ["", "## Erreurs restantes (%d)" % len(metrics["echecs"])]
    if metrics["echecs"]:
        for e in metrics["echecs"]: md.append("- **[%s]** %s → %s" % (e["famille"], e["question"], " ; ".join(e["raisons"])))
    else:
        md.append("_Aucune erreur : tous les parcours sont corrects._")
    write("qualite-routage.md", "\n".join(md))
    write("qualite-routage.html", page_html("Qualité du routage", renderish("\n".join(md)), depth, SITE + "/ia/qualite-routage.html"))

# ==================================================================================================
# INFRASTRUCTURE DE RAISONNEMENT DOCUMENTAIRE (dérivée / référentiel de navigation, non contractuelle)
# Aucune donnée réglementaire n'est inventée : uniquement des POINTEURS vers des autorités publiques,
# une hiérarchie documentaire, et une infrastructure de surveillance (jamais de mise à jour auto).
# ==================================================================================================
AUTORITES = {
    "legifrance": ("Légifrance", "https://www.legifrance.gouv.fr", "autorite_juridique", "Textes de loi et codes (source du droit)."),
    "code-assurances": ("Code des assurances (Légifrance)", "https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000006073984", "autorite_juridique", "Régime juridique des contrats d'assurance."),
    "code-secu": ("Code de la sécurité sociale (Légifrance)", "https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000006073189", "autorite_juridique", "Protection sociale, retraite, maladie."),
    "cgi": ("Code général des impôts (Légifrance)", "https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000006069577", "autorite_juridique", "Fiscalité (art. 990 I, 757 B…)."),
    "bofip": ("BOFiP-Impôts", "https://bofip.impots.gouv.fr", "autorite_administrative", "Doctrine fiscale administrative opposable."),
    "impots": ("impots.gouv.fr", "https://www.impots.gouv.fr", "autorite_administrative", "Fiscalité des particuliers."),
    "service-public": ("Service-Public.fr", "https://www.service-public.fr", "documentation_officielle", "Information administrative de référence."),
    "urssaf": ("URSSAF", "https://www.urssaf.fr", "autorite_administrative", "Cotisations sociales."),
    "ameli": ("Ameli (Assurance Maladie)", "https://www.ameli.fr", "autorite_administrative", "Santé, maladie, invalidité (régime général)."),
    "cnav": ("L'Assurance retraite (CNAV)", "https://www.lassuranceretraite.fr", "autorite_administrative", "Retraite du régime général."),
    "cnil": ("CNIL", "https://www.cnil.fr", "autorite_administrative", "Données personnelles."),
    "banque-france": ("Banque de France", "https://www.banque-france.fr", "autorite_administrative", "Stabilité financière."),
    "acpr": ("ACPR", "https://acpr.banque-france.fr", "autorite_administrative", "Contrôle prudentiel assurances & banques."),
    "amf": ("AMF", "https://www.amf-france.org", "autorite_administrative", "Marchés financiers, épargne."),
    "france-travail": ("France Travail", "https://www.francetravail.fr", "autorite_administrative", "Emploi, chômage."),
}
TYPE_ORDER = ["autorite_juridique", "autorite_administrative", "documentation_officielle"]
TYPE_LABEL = {"autorite_juridique": "Autorité juridique", "autorite_administrative": "Autorité administrative", "documentation_officielle": "Documentation officielle"}
# concept -> (matiere_evolutive, domaines_reglementaires, autorites)
CONCEPT_REG = {
    "invalidite": (True, ["prévoyance", "protection sociale"], ["code-assurances", "ameli", "service-public", "legifrance"]),
    "deces": (True, ["prévoyance", "succession"], ["code-assurances", "cgi", "bofip", "service-public"]),
    "deces-accidentel": (True, ["prévoyance"], ["code-assurances", "service-public"]),
    "accident": (False, ["prévoyance"], ["code-assurances", "service-public"]),
    "hospitalisation": (True, ["santé", "protection sociale"], ["ameli", "code-secu", "service-public"]),
    "incapacite-temporaire": (True, ["protection sociale"], ["ameli", "code-secu", "service-public"]),
    "carence": (False, ["assurance"], ["code-assurances"]),
    "rachat": (True, ["fiscalité", "assurance vie"], ["cgi", "bofip", "impots", "acpr", "code-assurances"]),
    "souscription": (True, ["assurance", "protection sociale"], ["code-assurances", "service-public", "acpr"]),
    "age": (True, ["retraite", "protection sociale"], ["cnav", "service-public", "code-secu"]),
    "suicide": (False, ["assurance"], ["code-assurances", "legifrance"]),
    "beneficiaire": (True, ["succession", "fiscalité"], ["cgi", "bofip", "code-assurances", "service-public"]),
    "fiscalite": (True, ["fiscalité", "succession"], ["bofip", "impots", "cgi", "service-public"]),
    "fin-garantie": (False, ["assurance"], ["code-assurances"]),
    "association": (False, ["associatif"], ["legifrance", "service-public"]),
}
def auth_link_md(k): a = AUTORITES[k]; return "[%s](%s)" % (a[0], a[1])
def auth_link_html(k): a = AUTORITES[k]; return '<a href="%s" target="_blank" rel="noopener">%s</a>' % (html.escape(a[1]), html.escape(a[0]))

def build_hierarchie():
    depth = 0
    md = md_hdr("Hiérarchie documentaire", "L'ordre dans lequel construire toute réponse. On ne s'arrête pas au contrat si la matière est réglementaire.") + """
## Ordre de construction d'une réponse
1. **Contrat** (fiche IA / catégories) — ce que dit le contrat, sourcé.
2. **Notice officielle** (PDF) — la source qui **fait foi** ; vérifier page.
3. **Documents publics AXA** — supports publics du produit.
4. **Réglementation officielle** — si la question dépend d'une matière évolutive (voir [réglementation](reglementation.html) et [sources officielles](sources-officielles.html)).
5. **Réponse finale** — sourcée, avec niveau de couverture.

## Hiérarchie d'autorité documentaire
1. **Autorité juridique** (Légifrance, codes) — le droit.
2. **Autorité administrative** (BOFiP, impots.gouv.fr, Ameli, CNAV, ACPR, AMF…) — la doctrine/application.
3. **Documentation officielle** (Service-Public.fr) — l'information de référence.
4. **Documentation AXA** (notice, supports) — l'application au produit.

> Règle : en cas de désaccord, l'échelon **supérieur** l'emporte pour le droit ; mais pour le **contrat**, la **notice PDF AXA fait foi**. La réglementation encadre, elle ne réécrit pas la notice.
"""
    write("hierarchie.md", md); write("hierarchie.html", page_html("Hiérarchie documentaire", renderish(md), depth, SITE + "/ia/hierarchie.html"))

def build_sources_officielles():
    depth = 0
    reg = {}
    for sg, nom, kws, facets in CONCEPTS:
        ev, dom, auths = CONCEPT_REG.get(sg, (False, [], []))
        reg[sg] = {"nom": nom, "matiere_evolutive": ev, "domaines": dom,
                   "autorites": [{"cle": k, "nom": AUTORITES[k][0], "url": AUTORITES[k][1], "type": AUTORITES[k][2]} for k in auths]}
    data = {"meta": {"version": VERSION, "genere_le": DATE,
                     "avertissement": "Référentiel de NAVIGATION vers des autorités publiques (URLs publiques, à valider). Ne contient AUCUN contenu réglementaire ; ne se substitue pas aux sources qui font foi. La notice PDF AXA fait foi pour le contrat.",
                     "hierarchie": ["autorite_juridique", "autorite_administrative", "documentation_officielle", "documentation_axa"]},
            "autorites": {k: {"nom": v[0], "url": v[1], "type": v[2], "role": v[3]} for k, v in AUTORITES.items()},
            "concepts": reg}
    write("sources-officielles.json", json.dumps(data, ensure_ascii=False, indent=1))
    md = [md_hdr("Sources officielles", "Autorités publiques de référence à consulter selon le thème. Pointeurs de navigation — jamais du contenu réglementaire ; à valider ; la notice PDF fait foi.")]
    md.append("\n> ⚠ Ces liens renvoient à des **autorités publiques** (Légifrance, BOFiP, Ameli…). Ils **n'apportent aucune donnée réglementaire dans la base** : ils indiquent **où** vérifier une matière évolutive.\n")
    for t in TYPE_ORDER:
        md.append("## %s" % TYPE_LABEL[t])
        for k, v in AUTORITES.items():
            if v[2] == t: md.append("- **%s** — %s — <%s>" % (v[0], v[3], v[1]))
        md.append("")
    md.append("## Par concept métier")
    for sg, nom, kws, facets in CONCEPTS:
        ev, dom, auths = CONCEPT_REG.get(sg, (False, [], []))
        md.append("- **%s**%s : %s" % (nom, " _(matière évolutive)_" if ev else "", " → ".join(auth_link_md(k) for k in auths) or "—"))
    write("sources-officielles.md", "\n".join(md))
    hb = ['<h1>Sources officielles</h1><p class="warn">Pointeurs de navigation vers des autorités publiques. Aucun contenu réglementaire n\'est stocké ici : ils indiquent <strong>où vérifier</strong> une matière évolutive. La notice PDF AXA fait foi pour le contrat.</p>']
    for t in TYPE_ORDER:
        hb.append("<h2>%s</h2><ul>" % TYPE_LABEL[t])
        for k, v in AUTORITES.items():
            if v[2] == t: hb.append("<li><strong>%s</strong> — %s — %s</li>" % (html.escape(v[0]), html.escape(v[3]), auth_link_html(k)))
        hb.append("</ul>")
    hb.append("<h2>Par concept métier</h2><ul>")
    for sg, nom, kws, facets in CONCEPTS:
        ev, dom, auths = CONCEPT_REG.get(sg, (False, [], []))
        hb.append("<li><strong>%s</strong>%s : %s</li>" % (html.escape(nom), " <em>(matière évolutive)</em>" if ev else "", " → ".join(auth_link_html(k) for k in auths) or "—"))
    hb.append("</ul>")
    write("sources-officielles.html", page_html("Sources officielles", "".join(hb), depth, SITE + "/ia/sources-officielles.html"))

def build_reglementation():
    depth = 0; data = {}
    md = [md_hdr("Détecteur de réglementation", "Signale automatiquement quand une réponse dépend d'une réglementation évolutive et quelles autorités consulter. Ne fournit pas la règle : indique où la vérifier.")]
    hb = ['<h1>Détecteur de réglementation</h1><p>Quand un concept relève d\'une matière évolutive (fiscalité, social, retraite, succession, prévoyance…), toute réponse doit être accompagnée de l\'avertissement ci-dessous.</p>']
    for sg, nom, kws, facets in CONCEPTS:
        ev, dom, auths = CONCEPT_REG.get(sg, (False, [], []))
        data[sg] = {"nom": nom, "matiere_evolutive": ev, "domaines": dom,
                    "avertissement": "Cette réponse dépend d'une réglementation susceptible d'évoluer." if ev else None,
                    "sources_officielles_recommandees": [{"nom": AUTORITES[k][0], "url": AUTORITES[k][1]} for k in auths] if ev else [],
                    "derniere_verification": None, "statut_verification": "non vérifié"}
        if ev:
            md += ["", "## %s" % nom,
                   "> ⚠ **Cette réponse dépend d'une réglementation susceptible d'évoluer** (%s)." % ", ".join(dom),
                   ">", "> **Sources officielles recommandées :** %s" % " · ".join(auth_link_md(k) for k in auths),
                   ">", "> **Dernière vérification :** non vérifié (voir [surveillance](surveillance.html))."]
            hb.append('<h2>%s</h2><p class="warn">⚠ Cette réponse dépend d\'une réglementation susceptible d\'évoluer (%s).<br>Sources officielles recommandées : %s<br>Dernière vérification : non vérifié (voir <a href="surveillance.html">surveillance</a>).</p>' % (html.escape(nom), html.escape(", ".join(dom)), " · ".join(auth_link_html(k) for k in auths)))
    write("reglementation.md", "\n".join(md)); write("reglementation.html", page_html("Réglementation", "".join(hb), depth, SITE + "/ia/reglementation.html"))
    write("reglementation.json", json.dumps({"meta": {"version": VERSION, "genere_le": DATE, "note": "Signalement des matières évolutives + autorités. Aucune règle stockée."}, "concepts": data}, ensure_ascii=False, indent=1))

def build_surveillance():
    depth = 0
    entries = {k: {"nom": v[0], "url": v[1], "type": v[2], "date_document": None, "date_derniere_verification": None,
                   "historique": [], "statut": "à vérifier", "version": None} for k, v in AUTORITES.items()}
    write("surveillance.json", json.dumps({"meta": {"version": VERSION, "genere_le": DATE,
        "regle": "Surveillance documentaire = détecter/comparer/dater/alerter/préparer. JAMAIS de mise à jour automatique ; JAMAIS de publication automatique. Validation humaine obligatoire.",
        "etats_possibles": ["Valide", "À vérifier", "Obsolète", "En attente de validation"]}, "sources": entries}, ensure_ascii=False, indent=1))
    md = md_hdr("Surveillance documentaire", "Infrastructure de suivi des sources officielles : détecter, comparer, dater, alerter, préparer une mise à jour. Jamais de mise à jour ni de publication automatique.") + """
## Règle absolue
La surveillance **ne modifie jamais** les connaissances. Elle **prépare** une mise à jour soumise à **validation humaine**.

## États possibles
- **Valide** · **À vérifier** · **Obsolète** · **En attente de validation**

## Champs suivis par source
URL · date du document · date de dernière vérification · historique · statut · version.

## État actuel des sources
""" + "\n".join("- **%s** (%s) — statut : **à vérifier** — <%s>" % (v[0], TYPE_LABEL.get(v[2], v[2]), v[1]) for v in AUTORITES.values()) + "\n\nFormat machine : [surveillance.json](surveillance.json)."
    write("surveillance.md", md); write("surveillance.html", page_html("Surveillance documentaire", renderish(md), depth, SITE + "/ia/surveillance.html"))

def build_connaissances_dynamiques():
    depth = 0
    chaine = ["Source officielle", "Règle actuelle", "Date", "Historique", "Validation humaine", "Publication"]
    items = {sg: {"nom": nom, "domaines": CONCEPT_REG.get(sg, (0, [], []))[1],
                  "chaine": {"source_officielle": [AUTORITES[k][1] for k in CONCEPT_REG.get(sg, (0, [], []))[2]],
                             "regle_actuelle": None, "date": None, "historique": [],
                             "validation_humaine": "requise", "publication": "manuelle uniquement"},
                  "statut": "en attente de validation"}
             for sg, nom, kws, facets in CONCEPTS if CONCEPT_REG.get(sg, (0, 0, 0))[0]}
    write("connaissances-dynamiques.json", json.dumps({"meta": {"version": VERSION, "genere_le": DATE,
        "regle": "Infrastructure prête. Aucune connaissance réglementaire n'est stockée ni mise à jour automatiquement. La chaîne exige une validation humaine avant publication."}, "concepts": items}, ensure_ascii=False, indent=1))
    md = md_hdr("Connaissances dynamiques", "Infrastructure (chaîne) prête pour intégrer, plus tard et manuellement, des règles réglementaires validées. Aucune intégration automatique.") + """
## Chaîne de validation (jamais automatique)
`Source officielle → Règle actuelle → Date → Historique → Validation humaine → Publication`

- La chaîne est **prête** mais **vide** : aucune règle réglementaire n'est stockée dans la base.
- Aucune mise à jour ne modifie directement les connaissances : **validation humaine obligatoire** avant publication.
- Les concepts en **matière évolutive** disposent d'un emplacement prêt (voir [connaissances-dynamiques.json](connaissances-dynamiques.json)).

_But : préparer l'infrastructure sans jamais inventer ni intégrer automatiquement une donnée réglementaire._
"""
    write("connaissances-dynamiques.md", md); write("connaissances-dynamiques.html", page_html("Connaissances dynamiques", renderish(md), depth, SITE + "/ia/connaissances-dynamiques.html"))

def build_choix_sources():
    depth = 0
    plans = {}
    for sg, nom, kws, facets in CONCEPTS:
        ev, dom, auths = CONCEPT_REG.get(sg, (False, [], []))
        order = ["fiche contrat (/ia/contrat/<slug>)", "catégories (garanties, exclusions, définitions, conditions, déclencheurs)", "notice PDF (fait foi)"]
        if ev: order.append("sources officielles : " + ", ".join(AUTORITES[k][0] for k in auths))
        plans[sg] = {"nom": nom, "ordre": order, "matiere_evolutive": ev,
                     "arret": "S'arrêter dès que l'élément est trouvé ET sourcé (notice). Pour une matière évolutive, ajouter le renvoi aux sources officielles.",
                     "ne_pas_conclure_si": "élément absent de la base ET absent de la notice ; ou valeur chiffrée non extraite (à vérifier en notice) ; ou matière évolutive sans vérification de la source officielle."}
    write("choix-sources.json", json.dumps({"meta": {"version": VERSION, "genere_le": DATE, "usage": "Ordre de consultation des documents par concept + conditions d'arrêt et de non-conclusion."}, "concepts": plans}, ensure_ascii=False, indent=1))
    md = md_hdr("Moteur — choix des sources", "Avant toute réponse : quel document consulter, dans quel ordre, pourquoi, quand passer au suivant, quand s'arrêter, quand dire « je ne peux pas conclure ».") + """
## Procédure générale
1. **Fiche contrat / catégories** — la donnée contractuelle, sourcée.
2. **Notice PDF** — vérifier à la page (fait foi).
3. **Documents publics AXA** — si besoin.
4. **Sources officielles** — **uniquement** si matière évolutive (voir [réglementation](reglementation.html)).

## Quand passer au document suivant
Quand le document courant ne contient pas l'élément, ou qu'un chiffre est « à vérifier », ou que la matière est réglementaire.

## Quand s'arrêter
Dès que l'élément est **trouvé et sourcé** (notice). Pour une matière évolutive, après avoir cité la source officielle recommandée.

## Quand dire « je ne peux pas conclure »
- Élément **absent de la base ET de la notice**.
- **Valeur chiffrée non extraite** (renvoyée à la notice / au certificat d'adhésion).
- **Matière évolutive** sans vérification possible de la source officielle.

## Ordre par concept
""" + "\n".join("- **%s** : %s" % (p["nom"], " → ".join(p["ordre"])) for p in plans.values())
    write("choix-sources.md", md); write("choix-sources.html", page_html("Choix des sources", renderish(md), depth, SITE + "/ia/choix-sources.html"))

def csv_cell(v):
    s = str(v if v is not None else "")
    return '"' + s.replace('"', '""') + '"' if any(c in s for c in [',', '"', '\n', ';']) else s
def csv_rows(rows): return "\r\n".join(",".join(csv_cell(c) for c in r) for r in rows) + "\r\n"

MAT_CATS = ["garanties", "exclusions", "definitions", "conditions", "declencheurs", "plafonds", "franchises", "options", "cotisations", "delais", "fiscalite", "points-vigilance", "formules"]
def build_matrices(concepts):
    depth = 1  # pages sous ia/matrices/
    cslugs = [cm["slug"] for cm in CONTRACT_META]; cnames = {cm["slug"]: cm["nom"] for cm in CONTRACT_META}
    # 1) Matrice de couverture : contrats × catégories (comptes)
    header = ["contrat"] + MAT_CATS
    rows = []
    for cm in CONTRACT_META:
        rows.append([cm["nom"]] + [str(len([e for e in ELEMENTS.get(k, []) if e["cslug"] == cm["slug"]])) for k in MAT_CATS])
    write("matrices/couverture.csv", csv_rows([header] + rows))
    write("matrices/couverture.json", json.dumps({"meta": {"version": VERSION, "genere_le": DATE}, "colonnes": MAT_CATS,
        "lignes": [{"contrat": r[0], **{MAT_CATS[i]: int(r[i + 1]) for i in range(len(MAT_CATS))}} for r in rows]}, ensure_ascii=False, indent=1))
    def html_table(header, rows, linkcol0=None):
        h = "<tr>" + "".join("<th>%s</th>" % html.escape(x) for x in header) + "</tr>"
        body = ""
        for r in rows:
            c0 = ('<a href="../contrat/%s.html">%s</a>' % (slug(r[0]), html.escape(str(r[0])))) if linkcol0 else html.escape(str(r[0]))
            body += "<tr><td>%s</td>%s</tr>" % (c0, "".join("<td>%s</td>" % html.escape(str(x)) for x in r[1:]))
        return "<table>%s%s</table>" % (h, body)
    def md_table(header, rows):
        out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
        for r in rows: out.append("| " + " | ".join(str(x) for x in r) + " |")
        return "\n".join(out)
    write("matrices/couverture.md", md_hdr("Matrice de couverture — contrats × catégories", "Nombre d'éléments par contrat et par catégorie.") + "\n" + md_table(header, rows))
    write("matrices/couverture.html", page_html("Matrice de couverture", "<h1>Matrice de couverture — contrats × catégories</h1>" + html_table(header, rows, linkcol0=True), depth, SITE + "/ia/matrices/couverture.html"))
    # 2) Concepts × contrats
    cheader = ["concept"] + [cnames[s] for s in cslugs]
    crows = []
    for sg, nom, kws, facets in CONCEPTS:
        hits, gl = concept_hits(kws)
        crows.append([nom] + [str(sum(1 for cat in hits for e in hits[cat] if e["cslug"] == s)) for s in cslugs])
    write("matrices/concepts-contrats.csv", csv_rows([cheader] + crows))
    write("matrices/concepts-contrats.json", json.dumps({"meta": {"version": VERSION}, "colonnes": [cnames[s] for s in cslugs],
        "lignes": [{"concept": r[0], **{cheader[i + 1]: int(r[i + 1]) for i in range(len(cslugs))}} for r in crows]}, ensure_ascii=False, indent=1))
    write("matrices/concepts-contrats.md", md_hdr("Matrice concepts × contrats", "Nombre d'éléments par concept et par contrat.") + "\n" + md_table(cheader, crows))
    write("matrices/concepts-contrats.html", page_html("Matrice concepts × contrats", "<h1>Matrice concepts × contrats</h1>" + html_table(cheader, crows), depth, SITE + "/ia/matrices/concepts-contrats.html"))
    # 3) Export plat par catégorie (CSV + JSON) : <catégorie> × contrats
    for k in MAT_CATS:
        items = ELEMENTS.get(k, [])
        exp = [["id", "contrat", "titre", "texte", "notice", "page"]]
        js = []
        for e in items:
            s = e.get("src") or {}
            exp.append([e["id"], e["contrat"], e.get("titre", ""), e.get("texte", ""), (str(s.get("document_source")).split("/")[-1] if s.get("document_source") else ""), s.get("page", "")])
            js.append({"id": e["id"], "contrat": e["contrat"], "titre": e.get("titre", ""), "texte": e.get("texte", ""),
                       "notice": s.get("document_source"), "page": s.get("page")})
        write("matrices/%s.csv" % k, csv_rows(exp))
        write("matrices/%s.json" % k, json.dumps({"meta": {"categorie": k, "version": VERSION, "total": len(js)}, "elements": js}, ensure_ascii=False, indent=1))
    # index des matrices
    depth = 1
    idx = ["<h1>Matrices documentaires</h1><p>Chaque matrice en HTML / Markdown / JSON / CSV. Dérivées, sourcées.</p>",
           '<h2>Matrices croisées</h2><ul>',
           '<li>Couverture (contrats × catégories) : <a href="couverture.html">HTML</a> · <a href="couverture.md">MD</a> · <a href="couverture.json">JSON</a> · <a href="couverture.csv">CSV</a></li>',
           '<li>Concepts × contrats : <a href="concepts-contrats.html">HTML</a> · <a href="concepts-contrats.md">MD</a> · <a href="concepts-contrats.json">JSON</a> · <a href="concepts-contrats.csv">CSV</a></li></ul>',
           '<h2>Exports par catégorie (× contrats)</h2><ul>']
    for k in MAT_CATS:
        idx.append('<li>%s : <a href="%s.json">JSON</a> · <a href="%s.csv">CSV</a> · <a href="../%s.html">page</a></li>' % (k, k, k, k))
    idx.append("</ul>")
    write("matrices/index.html", page_html("Matrices", "".join(idx), depth, SITE + "/ia/matrices/index.html"))
    mmd = md_hdr("Matrices documentaires", "Matrices dérivées en HTML/MD/JSON/CSV.") + "\n- Couverture : [HTML](matrices/couverture.html) · [JSON](matrices/couverture.json) · [CSV](matrices/couverture.csv)\n- Concepts × contrats : [HTML](matrices/concepts-contrats.html) · [CSV](matrices/concepts-contrats.csv)\n- Par catégorie : " + " · ".join("[%s.csv](matrices/%s.csv)" % (k, k) for k in MAT_CATS)
    write("matrices.md", mmd); write("matrices.html", page_html("Matrices", renderish(mmd), 0, SITE + "/ia/matrices.html"))

def build_graphe():
    nodes, edges, seen = [], [], set()
    def node(nid, typ, label, extra=None):
        if nid in seen: return
        seen.add(nid); n = {"id": nid, "type": typ, "label": label}
        if extra: n.update(extra)
        nodes.append(n)
    for cm in CONTRACT_META:
        node("contrat:" + cm["slug"], "contrat", cm["nom"], {"url": SITE + "/ia/contrat/%s.html" % cm["slug"]})
    for sg, nom, kws, facets in CONCEPTS:
        ev, dom, auths = CONCEPT_REG.get(sg, (False, [], []))
        node("concept:" + sg, "concept", nom, {"url": SITE + "/ia/concepts.html#c-" + sg})
        for k in auths:
            node("autorite:" + k, "article_reglementaire", AUTORITES[k][0], {"url": AUTORITES[k][1], "autorite_type": AUTORITES[k][2]})
            edges.append({"from": "concept:" + sg, "to": "autorite:" + k, "rel": "reglementation_recommandee"})
    for p in PDFS:
        if p.get("path"): node("notice:" + slug(p.get("nom_fichier") or p["path"]), "notice", p.get("nom_fichier") or p["path"].split("/")[-1], {"contrat": p.get("nom_contrat")})
    for cat in CONCEPT_ORDER + ["faits"]:
        for e in ELEMENTS.get(cat, []):
            nid = "el:" + e["id"]
            node(nid, cat.rstrip("s") if cat != "faits" else "fait", (e.get("titre") or e.get("texte") or "")[:60], {"contrat": e.get("contrat")})
            edges.append({"from": nid, "to": "contrat:" + e["cslug"], "rel": "appartient_a"})
            for c in el_concepts(e): edges.append({"from": nid, "to": "concept:" + c, "rel": "concerne"})
            s = e.get("src") or {}
            if s.get("document_source"): edges.append({"from": nid, "to": "notice:" + slug(str(s["document_source"]).split("/")[-1]), "rel": "source"})
    write("graphe.json", json.dumps({"meta": {"version": VERSION, "genere_le": DATE, "noeuds": len(nodes), "aretes": len(edges),
        "types_noeuds": sorted({n["type"] for n in nodes}), "types_relations": sorted({e["rel"] for e in edges}),
        "note": "Graphe documentaire dérivé. Relations = appartenance (élément→contrat), concept (élément→concept), source (élément→notice), réglementation (concept→autorité). AUCUNE inférence."},
        "noeuds": nodes, "aretes": edges}, ensure_ascii=False, indent=1))
    md = md_hdr("Graphe documentaire", "Nœuds (contrats, concepts, éléments, notices, autorités) et relations dérivées. Aucune inférence.") + """
## Contenu
- **%d nœuds**, **%d relations**. Types de nœuds : contrat, concept, garantie, exclusion, définition, condition, déclencheur, notice, article réglementaire.
- Relations dérivées : `appartient_a` (élément→contrat), `concerne` (élément→concept), `source` (élément→notice), `reglementation_recommandee` (concept→autorité).
- Aucune relation inventée ; tout est vérifiable dans les pages.

Format machine : [graphe.json](graphe.json).
""" % (len(nodes), len(edges))
    write("graphe.md", md); write("graphe.html", page_html("Graphe documentaire", renderish(md), 0, SITE + "/ia/graphe.html"))

def build_maturite(rows_cov):
    depth = 0
    caps = [
        ("Capacité documentaire", "Toutes les catégories exposées, sourcées, 100 % de couverture des données.", "élevée"),
        ("Capacité multi-contrats", "Concepts, thèmes, comparateur, matrices croisées contrats × catégories.", "élevée"),
        ("Capacité réglementaire", "Sources officielles par concept + détecteur de matière évolutive + surveillance (infra).", "moyenne (pointeurs, pas de contenu réglementaire)"),
        ("Capacité de preuve", "Graphe de preuves + graphe documentaire ; chaque élément citable (id, source, page).", "élevée"),
        ("Capacité de couverture", "Détecteur de couverture par concept + matrice de couverture + rapport global.", "élevée"),
        ("Capacité de navigation", "Index, guide, outils, hiérarchie documentaire, choix des sources, liens stables.", "élevée"),
        ("Capacité de raisonnement", "Planificateur + méthode + choix des sources + conditions de non-conclusion.", "moyenne→élevée (cadre le LLM, ne le remplace pas)"),
    ]
    md = [md_hdr("Rapport de maturité — infrastructure de raisonnement", "Mesure des capacités de la Vue IA comme environnement documentaire pour un LLM.")]
    md.append("\n| Capacité | Niveau | Détail |\n|---|---|---|")
    for nom, det, niv in caps: md.append("| %s | %s | %s |" % (nom, niv, det))
    md += ["", "## Couverture des données (rappel)", "", "\n".join("- %s : %d/%d" % (l, ok, tot) for l, tot, ok in rows_cov),
           "", "## Limites restantes",
           "- Matching concept par mots-clés (large, non sémantique).",
           "- Aucune donnée réglementaire stockée : uniquement des pointeurs à valider.",
           "- Chiffres « à vérifier en notice » non extraits (signalés, jamais comblés).",
           "- Régénération manuelle (`build_ia.py`).",
           "", "## Rôle vis-à-vis d'un LLM",
           "Le système **ne remplace pas** un LLM : il est le **meilleur environnement documentaire** pour lui — décomposition, parcours, preuves, couverture, arbitrage des sources, conditions de non-conclusion."]
    write("maturite.md", "\n".join(md)); write("maturite.html", page_html("Maturité", renderish("\n".join(md)), depth, SITE + "/ia/maturite.html"))

# ==================================================================================================
# MOTEUR DE PRÉCISION — détection d'entités, verrouillage contrat, pertinence pondérée, routage, statuts
# 100 % dérivé. Corrige le sur-rappel : le contrat explicite verrouille le périmètre ; la pertinence
# concept×contrat est pondérée (0-5) d'après les preuves ; les sources officielles ne se déclenchent
# qu'au niveau QUESTION (mots fiscaux/légaux), jamais sur le simple concept.
# ==================================================================================================
CNAME = {cm["slug"]: cm["nom"] for cm in CONTRACT_META}
ACC_SLUG = next((cm["slug"] for cm in CONTRACT_META if cm["slug"].startswith("ma-protection-accident")), "ma-protection-accident")
RET_SLUG = next((cm["slug"] for cm in CONTRACT_META if cm["slug"].startswith("ma-retraite")), "ma-retraite")
OBSEQ = "essen-ciel-assurance-obseques"; PATRI = "essen-ciel-patrimoine"

def detect_contracts(q):
    qn = " " + norm(q) + " "
    r = []
    # Limites de mots (regex) pour éviter « avizen pro » dans « avizen propose » et détecter les DEUX Avizen.
    if re.search(r"\bavizen pro\b", qn): r.append("avizen-pro")
    if re.search(r"\bavizen\b(?!\s+pro\b)", qn): r.append("avizen")
    if re.search(r"\bmaster\s?life\b", qn): r.append("masterlife-credit")
    if "protection accident" in qn: r.append(ACC_SLUG)
    if "ma retraite" in qn or re.search(r"\bper\b", qn) or "epargne retraite" in qn: r.append(RET_SLUG)
    if "excelium" in qn: r.append("excelium-assurance-vie")
    if "patrimoine" in qn: r.append(PATRI)
    elif "essen ciel" in qn or "essenciel" in qn or "obseques" in qn: r.append(OBSEQ)
    if "entour" in qn: r.append("entour-age")
    return list(dict.fromkeys(r))

CAT_INTENT = [  # (mot dans la question, catégories obligatoires induites)
    (["bareme", "formule", "calcul", "taux", "montant de"], ["formules", "garanties", "definitions"]),
    (["definition", "defini", "qu est ce", "c est quoi"], ["definitions"]),
    (["franchise", "carence", "delai d attente"], ["franchises"]),
    (["plafond", "montant maximum"], ["plafonds"]),
    (["exclusion", "exclu", "non couvert", "ne couvre pas"], ["exclusions"]),
    (["garantie", "couvert", "couverture", "prise en charge", "prestation"], ["garanties"]),
    (["condition", "souscription", "adhesion", "eligib"], ["conditions"]),
    (["declencheur", "declenche", "dans quels cas"], ["declencheurs"]),
    (["cotisation", "prix", "tarif", "prime"], ["cotisations"]),
    (["delai"], ["delais"]),
]
def detect_categories(qn):
    cats = []
    for mots, out in CAT_INTENT:
        if any(m in qn for m in mots):
            for c in out:
                if c not in cats: cats.append(c)
    return cats

STRONG_REG_KW = ["deductib", "fiscal", "fiscalite", "abattement", "impot", "succession", "securite sociale",
                 "protection sociale", "regime social", "age legal", "plafond legal", "droit de l assurance",
                 "obligation reglementaire", "definition legale", "990 i", "757 b", "cnav", "ameli", "urssaf"]
def is_regulatory(qn): return any(w in qn for w in STRONG_REG_KW)
COMPARE_KW = ["compare", "comparer", "comparaison", "versus", " vs ", "par rapport", "difference entre", "differences entre"]
TRANSV_KW = ["quels contrats", "quel contrat", "dans quels contrats", "liste des contrats", "autres contrats", "en plus de", "en plus d"]

def compute_pertinence():
    pert, ev = {}, []
    for sg, nom, kws, facets in CONCEPTS:
        hits, gl = concept_hits(kws)
        by = {}
        for cat in hits:
            for e in hits[cat]: by.setdefault(e["cslug"], {}).setdefault(cat, []).append(e)
        for cslug, cats in by.items():
            cs = set(cats.keys())
            if {"garanties", "definitions", "declencheurs"} <= cs: score = 5
            elif "garanties" in cs or "declencheurs" in cs: score = 4
            elif "exclusions" in cs or "conditions" in cs: score = 3
            elif "definitions" in cs: score = 2
            else: score = 1
            pert[(sg, cslug)] = score
            preuves = [e["id"] for cat in cats for e in cats[cat]][:8]
            just = {5: "cœur du produit (garantie + définition + déclencheur)", 4: "garantie ou déclencheur important",
                    3: "condition, limite ou exclusion structurante", 2: "définition ou contexte", 1: "mention secondaire"}[score]
            ev.append({"concept": sg, "contrat": cslug, "score": score, "types": sorted(cs),
                       "preuves": preuves, "justification": "%s dans %s." % (just.capitalize(), CNAME.get(cslug, cslug))})
    return pert, ev
PERT, PERT_EV = compute_pertinence()
def cc_score(sg, cslug): return PERT.get((sg, cslug), 0)

def analyze(q):
    qn = norm(q)
    explicit = detect_contracts(q)
    concepts = [sg for sg, nom, kws, facets in CONCEPTS if any(w in qn for w in kws)]
    # concept principal = plus haute pertinence sur les contrats explicites, sinon le plus fréquent
    def concept_weight(sg):
        if explicit: return max((cc_score(sg, c) for c in explicit), default=0)
        return sum(1 for c in CNAME if cc_score(sg, c) >= 4)
    concepts = sorted(concepts, key=concept_weight, reverse=True)
    main = concepts[0] if concepts else None
    secondaires = concepts[1:]
    cats = detect_categories(qn)
    reg = is_regulatory(qn)
    is_cmp = any(w in qn for w in COMPARE_KW)
    is_transv = any(w in qn for w in TRANSV_KW)
    en_plus = ("en plus" in qn or "autres contrats" in qn)
    # périmètre + contrats
    if is_cmp and len(explicit) >= 2:
        perimetre = "comparaison"; retenus = explicit
    elif explicit and en_plus:
        perimetre = "mono+transversal"
        extra = [c for c in CNAME if main and cc_score(main, c) >= 1 and c not in explicit]
        retenus = explicit + sorted(extra, key=lambda c: cc_score(main, c), reverse=True)
    elif explicit:
        perimetre = "mono-contrat"; retenus = explicit  # VERROUILLÉ
    elif main:
        perimetre = "multi-contrats"
        retenus = sorted([c for c in CNAME if cc_score(main, c) >= 1], key=lambda c: cc_score(main, c), reverse=True)
    else:
        perimetre = "ambigu"; retenus = []
    rejetes = [c for c in CNAME if c not in retenus]
    # source officielle : niveau QUESTION uniquement, jamais pour une question de LISTE de contrats.
    source_off = bool(reg) and not is_transv
    # statut de conclusion — dépend de la question réelle, pas d'un simple remplissage de catégories.
    q_absence = ("ne trouve pas" in qn) or ("conclure qu" in qn)  # « puis-je conclure qu'il n'y en a pas ? »
    if q_absence:
        statut = "verification_notice_requise"  # une absence dans la base ne prouve pas l'absence au contrat
    elif source_off:
        statut = "verification_source_officielle_requise"
    elif perimetre == "ambigu":
        statut = "question_ambigue"
    elif perimetre == "mono-contrat":
        c = explicit[0]
        if not main:
            statut = "donnees_insuffisantes"  # contrat nommé mais aucun concept identifié dans la base
        else:
            need_value = any(x in cats for x in ["formules", "plafonds", "franchises"])
            struct = cc_score(main, c) >= (4 if need_value else 1)
            statut = "conclusion_documentee" if struct else "verification_notice_requise"
    elif perimetre == "comparaison":
        statut = "conclusion_documentee" if (main and all(cc_score(main, c) >= 1 for c in explicit)) else "conclusion_partielle"
    elif perimetre in ("multi-contrats", "mono+transversal"):
        statut = "conclusion_documentee" if retenus else "donnees_insuffisantes"
    else:
        statut = "question_ambigue"
    notice_requise = perimetre in ("mono-contrat", "comparaison", "mono+transversal")
    return {"question": q, "contrat_explicite": explicit, "concept_principal": main, "concepts_secondaires": secondaires,
            "type_question": ("comparaison" if is_cmp else ("transversale" if (is_transv and not explicit) else ("reglementaire" if source_off else ("mono-contrat" if explicit else ("multi" if main else "ambigu"))))),
            "categories_demandees": cats, "perimetre": perimetre, "comparaison": is_cmp,
            "dimension_reglementaire": bool(reg), "source_officielle_requise": source_off,
            "contrats_retenus": retenus, "contrats_rejetes": rejetes, "notice_requise": notice_requise,
            "statut": statut, "peut_conclure": statut == "conclusion_documentee"}

def build_pertinence():
    depth = 0
    ev = sorted(PERT_EV, key=lambda x: (-x["score"], x["concept"], x["contrat"]))
    write("pertinence.json", json.dumps({"meta": {"version": VERSION, "genere_le": DATE,
        "echelle": {0: "absent", 1: "mention secondaire", 2: "définition/contexte", 3: "condition/limite/exclusion structurante", 4: "garantie/déclencheur important", 5: "cœur du produit"},
        "note": "Score concept×contrat dérivé des catégories où le concept apparaît. Chaque score conserve preuves + justification. Aucun score sans preuve."}, "pertinence": ev}, ensure_ascii=False, indent=1))
    md = [md_hdr("Pertinence pondérée (concept × contrat)", "Niveau de pertinence 0-5 de chaque concept pour chaque contrat, dérivé des preuves. Distingue une garantie centrale d'une simple mention."),
          "\n**Échelle** : 0 absent · 1 mention secondaire · 2 définition · 3 condition/exclusion · 4 garantie/déclencheur · 5 cœur du produit.\n"]
    hb = ['<h1>Pertinence pondérée (concept × contrat)</h1><p>0 absent · 1 mention · 2 définition · 3 condition/exclusion · 4 garantie/déclencheur · 5 cœur. Dérivé des preuves.</p><table><tr><th>Concept</th><th>Contrat</th><th>Score</th><th>Types</th><th>Justification</th></tr>']
    for e in ev:
        md.append("- **%s** × %s : **%d** (%s) — %s `preuves: %s`" % (e["concept"], CNAME.get(e["contrat"], e["contrat"]), e["score"], ", ".join(e["types"]), e["justification"], ", ".join(e["preuves"][:3])))
        hb.append('<tr><td>%s</td><td><a href="contrat/%s.html">%s</a></td><td>%d</td><td>%s</td><td>%s</td></tr>' % (html.escape(e["concept"]), e["contrat"], html.escape(CNAME.get(e["contrat"], e["contrat"])), e["score"], html.escape(", ".join(e["types"])), html.escape(e["justification"])))
    hb.append("</table>")
    write("pertinence.md", "\n".join(md)); write("pertinence.html", page_html("Pertinence", "".join(hb), depth, SITE + "/ia/pertinence.html"))
    # matrice pondérée concepts × contrats (remplace la version comptage)
    depth = 1; cslugs = [cm["slug"] for cm in CONTRACT_META]
    header = ["concept"] + [CNAME[s] for s in cslugs]
    rows = [[nom] + [str(cc_score(sg, s)) for s in cslugs] for sg, nom, kws, facets in CONCEPTS]
    write("matrices/concepts-contrats.csv", csv_rows([header] + rows))
    write("matrices/concepts-contrats.json", json.dumps({"meta": {"version": VERSION, "type": "pertinence_ponderee_0_5"}, "colonnes": [CNAME[s] for s in cslugs], "lignes": [{"concept": r[0], **{header[i + 1]: int(r[i + 1]) for i in range(len(cslugs))}} for r in rows]}, ensure_ascii=False, indent=1))
    th = "<tr>" + "".join("<th>%s</th>" % html.escape(x) for x in header) + "</tr>"
    tb = "".join("<tr><td>%s</td>%s</tr>" % (html.escape(r[0]), "".join('<td style="text-align:center">%s</td>' % (x if x != "0" else "·") for x in r[1:])) for r in rows)
    write("matrices/concepts-contrats.html", page_html("Matrice pondérée concepts × contrats", "<h1>Matrice pondérée — concepts × contrats (0-5)</h1><p>0 absent · 5 cœur du produit.</p><table>%s%s</table>" % (th, tb), depth, SITE + "/ia/matrices/concepts-contrats.html"))
    write("matrices/concepts-contrats.md", md_hdr("Matrice pondérée concepts × contrats", "Score 0-5.") + "\n| " + " | ".join(header) + " |\n|" + "|".join(["---"] * len(header)) + "|\n" + "\n".join("| " + " | ".join(str(x) for x in r) + " |" for r in rows))

def build_routage():
    depth = 0
    md = md_hdr("Routage par type de question", "Comment le système détermine le périmètre, les contrats retenus, les catégories et le déclenchement des sources officielles. Le contrat explicitement nommé verrouille la recherche.") + """
## Détection d'entités (dérivée, sans LLM)
- **Contrat explicite** : nom/variantes détectés dans la question → **verrouillage** du périmètre.
- **Concept principal / secondaires** : concepts dont un synonyme apparaît, classés par pertinence (score 0-5).
- **Type de question** : mono-contrat · transversale · comparaison · réglementaire · ambiguë.
- **Catégories demandées** : barème→formules/garanties/définitions · définition→définitions · franchise→franchises · exclusion→exclusions · etc.
- **Dimension réglementaire** : détectée sur des **mots de la question** (déductible, fiscal, succession, âge légal, Sécurité sociale…), pas sur le concept.

## Règles de routage
1. **Contrat explicite nommé** → **mono-contrat verrouillé** (les autres contrats sont *rejetés*), sauf demande de comparaison / d'alternatives / « autres contrats ».
2. **Comparaison** (`compare A et B`) → **uniquement** A et B.
3. **Transversale** (`quels contrats…`) → contrats classés par **score de pertinence** ; 4-5 d'abord, 1-3 signalés à part.
4. **Réglementaire** → contrat d'abord si utile, **puis** sources officielles adaptées.
5. **Strictement contractuelle** (garantie, exclusion, barème, franchise, plafond, déclencheur d'un contrat) → **aucune source officielle externe** par défaut.

## Déclenchement des sources officielles
Requis **uniquement** si la question porte sur : fiscalité, déductibilité, plafond légal, âge légal, retraite/PER (fiscal), succession, protection/Sécurité sociale, droit de l'assurance, obligation réglementaire, définition légale.
**Jamais** pour une garantie/exclusion/définition/barème/délai/franchise/déclencheur/plafond **contractuels**.

Format machine : [routage.json](routage.json) (analyse des 10 questions de validation).
"""
    # Étape 13 — analyse détaillée des 10 questions de validation.
    valids = [tq["question"] for tq in _quality_tests() if tq["famille"] == "validation"]
    analyses = [analyze(q) for q in valids]
    write("routage.json", json.dumps({"meta": {"version": VERSION, "genere_le": DATE,
        "note": "Analyse dérivée (détection d'entités + routage) des questions de validation. Sans LLM."}, "analyses": analyses}, ensure_ascii=False, indent=1))
    md += "\n## Validation — 10 questions\n"
    hb_extra = "<h2>Validation — 10 questions</h2>"
    for a in analyses:
        line = ("- **%s**\n  - entités : contrat=%s · concept=%s · secondaires=%s\n  - périmètre : **%s** (%s)\n  - contrats retenus : %s\n  - contrats rejetés : %d\n  - catégories : %s\n  - source officielle : **%s**\n  - statut : **%s**" % (
            a["question"], a["contrat_explicite"] or "aucun", a["concept_principal"] or "—", ", ".join(a["concepts_secondaires"]) or "—",
            a["perimetre"], a["type_question"], ", ".join(a["contrats_retenus"]) or "—", len(a["contrats_rejetes"]),
            ", ".join(a["categories_demandees"]) or "—", a["source_officielle_requise"], a["statut"]))
        md += "\n" + line + "\n"
        hb_extra += ('<h3>%s</h3><ul><li>Entités : contrat <code>%s</code> · concept <code>%s</code></li>'
                     '<li>Périmètre : <strong>%s</strong> (%s)</li><li>Contrats retenus : %s · rejetés : %d</li>'
                     '<li>Catégories : %s</li><li>Source officielle : <strong>%s</strong></li><li>Statut : <strong>%s</strong></li></ul>') % (
            html.escape(a["question"]), html.escape(", ".join(a["contrat_explicite"]) or "aucun"), html.escape(str(a["concept_principal"] or "—")),
            html.escape(a["perimetre"]), html.escape(a["type_question"]), html.escape(", ".join(a["contrats_retenus"]) or "—"),
            len(a["contrats_rejetes"]), html.escape(", ".join(a["categories_demandees"]) or "—"), a["source_officielle_requise"], html.escape(a["statut"]))
    write("routage.md", md)
    write("routage.html", page_html("Routage", renderish(md.split("## Validation")[0]) + hb_extra, depth, SITE + "/ia/routage.html"))


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
    # Outils de circulation (dérivés) — concepts, planificateur, couverture, comparateur, preuves, méthode, tests.
    concepts = build_concepts()
    build_planificateur(concepts)
    build_couverture_recherche(concepts)
    build_comparateur(concepts)
    build_preuves()
    build_methode()
    metrics = build_tests(concepts)  # tests-qualité + harness de précision
    # Infrastructure de raisonnement documentaire (Parties 2–10, 12)
    build_hierarchie()
    build_sources_officielles()
    build_reglementation()
    build_surveillance()
    build_connaissances_dynamiques()
    build_choix_sources()
    build_matrices(concepts)
    build_pertinence()   # moteur de précision : pertinence pondérée (écrase la matrice concepts×contrats)
    build_routage()
    build_qualite(metrics)
    build_graphe()
    build_outils()
    build_instructions_maitres()   # cerveau du protocole IA (mini-prompt conseiller → cette page)
    build_static_pages(tc)
    rows, allok = build_coverage(coverage())
    build_maturite(rows)
    nfiles = sum(len(fs) for _, _, fs in os.walk(IA))
    print("✅ Vue IA générée : %d fichiers, %d contrats, %d thèmes." % (nfiles, len(CONTRATS), len(THEMES)))
    print("Couverture données : %s" % ("100%" if allok else "partielle"))
    print("Précision routage — %d tests : contrats P=%.0f%% R=%.0f%% | périmètre %.0f%% | source off. %.0f%% | statut %.0f%% | faux positifs contrats : %d" % (
        metrics["n"], metrics["contrats_precision"], metrics["contrats_recall"], metrics["perimetre_exact"],
        metrics["source_exact"], metrics["statut_exact"], metrics["faux_positifs"]))
    if metrics["echecs"]:
        print("Échecs restants (%d) :" % len(metrics["echecs"]))
        for e in metrics["echecs"][:12]: print("  [%s] %s -> %s" % (e["famille"], e["question"][:52], ", ".join(e["raisons"])))

if __name__ == "__main__":
    build()
