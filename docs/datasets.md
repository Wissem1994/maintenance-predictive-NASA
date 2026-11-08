# Datasets, provenance et import

Le registre machine lisible est [dataset_registry.json](../data/dataset_registry.json). Les empreintes de l’archive et du document IMS sont dans [nasa_download.json](reports/nasa_download.json).

## NASA IMS

Source : [NASA IMS Bearings](https://data.nasa.gov/dataset/ims-bearings). Le [dépôt NASA PCoE](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/) désigne le [miroir PHM Society](https://data.phmsociety.org/nasa/). Attribution : J. Lee, H. Qiu, G. Yu, J. Lin et Rexnord Technical Services (2007), IMS, University of Cincinnati, Bearing Data Set, NASA Prognostics Data Repository.

Le portail affiche « other-license-specified » et renvoie à [government works](https://www.usa.gov/government-works). Cela ne justifie pas d’attribuer une licence CC0 à tous les travaux universitaires déposés. Conserver les notices et l’attribution ; vérifier les droits pour toute redistribution commerciale.

Le lien direct NASA a échoué dans cette session (connexion réinitialisée). Le miroir institutionnel PHM a répondu et l’archive complète a été téléchargée. Aucune copie communautaire non vérifiée n’a été substituée.

### Format documenté et conventions

| Essai | Canaux | Correspondance | Défaut constaté en fin d’essai selon document IMS |
|---|---:|---|---|
| 1st_test | 8 | 1–2 → roulement 1 ; 3–4 → 2 ; 5–6 → 3 ; 7–8 → 4 | Bague intérieure roulement 3 ; élément roulant roulement 4 |
| 2nd_test | 4 | canal n → roulement n | Bague extérieure roulement 1 |
| 3rd_test | 4 | canal n → roulement n | Bague extérieure roulement 3 |

Le document de l’archive confirme ces mappings. Il annonce 2 156, 984 et 4 448 fichiers pour les trois essais. Le nombre réel du troisième lot devra être confronté au document lors de son extraction ; le sous-dossier « 4th_test » peut être un alias de conditionnement du troisième essai. L’import conserve le chemin original et normalise cet alias en 3rd_test.

Chaque fichier ASCII contient 20 480 lignes et 4 ou 8 colonnes. Fréquence **documentée** : 20 kHz. Calcul : 20 480 / 20 000 = **1,024 s**. Ne pas remplacer silencieusement la fréquence par 20,48 kHz au motif que le document décrit approximativement des fenêtres d’une seconde.

Les horodatages viennent des noms de fichiers, jamais de leur date de copie. Le fuseau n’est pas documenté : stockage comme horloge expérimentale sans suffixe UTC. `received_at` est un horodatage UTC distinct.

Les fichiers ne fournissent pas de température, vitesse instantanée, couple ni charge instantanée. La vitesse nominale du banc décrite dans le document est une condition d’essai, pas une série mesurée ; l’API renvoie donc null pour ces mesures absentes. Les amplitudes sont conservées en unité source non vérifiée ; aucune norme de vibration en mm/s n’est appliquée.

### Import manuel

1. Télécharger « IMS.zip » depuis NASA, ou « 4. Bearings.zip » depuis le miroir PHM.
2. Extraire le ZIP, puis IMS.7z, puis les archives RAR. Aucun outil système n’est installé par le projet.
3. Placer les fichiers avec leur arborescence sous :

```text
data/raw/nasa_ims/
  1st_test/.../2003.10.22.12.06.24
  2nd_test/2004.02.12.10.32.39
  3rd_test/4th_test/.../2004.03.04.09.27.46
```

4. Exécuter `python -m scripts.import_nasa --trial 2nd_test`, puis explore_nasa et train.
5. L’import rejette formats, nombres de points, NaN/Inf ou timestamps dupliqués. Ne jamais compléter un fichier NASA manquant par un signal simulé.

Le script download_nasa propose `--source nasa`, `--source phm`, `--extract` et `--extract-only`. Il écrit via un fichier .part et vérifie le format ZIP. Il ne reprend pas un téléchargement partiel par HTTP Range. Les archives sont des entrées administrateur provenant des sources documentées, pas un service d’upload public.

### Résultat effectif

Essai 2 complet importé : 984 fichiers, quatre canaux, 3 936 fenêtres de 20 480 points. Premier et dernier horodatage et intervalles figurent dans l’inventaire. Le manifeste local `data/processed/nasa_features.manifest.json` garde les fichiers et leurs empreintes.

Un défaut constaté à la fin n’est pas une annotation du début exact de la panne, ni une étiquette positive à appliquer à tous les fichiers précédents. Aucun label de panne par fenêtre n’a été fabriqué.

## Paderborn

[Source KAt DataCenter](https://mb.uni-paderborn.de/en/kat/research/bearing-datacenter), [téléchargements](https://mb.uni-paderborn.de/en/kat/research/bearing-datacenter/data-sets-and-download). Licence confirmée sur la page institutionnelle : **CC BY-NC 4.0**, attribution requise ; contacter les auteurs pour usage commercial. Citer Lessmeier, Kimotho, Zimmer et Sextro, PHME 2016.

Les signaux comprennent vibrations/courants et des conditions auxiliaires. Ce lot n’a pas été téléchargé ici. Aucun classifieur, matrice de confusion ou score de généralisation Paderborn n’est annoncé. Une future implémentation doit importer les métadonnées de dommages, séparer les roulements/essais avant les fenêtres et conserver ce dataset distinct de NASA.

## AI4I 2020

[Source UCI](https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset), DOI 10.24432/C5HS5C, **CC BY 4.0**. Dataset **synthétique tabulaire**, pas des vibrations expérimentales. Téléchargé depuis UCI le 7 novembre 2026 : 10 000 lignes, SHA256 du CSV dc6630cd9b1f0f853922fad78a1b6436570d3f1ec863f1dd5c4340ac56bc8a8e. Le script scripts/train_ai4i.py entraîne et calibre le modèle complémentaire, sans fusion avec NASA. Voir ml-methodology.md pour les partitions et résultats.

Le modèle exclut les indicateurs de modes de panne des variables explicatives lorsqu’ils servent de cible. Une classification de panne présente ne constitue pas automatiquement une prévision à horizon futur.

## Données synthétiques de démonstration

Le générateur local et son détecteur possèdent la provenance industrial_simulation/synthetic. Ils n’alimentent ni les CSV NASA ni ses modèles. Les fixtures de tests sont isolées dans .cache/pytest et ne servent pas au dashboard.
