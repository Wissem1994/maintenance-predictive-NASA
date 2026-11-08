# Compte rendu de réalisation

Tous les fichiers sont dans le dépôt fourni. Les commandes ci-dessous sont exécutées depuis sa racine, sauf indication frontend. Les résultats finaux sont distingués des extensions conditionnelles.

## Phase 1 — Environnement et données NASA

**Réalisé :** inspection Windows/outils, Git initialisé, Python 3.12.13 isolé et .venv, dépendances scientifiques, préparation React. Archive institutionnelle réelle téléchargée, essai 2 extrait et exploré, import strict avec empreintes, 3 936 caractéristiques, figures temporelles/FFT/RMS.

**Fichiers :** .gitignore, .env.example, pyproject.toml, backend/requirements*.txt, ml/ingestion/nasa.py, ml/features/signal.py, scripts/download_nasa.py, scripts/import_nasa.py, scripts/explore_nasa.py, backend/tests/test_signal.py, backend/tests/test_nasa.py, data/dataset_registry.json, docs/reports/nasa_*.

**Commandes exécutées :** inspection Get-Command et --version ; git init ; uv python install 3.12 --no-bin avec répertoire local ; uv venv ; uv pip install ; curl de l’archive PHM ; extraction ZIP/7z puis tar du RAR de l’essai 2 ; python -m scripts.import_nasa --trial 2nd_test ; python -m scripts.explore_nasa ; pytest ciblé.

**Résultat :** sept tests initiaux réussis, dont lecture d’un fichier NASA réel. 984 fichiers × quatre canaux, 20 480 points, intervalle constaté 600 secondes. Figures inspectées visuellement.

**Blocages et replis :** lien direct NASA réinitialisé, miroir PHM référencé par NASA utilisé. Python PATH 3.8 et Python 3.14 non retenus ; Python local 3.12 téléchargé avec autorisation, sans installation système. Dossier temporaire partagé refusé : tests déplacés dans .cache. Docker présent mais moteur indisponible.

**Vérifier :** suivre README puis ouvrir les PNG/inventaire ; relancer import/explore sur les bruts. Essais 1 et 3 restent compressés, leur pipeline est pris en charge mais non validé sur ces lots.

## Phase 2 — Premier modèle

**Réalisé :** baseline médiane/MAD et Isolation Forest par canal NASA, prétraitement train uniquement, seuil de calibration, test chronologique, artefacts/rapports et inférence.

