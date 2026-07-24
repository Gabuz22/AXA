// worker.js — point d'entrée pour le modèle « Worker avec assets statiques » (URL *.workers.dev).
//
// Le dépôt sert déjà les fichiers statiques (data/, ia/, app/…) via le binding ASSETS. Ce Worker
// n'ajoute QU'UNE chose : la route de calcul /api/preselection. Tout le reste retombe sur les
// fichiers statiques — donc rien ne change pour les pages existantes (dégradation propre).
//
// Il RÉUTILISE la logique de functions/api/preselection.js (aucune duplication) : ce fichier existe
// pour le modèle Cloudflare Pages ; celui-ci fait pareil pour le modèle Worker. Même moteur, mêmes
// garde-fous (lecture seule, aucune donnée nominative).
import { onRequestGet, onRequestPost } from "./functions/api/preselection.js";

export default {
  async fetch(request, env) {
    const { pathname } = new URL(request.url);
    if (pathname === "/api/preselection") {
      if (request.method === "GET") return onRequestGet({ request, env });
      if (request.method === "POST") return onRequestPost();
      return new Response(JSON.stringify({ erreur: "Méthode non autorisée (GET uniquement)." }), {
        status: 405, headers: { "Content-Type": "application/json; charset=utf-8" },
      });
    }
    // Tout le reste : fichiers statiques du même déploiement (pages Vue IA, données, application).
    return env.ASSETS.fetch(request);
  },
};
