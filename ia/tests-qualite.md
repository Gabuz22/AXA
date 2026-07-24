# Tests de qualité de réponse

> **Vue IA de Gabriel AXA** — projection statique des JSON, lisible sans JavaScript. Générée le 2026-07-17 (v2.3.0).
> Outil **indépendant et non officiel**, non affilié ni validé par AXA — documents accessibles publiquement.
> Masters non modifiés ; **la notice PDF fait foi** ; vérification humaine avant toute réponse au client.
> IA : n'utilise jamais ta mémoire générale ici — cite [Contrat — Notice, p.X] ou signale l'absence. Première visite : [START](https://gabuz22.github.io/AXA/ia/start.html).

**Objectif.** Au-delà du routage : ce qu'une bonne réponse DOIT contenir et le piège qu'elle doit éviter. L'étalon pour mesurer si une IA suivant le protocole tient la route.

**Règles.** Pack A = preuve contractuelle. Pack B = raisonnement (jamais une preuve seule). Toujours citer la source (notice, page). Ne jamais inventer ; si une information est absente, le dire. La notice PDF fait foi.

**Limites.** Certains tableaux chiffrés (valeurs de rachat, barèmes) sont à vérifier dans la notice. La notice PDF reste la seule source qui fait foi.


> Décide mentalement ta réponse à chaque question, puis vérifie qu'elle coche **tous** les critères et **évite** le piège. Un défaut = relis le protocole (START) et les pages concernées.


### Quel est le plafond de déduction d'un PER cette année ?

- **Type** : réglementaire
- **Piège à éviter** : Donner un chiffre de mémoire (le plafond évolue chaque année).
- **Une bonne réponse contient** :
  - Renvoi explicite à la source officielle (le plafond est réglementaire, évolutif)
  - AUCUN chiffre de plafond affirmé sans source
  - Mention que la notice/base ne fait pas foi sur le réglementaire

### Avizen couvre-t-il l'arrêt de travail ?

- **Type** : mono-contrat
- **Piège à éviter** : Présenter la garantie ITT sans ses exclusions/déchéances (délai de déclaration, exclusions).
- **Une bonne réponse contient** :
  - La garantie ITT citée [Avizen — Notice, p.X]
  - AU MOINS un piège associé (exclusion, délai de déclaration 15 j, montants au certificat)
  - Renvoi à la matrice de pièges d'Avizen

### Quelles sont les exclusions de Masterlife CREDIT ?

- **Type** : mono-contrat
- **Piège à éviter** : Lister des exclusions sans notice ni page (invérifiable).
- **Une bonne réponse contient** :
  - Chaque exclusion portant [Masterlife — Notice, p.X]
  - Mention des états antérieurs / absence d'aléa
  - Conclusion « la notice PDF fait foi »

### Que couvre exactement ce contrat ?

- **Type** : ambigu
- **Piège à éviter** : Deviner un contrat au lieu de demander lequel.
- **Une bonne réponse contient** :
  - Demande de précision : quel contrat ?
  - AUCUN contrat traité par défaut

### Quelles garanties Avizen Pro propose-t-il ?

- **Type** : mono-contrat
- **Piège à éviter** : Mélanger avec les garanties d'Avizen (contrat voisin mais distinct).
- **Une bonne réponse contient** :
  - Uniquement Avizen Pro
  - Chaque garantie citée [Avizen Pro — Notice, p.X]
  - Ne PAS citer les autres contrats

### À partir de quel âge peut-on adhérer à Entour'Age et à Essen'Ciel obsèques ?

- **Type** : comparaison
- **Piège à éviter** : Confondre les deux fenêtres d'âge (elles diffèrent : 40–75 vs 50–85).
- **Une bonne réponse contient** :
  - Entour'Age 40–75 ans et Essen'Ciel 50–85 ans, chacun cité sa notice
  - Renvoi à la page divergences
  - Ne PAS moyenner ni mélanger les deux

### Quelle est la valeur de rachat de Ma Protection Accident ?

- **Type** : mono-contrat
- **Piège à éviter** : Inventer une valeur de rachat pour un contrat qui n'en a pas.
- **Une bonne réponse contient** :
  - Dire que c'est SANS OBJET (contrat de dommages corporels, pas d'assurance-vie)
  - Ne PAS inventer de montant

### Quel est le montant exact de la cotisation d'Avizen pour un homme de 40 ans ?

- **Type** : mono-contrat
- **Piège à éviter** : Inventer un montant (les tarifs sont au certificat, pas dans la notice).
- **Une bonne réponse contient** :
  - Dire que le montant n'est pas dans la base / renvoyé au certificat d'adhésion
  - Ne combler par AUCUN chiffre

## Format machine
- [tests-qualite.json](tests-qualite.json) — 8 questions-étalon (question, type, piège, critères). - [verifier.html](verifier.html) — contrôle mécanique d'une réponse.