**Fichiers :** ml/training/anomaly.py, scripts/train.py, artifacts/*.json et *.joblib locaux, backend/tests/test_ml_simulation.py, docs/ml-methodology.md, docs/reports/nasa_model_validation.json.

**Commande :** python -m scripts.train. Quatre détecteurs entraînés, partitions 196/99/689 par canal. Métriques réellement calculées ; proportions d’anomalies publiées, métriques impossibles null.

**Tests :** contrôle de roundtrip Joblib, absence de probabilité inventée et séparation chronologique, inclus dans les tests finaux.

**Limite :** hypothèse de début nominal et pas de labels par fenêtre ; pas de précision/F1 NASA ni validation industrielle.

**Vérifier :** page Modèles IA, JSON de métadonnées et script d’entraînement.

## Phase 3 — Backend et persistance

**Réalisé :** FastAPI, commandes Pydantic, SQLAlchemy/SQLite WAL/FK, dix tables métier, index/contraintes, migration Alembic et API de gestion.

**Fichiers :** backend/app/core/config.py, database/session.py, models/entities.py, schemas/requests.py, main.py, alembic.ini, backend/alembic/, scripts/init_db.py, backend/tests/conftest.py et test_api.py.

**Commandes :** alembic revision --autogenerate -m initial_schema ; python -m scripts.init_db ; alembic check ; lancement Uvicorn et requêtes HTTP.

**Tests :** API, validation, absence de ressources, persistance après redémarrage, séparation des modes, interventions ; check Alembic final sans différence de schéma.

**Vérifier :** /docs et /api/health, puis arrêter/redémarrer sans supprimer data/predictmaint.db.

## Phase 4 — Rejeu NASA

**Réalisé :** sélection essai/canal, position initiale, pause/reprise/arrêt/reset, vitesses, attente historique réelle, inférence et transaction avant notification, temps de mesure/réception distincts.

**Fichiers :** backend/app/services/engine.py et registry.py, websocket/broker.py, routes dans main.py, backend/tests/test_acceptance.py.

**Commandes :** requêtes POST replay via tests et navigateur ; python -m scripts.demo --mode nasa.

**Tests :** chronologie et intervalle de 600 s, changement de vitesse en pause, API et vrai événement WebSocket, inférence NASA observée dans le parcours navigateur.

**Limite :** une session et un processus backend ; pas de reprise automatique après arrêt du processus.

**Vérifier :** NASA Replay, ×60, trente derniers fichiers ; observer un nouveau fichier toutes les dix secondes. Une alerte active est dédupliquée entre sessions ; le script peut la réutiliser explicitement après trois nouvelles mesures.

## Phase 5 — Interface

**Réalisé :** dashboard, supervision, fiche, analyse temporelle/FFT et comparaison, alertes, maintenance, modèles et provenance ; thème clair/sombre, responsive, son activable, reconnexion.

**Fichiers :** frontend/package.json et package-lock.json, Vite/TypeScript/Tailwind, src/App.tsx, hooks/, components/, pages/, styles/, App.test.tsx et e2e/.

**Commandes :** npm.cmd install ; npm.cmd test ; npm.cmd run build ; npm.cmd run dev ; npm.cmd run e2e et science.spec.ts.

**Tests :** trois composants réussis, compilation TypeScript/Vite réussie, parcours complet réussi, parcours scientifique réussi ; captures desktop/mobile inspectées. Vérification de l’absence de débordement horizontal sur mobile.

**Corrections :** autorisation de lecture des parents pour esbuild dans le bac à sable ; Playwright mis à jour en 1.65 pour Node 26 ; Vitest limité à ses tests ; sélecteurs Playwright rendus précis.

**Limite :** chunk graphiques de 560,81 ko minifié (159,27 ko gzip) avec avertissement Vite ; pas de mesure de performance sur réseau industriel contraint.

**Vérifier :** lancer les deux terminaux du README et naviguer sur chaque page.

## Phase 6 — Alertes

**Réalisé :** seuils synthétiques, anomalies persistantes, hystérésis, déduplication, anti-spam, absence au-delà de l’échéance attendue, historique, acquittement/résolution et commandes de scénario informatives.

**Fichiers :** backend/app/services/alerts.py, surveillance dans engine.py, pages/Operations.tsx, tests API et acceptation.

**Tests :** déclenchement, déduplication, acquittement, résolution, retour sous seuil, délai anti-spam, absence et reprise. Le parcours navigateur exige une nouvelle alerte créée après son démarrage ; il est passé en 44 secondes.

**Limite :** seuils non validés et réglages/compteurs en mémoire.

**Vérifier :** sim-01 → dégradation ; centre d’alertes → détails/valeurs, acquitter puis intervention.

## Phase 7 — Simulation

**Réalisé :** jusqu’à 20 équipements, neuf scénarios, signal/thermique/rotation/charge/couple simplifiés, graine, provenance et modèle nominal séparés.

**Fichiers :** simulation/industrial.py, scripts/train_simulation.py, routes/engine, tests de reproductibilité et scénarios.

**Commande :** python -m scripts.train_simulation ; simulation démarrée dans navigateur/tests ; scripts.demo.

**Tests :** graine reproductible, hausse des vibrations/températures, arrêt et maintenance, 20 machines effectivement reçues du backend.

**Limite :** générateur pédagogique, sans jumeau physique validé.

**Vérifier :** onglet Simulation, seed 42, fiche machine et scénario.

## Phase 8 — Compléments et suivi

**Réalisé :** interventions complètes, registre local de modèles, distributions/limites, AI4I téléchargé depuis UCI, Random Forest calibré, référence, matrice et courbe de calibration.

**Fichiers :** scripts/train_ai4i.py, docs/reports/ai4i_validation.json, registre/Science.tsx, tests d’acceptation du modèle sauvegardé.

**Commande :** python -m scripts.train_ai4i (archive déjà téléchargée) ; option --download disponible. Résultats : F1 0,67647 ; PR-AUC 0,67071 ; Brier 0,00982, sur 2 000 lignes test synthétiques.

**Limites :** classification présente AI4I, pas une panne future ni des vibrations. Paderborn non importé, licence CC BY-NC vérifiée ; sa classification reste conditionnelle à un lot acquis et validé. XGBoost/MLflow non ajoutés : pas de bénéfice nécessaire pour ce périmètre.

**Vérifier :** Modèles IA, section complémentaire AI4I, sans appliquer ses métriques au parc NASA.

## Phase 9 — Vérification et livraison locale

**Réalisé :** documentation installation/utilisation/API/données/ML/architecture/risques/démo/intégrations, scripts Windows et shell, tests d’intégration et navigateur, contrôle des origines WebSocket et des chemins de fichiers.

**Commandes finales :** pytest -q ; ruff check ; mypy --no-incremental ; alembic check ; npm test ; npm run build ; Playwright complet et parcours scientifique. Les résultats du script autonome sont consignés dans reports/demo-*.txt après exécution.

**Résultat final vérifié :** 19 tests Python réussis ; trois tests React réussis ; deux parcours Playwright exécutés et réussis dans la même suite ; Ruff/Mypy réussis ; build réussi ; aucune migration manquante détectée. Un avertissement de dépréciation AnyIO/Starlette et l’avertissement de taille du bundle restent documentés.

**Non vérifié :** exécution des scripts Linux/macOS, PostgreSQL, Docker et connecteurs industriels réels. Aucun déploiement externe ni logiciel système installé.

**Vérifier :** suivre le démarrage en deux terminaux et les commandes du README. Les bases et traces de démonstration restent locales ; aucune purge destructive n’est effectuée pour obtenir un résultat favorable.
