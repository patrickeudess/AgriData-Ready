# 🌾 AgriData Ready

**From Raw Data to FAIR & AI-Ready Data**

Application web interactive qui guide l'utilisateur étape par étape pour transformer des données brutes en données propres, documentées, conformes aux principes FAIR et prêtes pour l'intelligence artificielle.

## Fonctionnalités

1. **Importer** — Déposer un fichier CSV, Excel ou JSON
2. **Qualité** — Détection automatique des problèmes (valeurs manquantes, doublons, formats incohérents, valeurs anormales)
3. **Modifier** — Édition directe des données (cellules, colonnes, lignes, valeurs manquantes, doublons)
4. **Documenter les variables** — Description, type, unité, format, valeurs possibles, règles de validation
5. **Métadonnées** — Titre, auteur, licence, zone géographique, méthode de collecte, etc.
6. **Score FAIR** — Évaluation Findable, Accessible, Interoperable, Reusable
7. **Score AI Readiness** — Complétude, cohérence, documentation, qualité des variables, variable cible, structure, données sensibles
8. **Recommandations** — Actions concrètes hiérarchisées par priorité
9. **Exporter** — Dossier ZIP complet (données corrigées, métadonnées, dictionnaire, scores, rapport HTML)

## Installation

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Références

- Wilkinson et al. (2016) — FAIR Principles
- Wang & Strong (1996) — Data Quality
- Sambasivan et al. (2021) — Data Cascades in AI
- Andrew Ng — Data-Centric AI

---
*Mémoire DU Données — UCAD/EBAD — Patrick-Eudess Zatty ALLA — 2026*
