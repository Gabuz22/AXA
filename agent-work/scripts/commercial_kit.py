#!/usr/bin/env python3
"""KIT DE RENDEZ-VOUS — l'outil quotidien du conseiller, généré depuis un cas client. 0 token.

À partir d'un cas (modèle inspector_case), assemble DÉTERMINISTIQUEMENT un kit complet d'entretien :
  1. fiche de PRÉPARATION (profil, priorités d'inspecteur, audit de l'existant, pièges à ne pas oublier) ;
  2. PLAN d'entretien en étapes (découverte → besoins → solutions → objections → suites) ;
  3. QUESTIONS de découverte/qualification (matrice de risques + informations manquantes) ;
  4. ARGUMENTAIRES par contrat adaptés au profil (finalité + situations favorables + parade aux objections) ;
  5. trame de COMPTE-RENDU / MAIL de synthèse (placeholders [À COMPLÉTER], réserves incluses).

Sorties JSON (IA) ET Markdown (humain, copiable tel quel). Génériques : la structure du kit est
domain-agnostique ; tout le contenu métier vient du graphe + metier_inspecteur (heuristiques étiquetées).
Garde-fous : aucun tarif/éligibilité/règle fiscale affirmés ; interprétations marquées ; validation humaine.
"""
import knowledge_graph as KG
import inspector_advice as IA
import inspector_mono as IM


def _finalite_txt(graph, subject, domain):
    s = IM.reasoning_sheet(graph, subject, domain)
    f = s.get("finalite")
    if isinstance(f, dict):
        return f.get("texte"), f.get("origine")
    return None, None


def build_kit(case, graph, metier, domain="axa-contrat"):
    avis = IA.advise(case, graph, metier, domain)

    # contrats à présenter = à examiner sur les 3 premières étapes du plan (l'entretien réel est court)
    presenter = []
    for p in avis["plan_action"][:3]:
        for c in p["contrats_a_examiner"]:
            if c not in presenter:
                presenter.append(c)

    argumentaires = []
    for c in presenter[:4]:
        fin, origine = _finalite_txt(graph, c, domain)
        sheet = IM.reasoning_sheet(graph, c, domain)
        fav = sheet.get("situations_favorables")
        risques_c = [p["risque"] for p in avis["plan_action"] if c in p["contrats_a_examiner"]]
        parades = [ob for ob in avis["objections_probables"] if ob["risque"] in risques_c]
        argumentaires.append({
            "contrat": c,
            "accroche_metier": fin or "à approfondir",
            "pour_ce_client": (fav or {}).get("texte") if isinstance(fav, dict) else None,
            "repond_aux_risques": risques_c,
            "pieges_a_ne_pas_oublier": (metier.get("pieges_frequents", {}).get(c) or [])[:3],
            "objections_et_parades": parades[:2],
            "origine_interpretations": origine or metier.get("origin"),
        })

    decouverte = []
    seen = set()
    for p in avis["plan_action"]:
        for q in p["questions_a_poser"]:
            if q not in seen:
                decouverte.append({"question": q, "risque": p["risque"]})
                seen.add(q)
    for m in avis["informations_manquantes"]:
        q = "À recueillir : %s" % m
        if q not in seen:
            decouverte.append({"question": q, "risque": "profil"})
            seen.add(q)

    plan = [
        {"phase": 1, "nom": "Accueil & cadre", "contenu": "Rappeler l'objet du rendez-vous ; annoncer la démarche : comprendre la situation AVANT de parler produits."},
        {"phase": 2, "nom": "Découverte", "contenu": "Dérouler les questions de découverte (ci-dessous), en commençant par les informations manquantes."},
        {"phase": 3, "nom": "Diagnostic partagé", "contenu": "Restituer : priorités (%s), trous potentiels (%s), doublons éventuels (%s). Faire valider par le client."
            % (", ".join(avis["risques_priorises"][:3]) or "—",
               ", ".join(avis["trous_de_couverture_potentiels"][:3]) or "aucun détecté",
               ", ".join(avis["doublons_potentiels"]) or "aucun détecté")},
        {"phase": 4, "nom": "Solutions", "contenu": "Présenter les contrats dans l'ORDRE des priorités (argumentaires ci-dessous) ; une solution simple reste préférable si elle suffit."},
        {"phase": 5, "nom": "Objections", "contenu": "Utiliser les parades préparées ; ne jamais improviser un chiffre ou une règle fiscale."},
        {"phase": 6, "nom": "Prochaines étapes", "contenu": "Lister les pièces à fournir, les vérifications (notices, sources officielles à jour), fixer la date du prochain contact."},
    ]

    compte_rendu = {
        "objet": "Compte-rendu d'entretien — [PRÉNOM NOM] — [DATE]",
        "corps": [
            "Situation évoquée : [À COMPLÉTER — reprendre les FAITS confirmés uniquement]",
            "Priorités identifiées ensemble : %s" % (", ".join(avis["risques_priorises"][:3]) or "[À COMPLÉTER]"),
            "Points d'attention abordés : %s" % ("; ".join(list(avis["plan_action"][0]["pieges_frequents"].get(
                next(iter(avis["plan_action"][0]["pieges_frequents"]), ""), ["—"]))[:1]) if avis["plan_action"] else "[À COMPLÉTER]"),
            "Solutions à l'étude : %s (sous réserve d'étude complète et des conditions contractuelles)" % (", ".join(presenter[:3]) or "[À COMPLÉTER]"),
            "Informations à me transmettre : %s" % (", ".join(avis["informations_manquantes"][:4]) or "[À COMPLÉTER]"),
            "Prochaine étape : [À COMPLÉTER — date et objet]",
        ],
        "mentions": "Ce compte-rendu ne constitue ni un devis ni un engagement ; les garanties, conditions et exclusions applicables sont celles des notices contractuelles.",
    }

    return {
        "kit_version": "1.0.0", "case_id": case.get("case_id"),
        "avertissement": "Kit généré automatiquement : les interprétations sont étiquetées (%s), aucun tarif/éligibilité/règle fiscale affirmés. À relire par le conseiller avant usage."
                         % (metier.get("origin") or "?"),
        "preparation": {
            "profil": avis["profil"], "principe": avis["principe_de_priorisation"],
            "priorites": avis["risques_priorises"], "audit_existant": avis["audit_existant"],
            "trous_potentiels": avis["trous_de_couverture_potentiels"],
            "doublons_potentiels": avis["doublons_potentiels"],
            "contrats_a_presenter": presenter,
        },
        "plan_entretien": plan,
        "questions_decouverte": decouverte,
        "argumentaires": argumentaires,
        "compte_rendu_type": compte_rendu,
        "reserves": avis["reserves"], "validation_humaine_requise": True,
    }


