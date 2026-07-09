# Guide utilisateur rapide

AfriData Ready accompagne la transformation d'un fichier brut en base plus propre, documentée et exploitable.

## 1. Importer un fichier

Ouvrez l'application, choisissez **Démarrage rapide** ou **Projet AfriData Ready**, puis importez un fichier CSV, Excel ou JSON.

Les données sont traitées localement dans le navigateur. Aucun fichier n'est envoyé sur un serveur par l'application statique.

## 2. Corriger la qualité des données

Dans **Qualité des données**, vérifiez :

- les valeurs manquantes ;
- les doublons ;
- les valeurs aberrantes ;
- les valeurs similaires dans une même colonne ;
- les formats incohérents.

Les boutons de correction modifient la base de travail et les exports utilisent cette version corrigée.

## 3. Documenter les variables

Renseignez les descriptions, types, unités, règles de validation et exemples. Cette étape améliore la compréhension du fichier et les scores de documentation.

## 4. Renseigner les métadonnées

Ajoutez le titre, l'auteur, l'organisation, la licence, le contact, la méthode de collecte et les mots-clés. Ces informations sont incluses dans les exports.

## 5. Vérifier les scores

Consultez les scores FAIR, AI Readiness, gouvernance et AQI. Ils sont indicatifs et servent à prioriser les améliorations.

## 6. Exporter le data product

Dans **Exporter**, téléchargez la base corrigée et les rapports associés : données, dictionnaire, métadonnées, qualité, AQI et journal des modifications.

## Données d'exemple

Un fichier d'exemple est disponible dans `samples/afridata_ready_exemple_qualite.xlsx`. Il contient volontairement des valeurs manquantes, doublons, valeurs aberrantes et variantes d'écriture pour tester l'application.

## Avertissement

AfriData Ready fournit une aide à la préparation et à l'évaluation des données. Les scores produits sont des évaluations internes et ne constituent pas une certification officielle.
