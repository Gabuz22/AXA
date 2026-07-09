# Dossiers de compatibilité cockpit
data/AXA/{contrats,calculs,ia}/ sont des COPIES de data/AXA/04_BUILDS_ATELIER/{contrats,calculs,ia}/
restaurées le 2026-06-20 parce que le cockpit (index_gabriel_virtuel_*.html) fetch ces chemins plats :
 - ../data/AXA/contrats/contrats_index.json
 - ../data/AXA/calculs/calculs_index.json
 - ../data/AXA/ia/axa_pdf_index.json
La réorganisation AXA 9-zones avait déplacé ces fichiers dans 04_BUILDS_ATELIER, cassant le cockpit.
SOURCE CANONIQUE = 04_BUILDS_ATELIER. Ces copies sont une couche de compatibilité.
Alternative future : mettre à jour les 3 chemins fetch du HTML vers 04_BUILDS_ATELIER/ puis retirer ces copies.
