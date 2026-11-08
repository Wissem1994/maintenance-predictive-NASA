# Installation et environnement

## Inspection effective du 7 novembre 2026

| Composant | Observation |
|---|---|
| Système | Windows 10, version NT 10.0.19045 ; PowerShell 5.1 |
| Python du PATH | 3.8.8, trop ancien pour le projet |
| Autre Python présent | 3.14.10, non retenu pour la pile scientifique demandée |
| Python du projet | 3.12.13 téléchargé par uv dans .runtime, environnement .venv |
| pip existant | 21.0.1 pour 3.8 ; 26.2.2 pour 3.14 |
| uv | 0.11.27 déjà installé |
| Node.js / npm | 26.13.0 / 11.20.0 |
| Git | 2.40.0.windows.1 ; dépôt local initialisé sans configuration globale |
| Docker | CLI 29.9.2 présente ; moteur indisponible |
| Extraction | bsdtar 3.5.2 présent ; pas de 7z CLI, py7zr utilisé dans .venv |
| Espace disque | Plus de 600 Go libres lors de l’inspection via Python |
| RAM | Interrogation CIM refusée ; capacité non vérifiée |

Le bac à sable Codex a nécessité une autorisation réseau pour les téléchargements et une autorisation de lecture pour esbuild. Ce sont des contraintes de la session d’exécution ; elles ne modifient pas les instructions locales du projet. Aucun logiciel système n’a été installé.

## Windows, nouveau poste

Prérequis : Python **3.11 ou 3.12** (3.12 recommandé), Node.js récent compatible Vite (22/24 LTS recommandés ; 26.13 testé ici), npm et Git. Prévoir environ 8 Go pour une extraction complète des données et caches.

Avec uv déjà installé :

```powershell
$env:UV_CACHE_DIR = "$PWD\.cache\uv"
$env:UV_PYTHON_INSTALL_DIR = "$PWD\.runtime\python"
uv python install 3.12 --no-bin
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r backend/requirements-dev.txt
cd frontend
npm.cmd ci --cache ../.cache/npm
cd ..
.venv\Scripts\python.exe -m scripts.init_db
```

Ces commandes isolent Python dans le projet. Sans uv, installer Python avec son propre accord puis :

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
cd frontend
npm.cmd ci
cd ..
.venv\Scripts\python.exe -m scripts.init_db
```

Le script `scripts\setup.cmd` automatise la création de l’environnement, les dépendances et les migrations. Il réutilise .venv s’il existe. Une installation créée par uv peut ne pas contenir pip ; utiliser alors `uv pip`, comme dans le script.

Le script ne télécharge pas automatiquement l’archive NASA. Suivre [datasets.md](datasets.md).

## Windows : lancement en une étape

Double-cliquer sur **`Lancer PredictMaint.cmd`** à la racine, ou sur **Lancer PredictMaint** sur le Bureau. Le navigateur s’ouvre automatiquement sur http://localhost:5173 une fois l’API et l’interface prêtes. Les deux serveurs fonctionnent en arrière-plan ; la fenêtre de lancement se ferme. En cas d’erreur, elle reste ouverte et indique le problème.

Double-cliquer sur **`Arreter PredictMaint.cmd`** ou **Arreter PredictMaint** sur le Bureau pour arrêter les serveurs créés par le lanceur. Le backend termine ses requêtes et ferme son moteur avant de s’arrêter ; un arrêt forcé sert de secours s’il ne répond plus. Fermer la page web ne coupe pas les serveurs.

Le lanceur sérialise les doubles clics simultanés et réutilise les serveurs PredictMaint déjà prêts. Il refuse un port occupé par un autre service. Il ne termine que les processus qu’il a enregistrés, après vérification de leur identifiant, heure de création et exécutable. Des serveurs démarrés manuellement restent à arrêter dans leurs terminaux.

Les journaux du dernier démarrage de chaque serveur sont dans `.cache/launcher/logs/` (`backend.err.log`, `backend.out.log`, `frontend.err.log`, `frontend.out.log`). `launcher.log` conserve l’historique du lanceur. Aucun téléchargement ni réentraînement n’est effectué au lancement ; les migrations de base sont appliquées comme dans le script backend manuel.

Pour installer ou actualiser les deux raccourcis du Bureau, depuis la racine :

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-shortcuts.ps1
# Si le Bureau est redirigé et n’est pas détecté : ajouter -DesktopPath "chemin du Bureau"
```

Le projet doit rester à son emplacement actuel pour que les raccourcis fonctionnent. Après déplacement, recréer les raccourcis. L’installation préalable (`scripts\setup.cmd`) reste nécessaire sur un nouveau poste.

Pour vérifier le démarrage sans ouvrir le navigateur :

```powershell
& ".\Lancer PredictMaint.cmd" -NoBrowser
```

## Lancement manuel avec deux terminaux

Terminal 1 : `.\scripts\start-backend.cmd`.

Terminal 2 : `.\scripts\start-frontend.cmd`.

Adresse : http://localhost:5173. Arrêt : Ctrl+C dans chaque terminal. Ne lancer qu’un processus backend : le moteur d’acquisition est local à ce processus.

Pas besoin d’activer PowerShell ni de modifier ExecutionPolicy. `npm.cmd` contourne uniquement le choix du fichier exécutable npm.ps1 bloqué, sans changer la politique système.

## Linux/macOS

Installer les prérequis avec son gestionnaire habituel après accord. Les scripts ne les installent pas :

```sh
sh scripts/setup.sh
# terminal 1
sh scripts/start-backend.sh
# terminal 2
sh scripts/start-frontend.sh
```

Ils attendent `python3.12`. Remplacer par `python3.11` dans setup.sh si nécessaire. Pour RAR, utiliser bsdtar/libarchive si disponible ou extraire manuellement. Les scripts Linux/macOS sont fournis mais **non exécutés sur ce poste Windows**.

## Configuration

Copier .env.example vers .env si besoin. Les valeurs par défaut suffisent. Le backend lit .env à la racine. Pour changer l’URL frontend, créer `frontend/.env.local` avec `VITE_API_URL=http://localhost:8000` et redémarrer Vite. Cette valeur est intégrée au build.

SQLite par défaut : `data/predictmaint.db`. Conserver aussi les fichiers `-wal` et `-shm` pendant une sauvegarde à chaud ; préférer une sauvegarde SQLite cohérente ou arrêter le backend avant copie. Ne pas supprimer la base pour appliquer une migration.

## Dépannage

- Port occupé : arrêter l’autre instance ou choisir un port et mettre à jour URL/CORS.
- Aucun essai : conserver les dossiers 1st_test/2nd_test/3rd_test et les noms YYYY.MM.DD.HH.MM.SS.
- Doublons de données : l’import refuse deux fichiers du même essai et horodatage ; enlever la copie redondante après vérification.
- Scores absents : entraîner puis cliquer Recharger dans Modèles IA ou redémarrer le backend.
- Caches : .cache contient les caches de projet ; ne pas utiliser des dossiers temporaires appartenant à un autre compte Windows.
- Docker : inutile ; aucun démarrage du moteur n’est requis.
