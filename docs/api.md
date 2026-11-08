# API REST et WebSocket

Référence exécutable : http://localhost:8000/docs ; contrat JSON : /openapi.json. Lancer les migrations avant Uvicorn. API locale sans authentification, CORS limité aux origines configurées.

## Endpoints

| Méthode et route | Fonction |
|---|---|
| GET /api/health | état de la base et du moteur |
| GET /api/datasets | disponibilité et essais NASA réels |
| GET /api/engine | session active, curseur/vitesse/temps |
| GET /api/summary?mode=nasa | agrégats SQL sur tout l’historique pour les KPI |
| GET /api/machines?mode=nasa | liste avec dernière mesure et prédiction |
| GET /api/machines/{id} | identité, provenance, capteurs |
| GET /api/machines/{id}/measurements | historique et caractéristiques |
| GET /api/machines/{id}/predictions | historique des inférences |
| GET /api/machines/{id}/signal?measurement_id=… | aperçu temporel, FFT et caractéristiques |
| GET /api/alerts | filtres mode, statut, gravité, machine et recherche |
| POST /api/alerts/{id}/acknowledge | acquittement idempotent d’une alerte active |
| POST /api/alerts/{id}/resolve | résolution idempotente |
| GET /api/alert-config | réglages de démonstration et portée mémoire |
| PUT /api/alert-config | seuils, hystérésis, temporisations, anti-spam |
| GET /api/maintenance | historique filtré par mode/machine |
| POST /api/maintenance | création validée, réponse 201 |
| PATCH /api/maintenance/{id} | statut et commentaires |
| GET /api/models | versions, métriques, distributions et limites |
| POST /api/models/reload | synchroniser les artefacts locaux entraînés |
| POST /api/replay/start | essai/canal/vitesse/position initiale |
| POST /api/replay/pause, resume, stop, reset | commandes de session |
| POST /api/replay/speed | vitesse ×1, ×10 ou ×60 |
| POST /api/simulation/start | graine et 1 à 20 équipements |
| POST /api/simulation/{id}/scenario | l’un des neuf scénarios |

Les commandes replay pause/resume/stop/reset pilotent la session active, y compris une simulation. Le mode de consultation frontend ne change pas la session d’acquisition ; arrêter explicitement avant un changement de source.

Listes paginées : {items,total,limit,offset}. Limits bornées ; offset ≥ 0. Mesures : since/until en horodatages ISO et session_id. Résultats par id décroissant ; le frontend inverse l’ordre pour le graphique. Les filtres temporels ne convertissent pas le fuseau NASA inconnu.

Réponses : 404 ressource absente ; 422 paramètres invalides ; 409 conflit de commande/état ; 503 base indisponible. Les commandes de démarrage ne créent aucun fichier NASA manquant.

## Exemples

```json
POST /api/replay/start
{"trial":"2nd_test","channel":1,"speed":60,"start_index":954}
```

```json
POST /api/simulation/start
{"seed":42,"machine_count":20}
```

```json
POST /api/simulation/sim-01/scenario
{"scenario":"degradation"}
```

```json
POST /api/maintenance
{"machine_id":"sim-01","reason":"Inspection du roulement","priority":"high","status":"open","comments":"Démonstration"}
```

## WebSocket /ws

Envoi initial {type:"state",state:{…}}. Événements update après transaction validée, alert pour changements de gestion, error en cas d’échec, heartbeat toutes les quinze secondes d’inactivité. Chaque update contient le mode et l’état d’acquisition. Le client recharge les ressources REST correspondantes pour resynchroniser la vue ; une reconnexion recharge aussi la vue.

Une file par client est bornée à 32 événements. En cas de saturation, message resync au lieu d’accumuler la mémoire. Les événements ne sont pas un journal durable ; les ressources SQLite constituent l’historique. L’origine WebSocket est contrôlée ; le frontend reconnecte avec un délai progressif plafonné à quinze secondes.

## Export du contrat

Serveur lancé :

```powershell
curl.exe http://localhost:8000/openapi.json -o docs/reports/openapi.json
```
