# Guide utilisateur

## Sources

Le sélecteur NASA/Simulation change les données consultées. La bannière indique toujours la provenance. Une seule session d’acquisition fonctionne à la fois ; arrêter la session avant d’en lancer une dans l’autre mode.

**NASA Replay** : fichiers expérimentaux historiques, pas des mesures acquises aujourd’hui. Les températures et vitesses absentes restent vides. **Simulation** : mesures entièrement synthétiques, hypothèses et graine documentées.

## Dashboard et direct

Démarrer depuis le panneau source. Pour NASA, choisir l’essai, le canal, la vitesse et le début ou les trente derniers fichiers. À ×60 sur l’essai 2, l’intervalle historique de dix minutes devient dix secondes d’attente. Le changement de vitesse n’altère pas la fréquence d’échantillonnage de 20 kHz à l’intérieur des fichiers.

Les KPI décrivent le parc consulté et les dernières observations. « Arrêté » signifie aucun moteur actif pour cet équipement ou un arrêt synthétique, pas une panne expérimentale inférée. La liste d’attention trie les dernières anomalies selon la baseline robuste. Un score est un indicateur d’écart, pas une probabilité.

Cliquer une ligne ou utiliser Entrée sur celle-ci pour accéder à la fiche. Le WebSocket déclenche l’actualisation ; un rechargement périodique et une reconnexion progressive assurent la resynchronisation de la vue.

## Fiche équipement et analyse

La fiche présente tendance RMS, score, caractéristiques, alertes et interventions. Le filtre Du/Au porte sur le temps de mesure, donc l’année 2004 pour l’essai 2, même si le rejeu est lancé aujourd’hui. CSV exporte les points affichés, au plus 1 000.

Analyse vibratoire : choisir l’équipement, la mesure A puis une référence B éventuelle. Les courbes temporelles et FFT proviennent du fichier source ou du signal synthétique reconstruit. Comparer RMS, kurtosis, crest factor et amplitude crête à crête. Les aperçus sont réduits pour la fluidité, sans changer les caractéristiques calculées sur tous les points.

## Alertes

Le centre propose recherche, gravité, statut et pagination. Déplier les valeurs déclenchantes. La coche acquitte ; la double coche résout ; la clé ouvre une intervention. Résoudre manuellement ne remet pas une machine en état nominal et ne corrige pas le signal.

Une condition doit persister pendant trois observations par défaut. Le retour sous le seuil ×0,9 pendant trois observations résout automatiquement. Déduplication pendant l’état actif et délai anti-spam après résolution. Les interruptions normales du rejeu et ses longs intervalles historiques ne sont pas des pertes de capteurs.

Configurer modifie les seuils synthétiques de démonstration. Les réglages sont propres au lancement backend. Le son est désactivé par défaut et nécessite un clic pour activer l’audio du navigateur. Le thème clair/sombre est disponible dans la barre latérale.

## Simulation

Démarrer 20 machines depuis le dashboard. Ouvrir une fiche et choisir parmi neuf scénarios. Dégradation augmente progressivement le contenu vibratoire, échauffement modifie la température, arrêt/maintenance ramènent la vitesse à zéro, retour à la normale décroît progressivement. Un cycle est une étape du simulateur ; ce n’est pas une cadence d’acquisition industrielle validée.

## Maintenance et modèles

Créer une intervention depuis le centre, une fiche ou la page maintenance. Motif obligatoire, priorité, date de planification facultative, commentaires. Modifier statut et commentaires sur la carte puis enregistrer. Une intervention est un suivi ; elle ne commande aucun automate.

Modèles IA affiche les métadonnées et limites de chaque détecteur de la source sélectionnée. Le complément tabulaire AI4I, quand présent, est identifié séparément comme synthétique et comme classification de l’état présent. Ses performances ne sont jamais transférées aux machines NASA.

## Historique

Mesures, alertes et interventions survivent au redémarrage. Les acquisitions interrompues ne reprennent pas automatiquement. Le chemin des bruts doit être conservé pour relire un signal historique. Les dates de mise en service du parc synthétique sont fictives et marquées comme telles.
