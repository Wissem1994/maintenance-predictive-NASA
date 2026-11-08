# Démonstration professionnelle reproductible

## Préparer

Démarrer les deux terminaux décrits dans le README. Vérifier /api/health et /docs. Entraîner les modèles si artifacts est vide ; le frontend affiche honnêtement leur absence.

Prévoir une présentation de cinq à dix minutes, sans présenter le prototype comme un système de protection industrielle.

## Trame NASA

1. Ouvrir Données & traçabilité : essai 2, quatre canaux, 984 fichiers, source expérimentale.
2. Expliquer les 20 480 points à 20 kHz et la différence acquisition 2004/réception actuelle.
3. Dashboard : essai 2, canal 1, ×60, trente derniers fichiers. Le déplacement dans l’historique est explicite ; pas de scénario synthétique masqué.
4. Démarrer, ouvrir la fiche et Analyse vibratoire. Montrer signal, FFT et caractéristiques.
5. Attendre au moins trois mesures atypiques (environ vingt secondes après le premier fichier pour trois observations à ×60). Un seuil peut ne pas se déclencher immédiatement selon position et calibration ; examiner les valeurs réellement observées.
6. Montrer le modèle, ses partitions et ses limites. Le défaut extérieur du roulement 1 est documenté en fin d’essai, sans label de début exact.
7. Acquitter l’alerte et créer une intervention, puis arrêter le rejeu.

## Trame simulation

1. Arrêter toute acquisition, consulter Simulation et démarrer avec seed 42.
2. Montrer 20 équipements et les paramètres synthétiques.
3. Fiche sim-01 → Dégradation progressive. Le contenu impulsionnel et RMS augmentent avec l’âge du scénario.
4. Attendre l’alerte persistante (plusieurs cycles ; un anti-spam existant peut différer la réouverture).
5. Acquitter, créer une intervention, choisir Maintenance corrective puis Retour à la normale.
6. Montrer l’historique et redémarrer pour vérifier que l’intervention est conservée.

## Script automatique

Backend actif :

```powershell
.venv\Scripts\python.exe -m scripts.demo --mode simulation
# ou une fenêtre historique NASA réelle
.venv\Scripts\python.exe -m scripts.demo --mode nasa
```

Le script démarre les machines, observe les mesures, commande une dégradation (simulation), attend une alerte, acquitte, crée une intervention et conserve les identifiants réellement renvoyés. En simulation, il termine aussi une intervention fictive et commande la récupération. Il s’arrête après le parcours, sauf --keep-running. En NASA, après trois nouvelles mesures, une alerte persistante déjà active peut être réutilisée et son identifiant est explicitement marqué reused_existing_alert=true ; la déduplication ne crée pas artificiellement une nouvelle alerte. La simulation attend une nouvelle alerte de son exécution. Ne pas lancer ce script pendant un test Playwright utilisant la même base.

## Tests navigateur

Les deux serveurs doivent être lancés. `cd frontend; npm.cmd run e2e` sous PowerShell, ou commandes séparées si souhaité. Le test utilise Edge déjà installé via Playwright, sans télécharger un navigateur. Adapter channel dans playwright.config.ts pour un autre poste ; ne pas annoncer un passage sur un navigateur non testé.

Les captures desktop/mobile sont dans docs/reports. Le test crée une intervention nommée « Inspection démonstration Playwright » dans la vraie base locale ; ce sont des traces de démonstration, pas des travaux industriels exécutés.

## Questions d’entretien utiles

- Pourquoi un score d’anomalie ne donne-t-il pas directement une probabilité de panne ?
- Pourquoi séparer les fichiers/essais avant le fenêtrage ?
- Que manque-t-il pour mesurer les faux positifs et le délai d’anticipation sur NASA ?
- Comment gérer une modification de vitesse, charge ou capteur en usine ?
- Comment valider les seuils avec les maintenanciers et les incidents réels ?
- Pourquoi les métriques AI4I ne justifient-elles aucune promesse sur les vibrations réelles ?