def to_markdown(kit):
    """Rendu HUMAIN copiable (fiche de préparation d'entretien)."""
    L = []
    p = kit["preparation"]
    L.append("# Fiche de préparation d'entretien")
    L.append("> %s" % kit["avertissement"])
    L.append("\n## Profil lu (faits uniquement)\n- Drapeaux : %s" % (", ".join(p["profil"]["flags"]) or "—"))
    L.append("- Principe : %s" % p["principe"])
    L.append("\n## Priorités (ordre de l'entretien)")
    for i, r in enumerate(p["priorites"], 1):
        L.append("%d. %s" % (i, r))
    L.append("\n## Audit de l'existant")
    L.append("- Trous potentiels : %s" % (", ".join(p["trous_potentiels"]) or "aucun détecté"))
    L.append("- Doublons potentiels : %s" % (", ".join(p["doublons_potentiels"]) or "aucun détecté"))
    L.append("\n## Plan d'entretien")
    for ph in kit["plan_entretien"]:
        L.append("**%d. %s** — %s" % (ph["phase"], ph["nom"], ph["contenu"]))
    L.append("\n## Questions de découverte")
    for q in kit["questions_decouverte"][:12]:
        L.append("- [ ] %s _(%s)_" % (q["question"], q["risque"]))
    L.append("\n## Argumentaires")
    for a in kit["argumentaires"]:
        L.append("### %s" % a["contrat"])
        L.append("- **Accroche** : %s" % a["accroche_metier"])
        if a.get("pour_ce_client"):
            L.append("- **Pour ce client** : %s" % a["pour_ce_client"])
        for piege in a["pieges_a_ne_pas_oublier"]:
            L.append("- ⚠ %s" % piege)
        for ob in a["objections_et_parades"]:
            L.append("- **Si le client dit** %s → %s" % (ob["objection"], ob["reponse"]))
    L.append("\n## Trame de compte-rendu / mail")
    L.append("**Objet :** %s" % kit["compte_rendu_type"]["objet"])
    for line in kit["compte_rendu_type"]["corps"]:
        L.append("> %s" % line)
    L.append("\n_%s_" % kit["compte_rendu_type"]["mentions"])
    L.append("\n## Réserves\n" + "\n".join("- %s" % r for r in kit["reserves"]))
    return "\n".join(L)
