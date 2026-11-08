# Dictionnaire des données

## Tables persistantes

| Table | Rôle et clés principales |
|---|---|
| machines | id stable, nom/type, mode nasa ou simulation, statut, date fictive éventuelle, métadonnées de provenance |
| sensors | id, machine_id FK, type, unité déclarée, fréquence d’échantillonnage |
| measurements | id, machine_id/sensor_id FK, measured_at, received_at, provenance, source_file/hash, session_id, indicateurs scalaires |
| signal_features | measurement_id FK/PK, JSON des caractéristiques, début/taille de fenêtre, fréquence |
| predictions | measurement_id unique FK, machine_id/model_version FK, score, seuil, z, risque, booléen anomalie |
| model_versions | version PK, métadonnées JSON, chemin d’artefact local de confiance, actif |
| alerts | machine_id et mesure déclenchante, règle, gravité, valeurs, création/acquittement/résolution |
| maintenance_events | machine_id, motif, priorité/statut, planification/commentaires, dates création/mise à jour |
| replay_sessions | essai/canal, vitesse, état, curseur/total, dates UTC |
| simulation_sessions | graine, cycle, nombre d’équipements, état, dates UTC |

Les index machine/temps accélèrent l’historique. Les FK SQLite sont activées à chaque connexion ; une contrainte unique machine/session/horodatage évite les doublons d’acquisition. Les bruts restent sur disque, sans millions de lignes d’échantillons en base.

`measurement.measured_at` : NASA = temps local expérimental inconnu ; simulation = temps synthétique de cycle ancré à l’heure UTC de démarrage. `received_at` et dates de gestion = ISO 8601 UTC. Ne jamais interpréter le temps de réception comme le temps physique NASA.

Température, vitesse, charge et couple sont **null pour NASA**. Simulation : °C, tr/min, %, Nm fictifs. Couple seulement pour les deux types de transmission où il est pertinent.

## Caractéristiques

Pour x de N points, fréquence fs :

| Champ | Convention |
|---|---|
| mean | moyenne brute |
| rms | sqrt(mean(x²)), moyenne incluse |
| std / variance | moments de population, ddof=0 |
| kurtosis | Pearson, distribution normale ≈ 3 ; zéro conventionnel si variance nulle |
| skewness | moment standardisé, zéro conventionnel si variance nulle |
| peak_to_peak | max(x) − min(x) |
| crest_factor | max(abs(x))/RMS ; 0 si RMS nul |
| energy | somme discrète x² ; dépend de N et de l’unité source |
| duration_seconds | N/fs |
| band_low | puissance moyenne intégrée PSD [0,1000[ Hz |
| band_mid | puissance moyenne intégrée PSD [1000,5000[ Hz |
| band_high | puissance moyenne intégrée PSD [5000,fs/2] Hz |
| dominant_frequency_1..3 | pics locaux FFT décroissants en amplitude, Hz ; 0 si absents |

Les bandes sont des intégrales discrètes de PSD (unité amplitude²), pas la somme d’énergie discrète du champ energy. PSD et FFT utilisent Hann et retrait de la moyenne ; les autres caractéristiques temporelles restent brutes. Le crest factor de données centrées et celui du signal brut peuvent différer.

L’aperçu min/max peut dépasser légèrement la moitié des points de sa limite théorique en cas de dernier bloc ; il reste borné autour de 512, indépendamment de la taille brute. Un aperçu n’est pas un fichier rééchantillonné destiné à l’entraînement.

## Import CSV et manifeste

Une ligne = dataset/provenance, essai, roulement, canal, horodatage, fichier et SHA256, début/taille de fenêtre, fréquence, caractéristiques. Le manifeste inclut le nombre découvert/traité, le caractère partiel de l’import et les paramètres.

Les KPI du dashboard sont calculés par agrégats SQL sur tout l’historique via /api/summary, sans dépendre de la taille des listes chargées. Le journal d’alertes reste paginé.
