# Modèles et méthodologie d’évaluation

## NASA : détection d’anomalies par essai et canal

Objectif : détecter un changement des caractéristiques vibratoires par rapport au début du même essai. Aucun modèle de probabilité de panne future n’est disponible.

Variables : RMS, écart-type, kurtosis de Pearson, skewness, amplitude crête à crête, crest factor et énergie moyenne par trois bandes. Les autres caractéristiques sont conservées pour l’analyse. Pas de normalisation des signaux bruts avant RMS.

Chaque fichier donne une fenêtre complète par canal par défaut. En cas de fenêtres multiples, toutes les fenêtres du même horodatage restent dans la même partition. Ordre chronologique : 20 % entraînement, 10 % calibration du seuil, 70 % test. Pour les 984 fichiers : **196 / 99 / 689** par canal. Aucun mélange aléatoire de fenêtres voisines.

Le début d’essai est une hypothèse de référence nominale, sans annotation prouvant l’absence de défaut latent. L’essai 2 est partagé par quatre roulements sur le même banc ; les canaux ne sont pas des essais indépendants et la validation sur le même essai ne prouve pas le transfert à une nouvelle machine.

### Baseline

Médiane et écart absolu médian, appris sur la référence uniquement. Échelle : 1,4826 × MAD ; plancher max(1 % de la médiane absolue, 1e-8) pour les variables quasi constantes. Score de baseline : maximum des écarts absolus normalisés. Dépassement de référence à z > 6, convention de démonstration non industrielle.

### Isolation Forest

RobustScaler appris sur le train, 150 arbres, seed 42. Score exposé : **−score_samples**. Plus il est élevé, plus le fichier est atypique pour le détecteur. Le seuil est le quantile 0,99 des scores de calibration. Ce quantile est un seuil empirique ; il n’impose pas un taux industriel de faux positifs et ne garantit pas une calibration probabiliste.

Le score n’est jamais converti en pourcentage de panne. `failure_probability` et `health_index` restent null. Le risque qualitatif vaut nominal, à surveiller, ou élevé selon dépassement du seuil et z > 6 ; ce sont des niveaux de triage, pas des diagnostics.

### Résultats observés sur l’essai 2

| Canal | Proportion de fichiers test au-dessus du seuil IF | Dépassement baseline z > 6 |
|---|---:|---:|
| 1 | 0,67344 | 0,65022 |
| 2 | 0,53266 | 0,22351 |
| 3 | 0,19303 | 0,18287 |
| 4 | 0,47750 | 0,40784 |

Ce tableau mesure des dépassements, **pas l’exactitude**. Des canaux non documentés comme défaillants déclenchent aussi : couplage mécanique, dérive, sensibilité au choix de référence et au seuil sont des explications possibles, non établies causalement par cette analyse.

Sans labels par fichier, précision/rappel/F1/PR-AUC, matrice de confusion, faux positifs/négatifs et fausses alertes par heure ne sont pas calculables. Le temps précis d’apparition du défaut n’est pas fourni ; un délai de détection validé avant panne n’est donc pas annoncé. Une future annotation experte pourrait permettre ces évaluations, avec sensibilité aux hypothèses et validation sur essais tenus à l’écart.

## Détecteur du simulateur

Modèle distinct, entraîné exclusivement sur le générateur nominal : 100 cycles × 20 machines. Séparation par cycle 20/10/70, toutes les machines d’un cycle dans la même partition. Le taux d’anomalies test constaté est environ 0,01214. Il décrit le générateur synthétique, pas une usine.

La graine et le cycle suffisent à reconstruire le signal. Les conditions artificielles sont connues par construction ; les données ne constituent pas une validation de transfert.

## AI4I : modèle tabulaire complémentaire

10 000 lignes téléchargées depuis UCI, données **synthétiques**. Variables d’entrée : Type, températures air/processus en K, vitesse en rpm, couple en Nm, usure en minutes. Identifiants et cinq indicateurs de modes de panne exclus des entrées, ainsi que la cible Machine failure.

Ordre UDI conservé, partitions disjointes **6 000 entraînement / 2 000 calibration / 2 000 test**. Les UDI ne sont pas présentés comme des dates ni des machines réelles identifiées. Les dépendances résiduelles de la séquence synthétique et la dérive entre blocs limitent l’interprétation.

Random Forest : 200 arbres, profondeur max 12, feuilles min 3, pondération de classes, seed 42. OneHotEncoder appris sur train ; calibration sigmoïde sur un estimateur gelé (FrozenEstimator), sans réentraîner sur le test. Seuil de décision 0,5, non optimisé pour un coût de maintenance réel.

**Cible : panne présente sur la ligne courante**, sans horizon futur validé. Ces probabilités ne sont pas appliquées aux équipements NASA ou du simulateur.

Résultats effectivement calculés :

| Mesure | Modèle calibré | Référence constante (prior du train) |
|---|---:|---:|
| Précision | 0,79310 | 0 |
| Rappel | 0,58974 | 0 |
| F1 | 0,67647 | 0 |
| PR-AUC (average precision) | 0,67071 | 0,01950 |
| Brier (plus bas préférable) | 0,00982 | 0,01965 |

Matrice de confusion test, lignes vraies classes [0,1], colonnes prédites [0,1] : **[[1955, 6], [16, 23]]**. Donc six faux positifs et seize faux négatifs sur ce test, sans unité temporelle réelle pour des alertes par heure. La courbe de calibration empirique à cinq bandes et le détail sont dans [ai4i_validation.json](reports/ai4i_validation.json). Le Brier et la courbe sont des diagnostics sur ce domaine synthétique, pas une certification des probabilités en usine.

## Traçabilité et MLOps

Chaque modèle sauvegarde prétraitement, variables, version, configuration, seuil, partitions, métriques, limites et provenance. Les artefacts NASA incluent la version Python/scikit-learn et le SHA256 du CSV d’entrée. Les fichiers Joblib restent hors Git ; les rapports JSON vérifiables peuvent être conservés dans docs/reports.

Le registre backend choisit la version la plus récente pour chaque domaine/essai/canal. Recharger explicitement après entraînement. Les données d’entraînement et de calibration ne sont jamais remplacées par les observations de démonstration du frontend. MLflow n’est pas requis pour ce prototype.

## Paderborn

Classification de défauts non implémentée faute de lot importé et vérifié. Le prochain protocole devra tenir des roulements/essais complets à l’écart, comparer une baseline et Random Forest, publier une matrice de confusion, et distinguer dommages artificiels et dommages issus d’essais de durée de vie.
