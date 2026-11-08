# Adaptation à une usine de réducteurs

Sur un banc d’essai de réducteur, relier chaque acquisition à la référence du réducteur, au numéro de série, au rapport de réduction, aux roulements, aux capteurs calibrés, à la vitesse, au couple, à la charge, au lubrifiant et au protocole d’essai. Les signatures dépendent de ces conditions ; comparer des références comparables avant toute alarme.

## Acquisition

**OPC UA** : lire les variables d’automates et de bancs via une passerelle, certificats gérés, abonnements horodatés et qualité de donnée. Conserver l’heure équipement, l’heure passerelle et l’heure serveur, avec synchronisation NTP/PTP adaptée.

**MQTT** : publier des caractéristiques et événements sur des topics machine/capteur, avec identifiants et schémas versionnés, QoS et stratégie de rattrapage explicités. Ne pas envoyer inutilement tous les points vibratoires haute fréquence dans un broker généraliste.

Les signaux bruts peuvent rester en stockage objet ou fichiers structurés, avec SHA256 et liens depuis une base relationnelle. Calculer les caractéristiques près du banc si nécessaire ; conserver des segments bruts pour investiguer les alertes.

## Maintenance et production

**ERP/GMAO** : convertir une alerte validée par un opérateur en demande ou ordre d’intervention. Synchroniser identifiant, statut, technicien, pièce, cause constatée, durée d’arrêt et rapport de contrôle. Utiliser des clés d’idempotence et une file de reprises.

**MES** : contextualiser les phases d’essai/production, gammes, séries, changements de charge, arrêts planifiés et interventions. Écarter les phases de démarrage/arrêt du domaine nominal quand cela est justifié, sans effacer leurs traces.

## Validation avant déploiement

Collecter plusieurs machines et essais avec événements expertisés. Définir le défaut, l’horizon d’intérêt et les coûts d’erreurs avec les équipes. Préserver des équipements/essais entiers pour validation externe, évaluer fausses alertes par heure opérationnelle et délais d’anticipation avec incertitude.

Commencer en observation silencieuse, comparer aux inspections, puis mettre en service des recommandations supervisées. Les décisions de sécurité et de protection restent dans les systèmes industriels qualifiés.

## Exploitation

PostgreSQL et stockage objet, registre de modèles avec approbation, suivi des distributions et de dérive, contrôle d’intégrité des capteurs, logs structurés, sauvegardes/restaurations testées, droits par atelier et traçabilité des interventions. La calibration doit être réévaluée après changement de matériel, capteur ou protocole.

Ces intégrations sont des pistes documentées ; aucun connecteur MQTT/OPC UA/ERP/MES réel n’est implémenté dans ce dépôt.
