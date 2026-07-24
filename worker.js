// worker.js — point d'entrée pour le modèle « Worker avec assets statiques » (URL *.workers.dev).
//
// Le dépôt sert déjà les fichiers statiques (data/, ia/, app/…) via le binding ASSETS. Ce Worker
// n'ajoute QU'UNE chose : la route de calcul /api/preselection. Tout le reste retombe sur les
// fichiers statiques — donc rien ne change pour les pages existantes (dégradation propre).
//
// Il RÉUTILISE la logique de functions/api/preselection.js (aucune duplication) : ce fichier existe
// pour le modèle Cloudflare Pages ; celui-ci fait pareil pour le modèle Worker. Même moteur, mêmes
// garde-fous (lecture seule, aucune donnée nominative).
import * as preselection from "./functions/api/preselection.js";
import * as diagnostic from "./functions/api/diagnostic.js";
import * as verifier from "./functions/api/verifier.js";

// Table de routage : chemin → module Function (mêmes handlers que le modèle Pages).
const ROUTES = {
  "/api/preselection": preselection,
  "/api/diagnostic": diagnostic,
  "/api/verifier": verifier,   // seul endpoint qui accepte un POST utile (le brouillon à analyser) — mais toujours AUCUNE écriture
};

export default {
  async fetch(request, env) {
    const { pathname } = new URL(request.url);
    const mod = ROUTES[pathname];
    if (mod) {
      if (request.method === "GET") return mod.onRequestGet({ request, env });
      if (request.method === "POST") return mod.onRequestPost({ request, env });
      return new Response(JSON.stringify({ erreur: "Méthode non autorisée." }), {
        status: 405, headers: { "Content-Type": "application/json; charset=utf-8" },
      });
    }
    // Tout le reste : fichiers statiques du même déploiement (pages Vue IA, données, application).
    return env.ASSETS.fetch(request);
  },
};
