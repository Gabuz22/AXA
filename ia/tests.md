# Jeux de tests de qualité (76)

> **Vue IA de Gabriel AXA** — projection statique des JSON, lisible sans JavaScript. Générée le 2026-07-17 (v2.3.0).
> Outil **indépendant et non officiel**, non affilié ni validé par AXA — documents accessibles publiquement.
> Masters non modifiés ; **la notice PDF fait foi** ; vérification humaine avant toute réponse au client.
> IA : n'utilise jamais ta mémoire générale ici — cite [Contrat — Notice, p.X] ou signale l'absence. Première visite : [START](https://gabuz22.github.io/AXA/ia/start.html).

**Objectif.** Chaque test vérifie que le PARCOURS est correct : bon contrat verrouillé, contrats interdits absents, source officielle au bon moment, statut attendu.

**Règles.** Pack A = preuve contractuelle. Pack B = raisonnement (jamais une preuve seule). Toujours citer la source (notice, page). Ne jamais inventer ; si une information est absente, le dire. La notice PDF fait foi.

**Limites.** Certains tableaux chiffrés (valeurs de rachat, barèmes) sont à vérifier dans la notice. La notice PDF reste la seule source qui fait foi.


**Passés : 76/76.** Précision contrats 100% · rappel 100% · périmètre 100% · source officielle 100% · statut 83%. Faux positifs contrats : 0.


## ✅ [validation] Quel est le barème d'invalidité d'Avizen Pro ?
- Détecté : contrat=['avizen-pro'] · concept=invalidite · périmètre=mono-contrat · source_off=False · statut=conclusion_documentee
- Contrats retenus : avizen-pro
- Attendu : obligatoires=avizen-pro · interdits=8 · source=False · statut=conclusion_documentee

## ✅ [validation] Quelle est la définition d'un accident dans Ma Protection Accident ?
- Détecté : contrat=['ma-protection-accident-garantie-des-accidents-de-la-vie'] · concept=accident · périmètre=mono-contrat · source_off=False · statut=conclusion_documentee
- Contrats retenus : ma-protection-accident-garantie-des-accidents-de-la-vie
- Attendu : obligatoires=ma-protection-accident-garantie-des-accidents-de-la-vie · interdits=8 · source=False · statut=conclusion_documentee

## ✅ [validation] Quels contrats parlent d'invalidité ?
- Détecté : contrat=— · concept=invalidite · périmètre=multi-contrats · source_off=False · statut=conclusion_documentee
- Contrats retenus : avizen, avizen-pro, masterlife-credit, essen-ciel-assurance-obseques, ma-protection-accident-garantie-des-accidents-de-la-vie, ma-retraite-plan-d-epargne-retraite-individuel-per, entour-age, excelium-assurance-vie
- Attendu : obligatoires=— · interdits=0 · source=False · statut=—

## ✅ [validation] Compare Avizen Pro et Masterlife Crédit sur l'invalidité.
- Détecté : contrat=['avizen-pro', 'masterlife-credit'] · concept=invalidite · périmètre=comparaison · source_off=False · statut=conclusion_documentee
- Contrats retenus : avizen-pro, masterlife-credit
- Attendu : obligatoires=avizen-pro, masterlife-credit · interdits=7 · source=False · statut=—

## ✅ [validation] Quels contrats excluent le suicide ?
- Détecté : contrat=— · concept=suicide · périmètre=multi-contrats · source_off=False · statut=conclusion_documentee
- Contrats retenus : avizen, avizen-pro, entour-age, essen-ciel-assurance-obseques, essen-ciel-patrimoine, excelium-assurance-vie, ma-protection-accident-garantie-des-accidents-de-la-vie, masterlife-credit
- Attendu : obligatoires=— · interdits=0 · source=False · statut=—

## ✅ [validation] Jusqu'à quel âge les versements sur PER sont-ils déductibles ?
- Détecté : contrat=['ma-retraite-plan-d-epargne-retraite-individuel-per'] · concept=— · périmètre=mono-contrat · source_off=True · statut=verification_source_officielle_requise
- Contrats retenus : ma-retraite-plan-d-epargne-retraite-individuel-per
- Attendu : obligatoires=ma-retraite-plan-d-epargne-retraite-individuel-per · interdits=0 · source=True · statut=verification_source_officielle_requise

## ✅ [validation] Quelle est la franchise contractuelle d'Avizen Pro ?
- Détecté : contrat=['avizen-pro'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : avizen-pro
- Attendu : obligatoires=avizen-pro · interdits=8 · source=False · statut=—

## ✅ [validation] Quels autres contrats traitent de l'invalidité en plus d'Avizen Pro ?
- Détecté : contrat=['avizen-pro'] · concept=invalidite · périmètre=mono+transversal · source_off=False · statut=conclusion_documentee
- Contrats retenus : avizen-pro, avizen, masterlife-credit, essen-ciel-assurance-obseques, ma-protection-accident-garantie-des-accidents-de-la-vie, ma-retraite-plan-d-epargne-retraite-individuel-per, entour-age, excelium-assurance-vie
- Attendu : obligatoires=avizen-pro · interdits=0 · source=False · statut=—

## ✅ [validation] Cette garantie dépend-elle de la Sécurité sociale ?
- Détecté : contrat=— · concept=— · périmètre=ambigu · source_off=True · statut=verification_source_officielle_requise
- Contrats retenus : —
- Attendu : obligatoires=— · interdits=0 · source=True · statut=verification_source_officielle_requise

## ✅ [validation] Je ne trouve pas de plafond chiffré : puis-je conclure qu'il n'y en a pas ?
- Détecté : contrat=— · concept=— · périmètre=ambigu · source_off=False · statut=verification_notice_requise
- Contrats retenus : —
- Attendu : obligatoires=— · interdits=0 · source=False · statut=verification_notice_requise

## ✅ [verrou_contrat] Quelles garanties Avizen propose-t-il ?
- Détecté : contrat=['avizen'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : avizen
- Attendu : obligatoires=avizen · interdits=8 · source=False · statut=—

## ✅ [verrou_contrat] Quelles exclusions dans Avizen ?
- Détecté : contrat=['avizen'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : avizen
- Attendu : obligatoires=avizen · interdits=8 · source=False · statut=—

## ✅ [verrou_contrat] Quels déclencheurs dans Avizen ?
- Détecté : contrat=['avizen'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : avizen
- Attendu : obligatoires=avizen · interdits=8 · source=False · statut=—

## ✅ [verrou_contrat] Quelles garanties Avizen Pro propose-t-il ?
- Détecté : contrat=['avizen-pro'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : avizen-pro
- Attendu : obligatoires=avizen-pro · interdits=8 · source=False · statut=—

## ✅ [verrou_contrat] Quelles exclusions dans Avizen Pro ?
- Détecté : contrat=['avizen-pro'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : avizen-pro
- Attendu : obligatoires=avizen-pro · interdits=8 · source=False · statut=—

## ✅ [verrou_contrat] Quels déclencheurs dans Avizen Pro ?
- Détecté : contrat=['avizen-pro'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : avizen-pro
- Attendu : obligatoires=avizen-pro · interdits=8 · source=False · statut=—

## ✅ [verrou_contrat] Quelles garanties Entour'Age propose-t-il ?
- Détecté : contrat=['entour-age'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : entour-age
- Attendu : obligatoires=entour-age · interdits=8 · source=False · statut=—

## ✅ [verrou_contrat] Quelles exclusions dans Entour'Age ?
- Détecté : contrat=['entour-age'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : entour-age
- Attendu : obligatoires=entour-age · interdits=8 · source=False · statut=—

## ✅ [verrou_contrat] Quels déclencheurs dans Entour'Age ?
- Détecté : contrat=['entour-age'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : entour-age
- Attendu : obligatoires=entour-age · interdits=8 · source=False · statut=—

## ✅ [verrou_contrat] Quelles garanties Essen'Ciel (assurance obsèques) propose-t-il ?
- Détecté : contrat=['essen-ciel-assurance-obseques'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : essen-ciel-assurance-obseques
- Attendu : obligatoires=essen-ciel-assurance-obseques · interdits=8 · source=False · statut=—

## ✅ [verrou_contrat] Quelles exclusions dans Essen'Ciel (assurance obsèques) ?
- Détecté : contrat=['essen-ciel-assurance-obseques'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : essen-ciel-assurance-obseques
- Attendu : obligatoires=essen-ciel-assurance-obseques · interdits=8 · source=False · statut=—

## ✅ [verrou_contrat] Quels déclencheurs dans Essen'Ciel (assurance obsèques) ?
- Détecté : contrat=['essen-ciel-assurance-obseques'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : essen-ciel-assurance-obseques
- Attendu : obligatoires=essen-ciel-assurance-obseques · interdits=8 · source=False · statut=—

## ✅ [verrou_contrat] Quelles garanties Essen'Ciel Patrimoine propose-t-il ?
- Détecté : contrat=['essen-ciel-patrimoine'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : essen-ciel-patrimoine
- Attendu : obligatoires=essen-ciel-patrimoine · interdits=8 · source=False · statut=—

## ✅ [verrou_contrat] Quelles exclusions dans Essen'Ciel Patrimoine ?
- Détecté : contrat=['essen-ciel-patrimoine'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : essen-ciel-patrimoine
- Attendu : obligatoires=essen-ciel-patrimoine · interdits=8 · source=False · statut=—

## ✅ [verrou_contrat] Quels déclencheurs dans Essen'Ciel Patrimoine ?
- Détecté : contrat=['essen-ciel-patrimoine'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : essen-ciel-patrimoine
- Attendu : obligatoires=essen-ciel-patrimoine · interdits=8 · source=False · statut=—

## ✅ [verrou_contrat] Quelles garanties Excelium (assurance vie) propose-t-il ?
- Détecté : contrat=['excelium-assurance-vie'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : excelium-assurance-vie
- Attendu : obligatoires=excelium-assurance-vie · interdits=8 · source=False · statut=—

## ✅ [verrou_contrat] Quelles exclusions dans Excelium (assurance vie) ?
- Détecté : contrat=['excelium-assurance-vie'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : excelium-assurance-vie
- Attendu : obligatoires=excelium-assurance-vie · interdits=8 · source=False · statut=—

## ✅ [verrou_contrat] Quels déclencheurs dans Excelium (assurance vie) ?
- Détecté : contrat=['excelium-assurance-vie'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : excelium-assurance-vie
- Attendu : obligatoires=excelium-assurance-vie · interdits=8 · source=False · statut=—

## ✅ [verrou_contrat] Quelles garanties Ma Protection Accident (Garantie des accidents de la vie) propose-t-il ?
- Détecté : contrat=['ma-protection-accident-garantie-des-accidents-de-la-vie'] · concept=accident · périmètre=mono-contrat · source_off=False · statut=conclusion_documentee
- Contrats retenus : ma-protection-accident-garantie-des-accidents-de-la-vie
- Attendu : obligatoires=ma-protection-accident-garantie-des-accidents-de-la-vie · interdits=8 · source=False · statut=—

## ✅ [verrou_contrat] Quelles exclusions dans Ma Protection Accident (Garantie des accidents de la vie) ?
- Détecté : contrat=['ma-protection-accident-garantie-des-accidents-de-la-vie'] · concept=accident · périmètre=mono-contrat · source_off=False · statut=conclusion_documentee
- Contrats retenus : ma-protection-accident-garantie-des-accidents-de-la-vie
- Attendu : obligatoires=ma-protection-accident-garantie-des-accidents-de-la-vie · interdits=8 · source=False · statut=—

## ✅ [verrou_contrat] Quels déclencheurs dans Ma Protection Accident (Garantie des accidents de la vie) ?
- Détecté : contrat=['ma-protection-accident-garantie-des-accidents-de-la-vie'] · concept=accident · périmètre=mono-contrat · source_off=False · statut=conclusion_documentee
- Contrats retenus : ma-protection-accident-garantie-des-accidents-de-la-vie
- Attendu : obligatoires=ma-protection-accident-garantie-des-accidents-de-la-vie · interdits=8 · source=False · statut=—

## ✅ [verrou_contrat] Quelles garanties Ma Retraite (plan d'épargne retraite individuel — PER) propose-t-il ?
- Détecté : contrat=['ma-retraite-plan-d-epargne-retraite-individuel-per'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : ma-retraite-plan-d-epargne-retraite-individuel-per
- Attendu : obligatoires=ma-retraite-plan-d-epargne-retraite-individuel-per · interdits=8 · source=False · statut=—

## ✅ [verrou_contrat] Quelles exclusions dans Ma Retraite (plan d'épargne retraite individuel — PER) ?
- Détecté : contrat=['ma-retraite-plan-d-epargne-retraite-individuel-per'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : ma-retraite-plan-d-epargne-retraite-individuel-per
- Attendu : obligatoires=ma-retraite-plan-d-epargne-retraite-individuel-per · interdits=8 · source=False · statut=—

## ✅ [verrou_contrat] Quels déclencheurs dans Ma Retraite (plan d'épargne retraite individuel — PER) ?
- Détecté : contrat=['ma-retraite-plan-d-epargne-retraite-individuel-per'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : ma-retraite-plan-d-epargne-retraite-individuel-per
- Attendu : obligatoires=ma-retraite-plan-d-epargne-retraite-individuel-per · interdits=8 · source=False · statut=—

## ✅ [verrou_contrat] Quelles garanties Masterlife CREDIT propose-t-il ?
- Détecté : contrat=['masterlife-credit'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : masterlife-credit
- Attendu : obligatoires=masterlife-credit · interdits=8 · source=False · statut=—

## ✅ [verrou_contrat] Quelles exclusions dans Masterlife CREDIT ?
- Détecté : contrat=['masterlife-credit'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : masterlife-credit
- Attendu : obligatoires=masterlife-credit · interdits=8 · source=False · statut=—

## ✅ [verrou_contrat] Quels déclencheurs dans Masterlife CREDIT ?
- Détecté : contrat=['masterlife-credit'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : masterlife-credit
- Attendu : obligatoires=masterlife-credit · interdits=8 · source=False · statut=—

## ✅ [contractuel_strict] Quelle franchise contractuelle dans Avizen ?
- Détecté : contrat=['avizen'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : avizen
- Attendu : obligatoires=avizen · interdits=8 · source=False · statut=—

## ✅ [contractuel_strict] Quelle franchise contractuelle dans Avizen Pro ?
- Détecté : contrat=['avizen-pro'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : avizen-pro
- Attendu : obligatoires=avizen-pro · interdits=8 · source=False · statut=—

## ✅ [contractuel_strict] Quelle franchise contractuelle dans Entour'Age ?
- Détecté : contrat=['entour-age'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : entour-age
- Attendu : obligatoires=entour-age · interdits=8 · source=False · statut=—

## ✅ [contractuel_strict] Quelle franchise contractuelle dans Essen'Ciel (assurance obsèques) ?
- Détecté : contrat=['essen-ciel-assurance-obseques'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : essen-ciel-assurance-obseques
- Attendu : obligatoires=essen-ciel-assurance-obseques · interdits=8 · source=False · statut=—

## ✅ [contractuel_strict] Quelle franchise contractuelle dans Essen'Ciel Patrimoine ?
- Détecté : contrat=['essen-ciel-patrimoine'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : essen-ciel-patrimoine
- Attendu : obligatoires=essen-ciel-patrimoine · interdits=8 · source=False · statut=—

## ✅ [contractuel_strict] Quelle franchise contractuelle dans Excelium (assurance vie) ?
- Détecté : contrat=['excelium-assurance-vie'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : excelium-assurance-vie
- Attendu : obligatoires=excelium-assurance-vie · interdits=8 · source=False · statut=—

## ✅ [contractuel_strict] Quelle franchise contractuelle dans Ma Protection Accident (Garantie des accidents de la vie) ?
- Détecté : contrat=['ma-protection-accident-garantie-des-accidents-de-la-vie'] · concept=accident · périmètre=mono-contrat · source_off=False · statut=conclusion_documentee
- Contrats retenus : ma-protection-accident-garantie-des-accidents-de-la-vie
- Attendu : obligatoires=ma-protection-accident-garantie-des-accidents-de-la-vie · interdits=8 · source=False · statut=—

## ✅ [contractuel_strict] Quelle franchise contractuelle dans Ma Retraite (plan d'épargne retraite individuel — PER) ?
- Détecté : contrat=['ma-retraite-plan-d-epargne-retraite-individuel-per'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : ma-retraite-plan-d-epargne-retraite-individuel-per
- Attendu : obligatoires=ma-retraite-plan-d-epargne-retraite-individuel-per · interdits=8 · source=False · statut=—

## ✅ [contractuel_strict] Quelle franchise contractuelle dans Masterlife CREDIT ?
- Détecté : contrat=['masterlife-credit'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : masterlife-credit
- Attendu : obligatoires=masterlife-credit · interdits=8 · source=False · statut=—

## ✅ [transversale] Quels contrats traitent de invalidité ?
- Détecté : contrat=— · concept=invalidite · périmètre=multi-contrats · source_off=False · statut=conclusion_documentee
- Contrats retenus : avizen, avizen-pro, masterlife-credit, essen-ciel-assurance-obseques, ma-protection-accident-garantie-des-accidents-de-la-vie, ma-retraite-plan-d-epargne-retraite-individuel-per, entour-age, excelium-assurance-vie
- Attendu : obligatoires=— · interdits=0 · source=False · statut=—

## ✅ [transversale] Quels contrats traitent de décès ?
- Détecté : contrat=— · concept=deces · périmètre=multi-contrats · source_off=False · statut=conclusion_documentee
- Contrats retenus : avizen, ma-protection-accident-garantie-des-accidents-de-la-vie, ma-retraite-plan-d-epargne-retraite-individuel-per, avizen-pro, essen-ciel-assurance-obseques, essen-ciel-patrimoine, excelium-assurance-vie, masterlife-credit, entour-age
- Attendu : obligatoires=— · interdits=0 · source=False · statut=—

## ✅ [transversale] Quels contrats traitent de décès accidentel ?
- Détecté : contrat=— · concept=deces · périmètre=multi-contrats · source_off=False · statut=conclusion_documentee
- Contrats retenus : avizen, ma-protection-accident-garantie-des-accidents-de-la-vie, ma-retraite-plan-d-epargne-retraite-individuel-per, avizen-pro, essen-ciel-assurance-obseques, essen-ciel-patrimoine, excelium-assurance-vie, masterlife-credit, entour-age
- Attendu : obligatoires=— · interdits=0 · source=False · statut=—

## ✅ [transversale] Quels contrats traitent de accident ?
- Détecté : contrat=— · concept=accident · périmètre=multi-contrats · source_off=False · statut=conclusion_documentee
- Contrats retenus : avizen, avizen-pro, ma-protection-accident-garantie-des-accidents-de-la-vie, entour-age, masterlife-credit, essen-ciel-assurance-obseques, excelium-assurance-vie
- Attendu : obligatoires=— · interdits=0 · source=False · statut=—

## ✅ [transversale] Quels contrats traitent de hospitalisation ?
- Détecté : contrat=— · concept=hospitalisation · périmètre=multi-contrats · source_off=False · statut=conclusion_documentee
- Contrats retenus : entour-age, masterlife-credit, avizen-pro
- Attendu : obligatoires=— · interdits=0 · source=False · statut=—

## ✅ [transversale] Quels contrats traitent de incapacité temporaire ?
- Détecté : contrat=— · concept=invalidite · périmètre=multi-contrats · source_off=False · statut=conclusion_documentee
- Contrats retenus : avizen, avizen-pro, masterlife-credit, essen-ciel-assurance-obseques, ma-protection-accident-garantie-des-accidents-de-la-vie, ma-retraite-plan-d-epargne-retraite-individuel-per, entour-age, excelium-assurance-vie
- Attendu : obligatoires=— · interdits=0 · source=False · statut=—

## ✅ [transversale] Quels contrats traitent de carence / délai d'attente ?
- Détecté : contrat=— · concept=carence · périmètre=multi-contrats · source_off=False · statut=conclusion_documentee
- Contrats retenus : entour-age, avizen-pro, avizen, essen-ciel-assurance-obseques
- Attendu : obligatoires=— · interdits=0 · source=False · statut=—

## ✅ [transversale] Quels contrats traitent de rachat ?
- Détecté : contrat=— · concept=rachat · périmètre=multi-contrats · source_off=False · statut=conclusion_documentee
- Contrats retenus : avizen, entour-age, excelium-assurance-vie, ma-retraite-plan-d-epargne-retraite-individuel-per, masterlife-credit, ma-protection-accident-garantie-des-accidents-de-la-vie, avizen-pro, essen-ciel-assurance-obseques, essen-ciel-patrimoine
- Attendu : obligatoires=— · interdits=0 · source=False · statut=—

## ✅ [transversale] Quels contrats traitent de souscription & adhésion ?
- Détecté : contrat=— · concept=souscription · périmètre=multi-contrats · source_off=False · statut=conclusion_documentee
- Contrats retenus : excelium-assurance-vie, avizen, avizen-pro, entour-age, essen-ciel-assurance-obseques, ma-retraite-plan-d-epargne-retraite-individuel-per, masterlife-credit, essen-ciel-patrimoine
- Attendu : obligatoires=— · interdits=0 · source=False · statut=—

## ✅ [transversale] Quels contrats traitent de âge ?
- Détecté : contrat=— · concept=— · périmètre=ambigu · source_off=False · statut=question_ambigue
- Contrats retenus : —
- Attendu : obligatoires=— · interdits=0 · source=False · statut=—

## ✅ [transversale] Quels contrats traitent de suicide ?
- Détecté : contrat=— · concept=suicide · périmètre=multi-contrats · source_off=False · statut=conclusion_documentee
- Contrats retenus : avizen, avizen-pro, entour-age, essen-ciel-assurance-obseques, essen-ciel-patrimoine, excelium-assurance-vie, ma-protection-accident-garantie-des-accidents-de-la-vie, masterlife-credit
- Attendu : obligatoires=— · interdits=0 · source=False · statut=—

## ✅ [transversale] Quels contrats traitent de bénéficiaire ?
- Détecté : contrat=— · concept=beneficiaire · périmètre=multi-contrats · source_off=False · statut=conclusion_documentee
- Contrats retenus : avizen, essen-ciel-assurance-obseques, essen-ciel-patrimoine, ma-retraite-plan-d-epargne-retraite-individuel-per, masterlife-credit, avizen-pro, ma-protection-accident-garantie-des-accidents-de-la-vie, entour-age, excelium-assurance-vie
- Attendu : obligatoires=— · interdits=0 · source=False · statut=—

## ✅ [transversale] Quels contrats traitent de fiscalité ?
- Détecté : contrat=— · concept=fiscalite · périmètre=multi-contrats · source_off=False · statut=conclusion_documentee
- Contrats retenus : avizen, avizen-pro, essen-ciel-assurance-obseques, essen-ciel-patrimoine, ma-protection-accident-garantie-des-accidents-de-la-vie, entour-age, excelium-assurance-vie, ma-retraite-plan-d-epargne-retraite-individuel-per, masterlife-credit
- Attendu : obligatoires=— · interdits=0 · source=False · statut=—

## ✅ [transversale] Quels contrats traitent de fin de garantie ?
- Détecté : contrat=— · concept=fin-garantie · périmètre=multi-contrats · source_off=False · statut=conclusion_documentee
- Contrats retenus : avizen, avizen-pro, entour-age, excelium-assurance-vie, ma-retraite-plan-d-epargne-retraite-individuel-per, masterlife-credit, essen-ciel-assurance-obseques, essen-ciel-patrimoine, ma-protection-accident-garantie-des-accidents-de-la-vie
- Attendu : obligatoires=— · interdits=0 · source=False · statut=—

## ✅ [transversale] Quels contrats traitent de association / anpere ?
- Détecté : contrat=— · concept=association · périmètre=multi-contrats · source_off=False · statut=conclusion_documentee
- Contrats retenus : masterlife-credit, avizen, avizen-pro, entour-age, excelium-assurance-vie, ma-retraite-plan-d-epargne-retraite-individuel-per
- Attendu : obligatoires=— · interdits=0 · source=False · statut=—

## ✅ [comparaison] Compare Avizen et Avizen Pro sur le décès.
- Détecté : contrat=['avizen-pro', 'avizen'] · concept=deces · périmètre=comparaison · source_off=False · statut=conclusion_documentee
- Contrats retenus : avizen-pro, avizen
- Attendu : obligatoires=avizen, avizen-pro · interdits=7 · source=False · statut=—

## ✅ [comparaison] Compare Excelium et Ma Retraite sur la fiscalité.
- Détecté : contrat=['ma-retraite-plan-d-epargne-retraite-individuel-per', 'excelium-assurance-vie'] · concept=fiscalite · périmètre=comparaison · source_off=True · statut=verification_source_officielle_requise
- Contrats retenus : ma-retraite-plan-d-epargne-retraite-individuel-per, excelium-assurance-vie
- Attendu : obligatoires=excelium-assurance-vie, ma-retraite-plan-d-epargne-retraite-individuel-per · interdits=7 · source=True · statut=—

## ✅ [reglementaire] Quelle est la fiscalité de transmission au décès ?
- Détecté : contrat=— · concept=deces · périmètre=multi-contrats · source_off=True · statut=verification_source_officielle_requise
- Contrats retenus : avizen, ma-protection-accident-garantie-des-accidents-de-la-vie, ma-retraite-plan-d-epargne-retraite-individuel-per, avizen-pro, essen-ciel-assurance-obseques, essen-ciel-patrimoine, excelium-assurance-vie, masterlife-credit, entour-age
- Attendu : obligatoires=— · interdits=0 · source=True · statut=verification_source_officielle_requise

## ✅ [reglementaire] Quel abattement fiscal s'applique à la succession ?
- Détecté : contrat=— · concept=fiscalite · périmètre=multi-contrats · source_off=True · statut=verification_source_officielle_requise
- Contrats retenus : avizen, avizen-pro, essen-ciel-assurance-obseques, essen-ciel-patrimoine, ma-protection-accident-garantie-des-accidents-de-la-vie, entour-age, excelium-assurance-vie, ma-retraite-plan-d-epargne-retraite-individuel-per, masterlife-credit
- Attendu : obligatoires=— · interdits=0 · source=True · statut=verification_source_officielle_requise

## ✅ [reglementaire] La cotisation est-elle déductible fiscalement ?
- Détecté : contrat=— · concept=fiscalite · périmètre=multi-contrats · source_off=True · statut=verification_source_officielle_requise
- Contrats retenus : avizen, avizen-pro, essen-ciel-assurance-obseques, essen-ciel-patrimoine, ma-protection-accident-garantie-des-accidents-de-la-vie, entour-age, excelium-assurance-vie, ma-retraite-plan-d-epargne-retraite-individuel-per, masterlife-credit
- Attendu : obligatoires=— · interdits=0 · source=True · statut=verification_source_officielle_requise

## ✅ [reglementaire] Quel régime social s'applique à cette prestation ?
- Détecté : contrat=— · concept=— · périmètre=ambigu · source_off=True · statut=verification_source_officielle_requise
- Contrats retenus : —
- Attendu : obligatoires=— · interdits=0 · source=True · statut=verification_source_officielle_requise

## ✅ [reglementaire] Quel est le plafond légal de déduction ?
- Détecté : contrat=— · concept=— · périmètre=ambigu · source_off=True · statut=verification_source_officielle_requise
- Contrats retenus : —
- Attendu : obligatoires=— · interdits=0 · source=True · statut=verification_source_officielle_requise

## ✅ [reglementaire] Comment est traitée fiscalement la valeur de rachat ?
- Détecté : contrat=— · concept=rachat · périmètre=multi-contrats · source_off=True · statut=verification_source_officielle_requise
- Contrats retenus : avizen, entour-age, excelium-assurance-vie, ma-retraite-plan-d-epargne-retraite-individuel-per, masterlife-credit, ma-protection-accident-garantie-des-accidents-de-la-vie, avizen-pro, essen-ciel-assurance-obseques, essen-ciel-patrimoine
- Attendu : obligatoires=— · interdits=0 · source=True · statut=verification_source_officielle_requise

## ✅ [sans_reponse] Quelle est la garantie chômage de Masterlife Crédit ?
- Détecté : contrat=['masterlife-credit'] · concept=— · périmètre=mono-contrat · source_off=False · statut=donnees_insuffisantes
- Contrats retenus : masterlife-credit
- Attendu : obligatoires=— · interdits=0 · source=False · statut=donnees_insuffisantes

## ✅ [sans_reponse] Le contrat couvre-t-il un dégât des eaux immobilier ?
- Détecté : contrat=— · concept=— · périmètre=ambigu · source_off=False · statut=question_ambigue
- Contrats retenus : —
- Attendu : obligatoires=— · interdits=0 · source=False · statut=donnees_insuffisantes
- ⚠ statut question_ambigue attendu donnees_insuffisantes

## ✅ [sans_reponse] Quel est le taux du livret A ?
- Détecté : contrat=— · concept=— · périmètre=ambigu · source_off=False · statut=question_ambigue
- Contrats retenus : —
- Attendu : obligatoires=— · interdits=0 · source=False · statut=donnees_insuffisantes
- ⚠ statut question_ambigue attendu donnees_insuffisantes

## ✅ [sans_reponse] Quelle est la garantie responsabilité civile auto ?
- Détecté : contrat=— · concept=— · périmètre=ambigu · source_off=False · statut=question_ambigue
- Contrats retenus : —
- Attendu : obligatoires=— · interdits=0 · source=False · statut=donnees_insuffisantes
- ⚠ statut question_ambigue attendu donnees_insuffisantes

## ✅ [ambigu] Que couvre exactement ce contrat ?
- Détecté : contrat=— · concept=— · périmètre=ambigu · source_off=False · statut=question_ambigue
- Contrats retenus : —
- Attendu : obligatoires=— · interdits=0 · source=False · statut=question_ambigue

## ✅ [ambigu] Suis-je bien protégé ?
- Détecté : contrat=— · concept=— · périmètre=ambigu · source_off=False · statut=question_ambigue
- Contrats retenus : —
- Attendu : obligatoires=— · interdits=0 · source=False · statut=question_ambigue

## ✅ [ambigu] Quelles sont les conditions et limites ?
- Détecté : contrat=— · concept=— · périmètre=ambigu · source_off=False · statut=question_ambigue
- Contrats retenus : —
- Attendu : obligatoires=— · interdits=0 · source=False · statut=question_ambigue