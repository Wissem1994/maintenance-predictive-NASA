# Limites, risques et sécurité

## Science

La référence NASA est un début d’essai supposé nominal. Plusieurs canaux du même arbre partagent les conditions de fonctionnement ; ils ne constituent pas une validation indépendante. Le test est postérieur dans le même essai ; une validation par essais et équipements supplémentaires reste nécessaire.

Les défauts finaux sont documentés, pas le moment précis du début de dégradation. Aucun label par fenêtre, RUL, horizon de panne ou calibration d’une probabilité de panne future n’est inventé. Les métriques de classification NASA restent null. L’unité d’amplitude source n’est pas assimilée à mm/s ni soumise à une norme ISO de sévérité.

AI4I est synthétique et prédit l’état présent. Son Brier et sa courbe de calibration sont évalués sur un seul bloc synthétique, avec peu de pannes positives. Ils ne valident ni la causalité des variables ni une probabilité transférable à une vraie machine.

Paderborn n’est pas importé ; la classification de défauts de roulements reste à réaliser avec séparation par roulement/essai et examen des conditions de licence.

## Simulateur

Sinusoïdes à la rotation et à une composante haute fréquence, bruit gaussien, impulsions amorties pour les scénarios de roulement. Température à évolution exponentielle simplifiée ; charge lente sinusoïdale ; couple approximatif uniquement sur les transmissions. Les coefficients sont pédagogiques, sans identification physique sur un équipement Flender réel.

Le signal fait 4 096 points à 20 kHz par cycle synthétique. Il ne représente pas un enregistrement continu de toute la période entre cycles. La reproductibilité dépend de seed/index/cycle/scénario/âge et des versions de bibliothèques conservées.

## Logiciel

- Un backend et un moteur d’acquisition par instance ; pas de haute disponibilité ni de workers multiples.
- SQLite adapté au prototype ; pas de test de charge industriel.
- Les réglages d’alerte, compteurs de persistance et scénarios sont en mémoire ; un redémarrage remet ces états à zéro.
- Les sessions historiques restent persistées ; leur reprise après arrêt de processus n’est pas automatique.
- Les modèles doivent être réentraînés si bruts/variables/versions changent. Les artefacts Joblib ne sont pas compatibles indéfiniment entre versions.
- Les listes auxiliaires et cartes de maintenance chargent jusqu’à 200 éléments ; le journal d’alertes est paginé. Les KPI sont des agrégats SQL sur tout l’historique.
- L’interface limite l’historique affiché à 1 000 points. Export CSV porte sur cet ensemble affiché.
- La configuration Vite produit un chunk graphiques volumineux ; acceptable pour une démonstration locale, à optimiser avant distribution contrainte.
- Les scripts Linux/macOS et migration PostgreSQL n’ont pas été exécutés sur ce Windows.
- Docker n’a pas été testé : moteur indisponible, sans effet sur le fonctionnement local.

## Sécurité de cette version

Serveurs liés à 127.0.0.1, CORS et origine WebSocket contrôlés, tailles et bornes de requêtes validées, ressources vérifiées, chemins de signal bornés au répertoire NASA, files WebSocket bornées, migrations et FK.

Pas d’authentification, RBAC, TLS, audit nominatif, antivirus d’upload ni isolation des utilisateurs. Aucun accès réseau public ne doit être ouvert pour cette version. Aucun pilotage d’équipement réel.

Importer uniquement les archives institutionnelles et les artefacts entraînés localement. Joblib repose sur une désérialisation de confiance. Avant industrialisation : gestion des identités, secrets, sauvegardes, rétention, contrôle des versions, revue des licences et de sécurité, surveillance et validation métier.
