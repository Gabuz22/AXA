#!/usr/bin/env python3
"""DomainAdapter — interface GÉNÉRIQUE d'un domaine documentaire pour la plateforme de connaissances.

Un domaine (AXA, BOFiP, HAS, doc OpenAI, Journal Gabriel…) = un adaptateur. Le moteur (graphe,
couverture, ingestion, orchestrateur) est domain-agnostique : « il suffit d'ajouter un adaptateur ».

Un adaptateur expose CE QUE le domaine contient, jamais COMMENT on l'exploite :
  documents()           — les documents sources (id, sujet, fichier, pages) ;
  structured_entities() — la connaissance DÉJÀ structurée (ce que la base sait déjà) → amorce L2 ;
  known_terms(subject)  — vocabulaire connu d'un sujet (référentiel de recouvrement) ;
  label_rules()         — heuristique de cartographie (mots-clés → label de zone) ;
  namespaces()          — domaine des clauses vs domaines d'environnement (jamais mélangés) ;
  official_sources()    — autorités/URLs de l'environnement réglementaire (couche séparée).

Le registre permet un chargement paresseux par identifiant, sans coupler le moteur aux domaines.
"""


class DomainAdapter:
    domain_id = None                       # domaine des CLAUSES, ex: "axa-contrat"
    environment_domains = ()               # domaines d'ENVIRONNEMENT séparés, ex: ("fiscalite","reglementation")

    def documents(self):
        """[{doc_id, subject, document, pages}] — documents sources du domaine."""
        raise NotImplementedError

    def structured_entities(self):
        """[{subject, subtype, label, content}] — connaissance déjà structurée (amorce L2, provenance dérivée)."""
        return []

    def known_terms(self, subject):
        """set[str] — vocabulaire déjà connu pour ce sujet."""
        return set()

    def label_rules(self):
        """[(label, [mots-cles])] — heuristique de cartographie (générique-domaine)."""
        return []

    def namespaces(self):
        """{'contract': domain_id, 'environment': [...] } — cloisonnement des couches de domaine."""
        return {"contract": self.domain_id, "environment": list(self.environment_domains)}

    def official_sources(self):
        """[{id, autorite, url, theme}] — sources officielles de l'environnement (couche séparée, datée)."""
        return []

    def subject_of(self, ref):
        """Sujet CANONIQUE à partir d'une référence (slug OU nom) — pour aligner L1/L2 sur un même sujet.
        Défaut : identité. Un adaptateur réel résout slug<->nom."""
        return ref


# ------------------------------------------------------------------ registre (chargement paresseux)
_LOADERS = {
    "axa-contrat": ("domains.axa", "AXAAdapter"),
}


def register(domain_id, module_path, class_name):
    _LOADERS[domain_id] = (module_path, class_name)


def available():
    return sorted(_LOADERS)


def get(domain_id):
    """Instancie l'adaptateur d'un domaine (import paresseux). KeyError si inconnu."""
    import importlib
    module_path, class_name = _LOADERS[domain_id]
    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)()
