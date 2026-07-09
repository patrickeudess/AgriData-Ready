# AfriData Ready

**From Raw Data to FAIR & AI-Ready Data**

AfriData Ready est une application d'accompagnement pour transformer un fichier brut en jeu de données propre, documenté, conforme aux principes FAIR et plus prêt pour l'analyse ou l'intelligence artificielle.

## Interfaces

- `index.html` : application web statique, utilisable dans le navigateur et déployable sur GitHub Pages.
- `app.py` : prototype Streamlit pour une exécution Python locale.

## Fonctionnalités principales

1. Import de fichiers CSV, Excel ou JSON.
2. Diagnostic automatique de qualité : valeurs manquantes, doublons, colonnes vides, noms ambigus, formats incohérents et valeurs aberrantes.
3. Édition des données : cellules, colonnes, lignes, valeurs manquantes, doublons et valeurs proches.
4. Documentation des variables : description, type, unité, format, valeurs possibles, règles de validation et rôle pour l'IA.
5. Métadonnées du jeu de données : auteur, licence, zone géographique, méthode de collecte, citation, contact.
6. Évaluation FAIR et AI Readiness.
7. Score AQI interne, inspiré de référentiels de qualité et de gouvernance des données.
8. Recommandations priorisées et actions automatiques.
9. Export d'un data product : données corrigées, dictionnaire, métadonnées, scores, rapport et certificat.

## Utilisation rapide

### Version web statique

Ouvrir directement `index.html` dans un navigateur moderne, ou publier le dépôt via GitHub Pages.

Cette version fonctionne localement, sans serveur applicatif. Les projets sauvegardés sont stockés dans le navigateur via IndexedDB.

### Données d'exemple

Un jeu de données de test est fourni dans :

`samples/afridata_ready_exemple_qualite.xlsx`

Il contient volontairement des valeurs manquantes, doublons, valeurs aberrantes et variantes d'écriture pour tester le parcours qualité.

### Guide utilisateur

Consultez `GUIDE_UTILISATEUR.md` pour un parcours court en six étapes.

### Version Streamlit

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Déploiement

Le workflow GitHub Pages est défini dans `.github/workflows/pages.yml`. À chaque push sur `main`, le contenu du dépôt peut être publié comme site statique.

## Confidentialité et avertissement

- Les données traitées dans la version statique restent côté navigateur, sauf action explicite d'export ou de partage.
- Les fichiers importés peuvent contenir des valeurs sensibles : vérifiez les colonnes personnelles avant export.
- Les scores FAIR, AI Readiness et AQI sont des évaluations internes indicatives. Ils ne constituent pas une certification officielle.

## Licence

Le code est publié sous licence MIT. Voir `LICENSE`.

## Références

- Wilkinson et al. (2016) - FAIR Principles
- Wang & Strong (1996) - Data Quality
- ISO 8000 / ISO 25012 - Data Quality
- ISO 11179 - Metadata registries
- DataCite / Dublin Core - Metadata
- Sambasivan et al. (2021) - Data Cascades in AI
- Andrew Ng - Data-Centric AI

---

Mémoire DU Données - UCAD/EBAD - Patrick-Eudess Zatty ALLA - 2026
