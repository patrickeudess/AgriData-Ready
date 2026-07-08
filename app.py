import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import re
import json
import zipfile
import base64
from datetime import datetime
from copy import deepcopy
from pathlib import Path

st.set_page_config(
    page_title="AfriData Ready",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
:root {
    --primary: #00345F;
    --primary-light: #00A6B2;
    --accent: #FF8A00;
    --danger: #C62828;
    --bg: #F6FAFB;
    --card-bg: #FFFFFF;
}
.main-header {
    background: linear-gradient(135deg, #00345F 0%, #006C82 58%, #00A6B2 100%);
    color: white; padding: 2rem; border-radius: 12px; text-align: center; margin-bottom: 1.5rem;
}
.main-header img {
    display: block; max-width: 520px; width: min(100%, 520px);
    margin: 0 auto 0.8rem; background: white; border-radius: 10px;
    padding: 0.55rem; box-shadow: 0 8px 22px rgba(0,0,0,0.18);
}
.main-header h1 { font-size: 2.2rem; margin: 0; font-weight: 800; }
.main-header .slogan { font-size: 1rem; opacity: 0.9; font-style: italic; margin-top: 0.3rem; }
.main-header .sub { font-size: 0.8rem; opacity: 0.7; margin-top: 0.5rem; }
.step-card {
    background: white; border-radius: 10px; padding: 1rem 1.2rem;
    border-left: 5px solid #00A6B2; box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 0.8rem;
}
.step-card.active { border-left-color: #FF8A00; background: #FFF4E5; }
.step-card.done { border-left-color: #00345F; background: #E8F7F8; }
.metric-card {
    background: white; border-radius: 10px; padding: 1rem; text-align: center;
    box-shadow: 0 2px 6px rgba(0,0,0,0.06); border-top: 4px solid #00A6B2;
}
.metric-val { font-size: 1.8rem; font-weight: 800; color: #00345F; }
.metric-label { font-size: 0.75rem; color: #666; text-transform: uppercase; }
.quality-issue {
    background: #FFF4E5; border-left: 4px solid #FF8A00;
    padding: 0.6rem 1rem; border-radius: 0 8px 8px 0; margin: 0.3rem 0; font-size: 0.88rem;
}
.quality-issue.critical { background: #FFEBEE; border-left-color: #C62828; }
.quality-issue.good { background: #E8F7F8; border-left-color: #00345F; }
.reco-card { padding: 0.6rem 1rem; border-radius: 0 8px 8px 0; margin: 0.3rem 0; font-size: 0.88rem; }
.reco-urgent { background: #FFEBEE; border-left: 4px solid #C62828; }
.reco-important { background: #FFF4E5; border-left: 4px solid #FF8A00; }
.reco-improve { background: #E8F7F8; border-left: 4px solid #00345F; }
.score-gauge { text-align: center; padding: 1rem; }
.fair-letter {
    display: inline-block; width: 60px; height: 60px; line-height: 60px;
    border-radius: 50%; font-size: 1.5rem; font-weight: 800; margin: 0.3rem;
    color: white; text-align: center;
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# SESSION STATE INITIALIZATION
# ═══════════════════════════════════════════════════════════════

def init_state():
    defaults = {
        "step": 1,
        "df_original": None,
        "df": None,
        "file_name": "",
        "sheets": {},
        "selected_sheet": "",
        "quality_report": None,
        "variable_docs": {},
        "metadata": {},
        "fair_score": None,
        "ai_score": None,
        "recommendations": [],
        "edit_history": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

STEPS = [
    "Importer les données",
    "Qualité des données",
    "Modifier les données",
    "Documenter les variables",
    "Métadonnées",
    "Score FAIR",
    "Score AI Readiness",
    "Recommandations",
    "Exporter",
]


# ═══════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════

def load_file(uploaded_file):
    name = uploaded_file.name.lower()
    sheets = {}
    if name.endswith(".csv"):
        for enc in ["utf-8", "latin-1", "cp1252"]:
            try:
                df = pd.read_csv(uploaded_file, encoding=enc)
                sheets["Données"] = df
                break
            except Exception:
                uploaded_file.seek(0)
    elif name.endswith((".xlsx", ".xls")):
        try:
            xl = pd.ExcelFile(uploaded_file)
            for s in xl.sheet_names:
                df = xl.parse(s)
                if not df.empty:
                    sheets[s] = df
        except Exception as e:
            st.error(f"Erreur : {e}")
    elif name.endswith(".json"):
        try:
            data = json.load(uploaded_file)
            if isinstance(data, list):
                sheets["Données"] = pd.DataFrame(data)
            elif isinstance(data, dict):
                sheets["Données"] = pd.DataFrame(data)
        except Exception as e:
            st.error(f"Erreur JSON : {e}")
    return sheets


# ═══════════════════════════════════════════════════════════════
# QUALITY ANALYSIS
# ═══════════════════════════════════════════════════════════════

def analyze_quality(df):
    issues = []
    n_rows, n_cols = df.shape
    n_cells = n_rows * n_cols

    # Missing values
    missing_total = df.isnull().sum().sum()
    missing_pct = (missing_total / n_cells * 100) if n_cells > 0 else 0
    if missing_total > 0:
        severity = "critical" if missing_pct > 20 else "warning"
        issues.append({"type": "missing", "severity": severity,
                       "message": f"{missing_total} valeurs manquantes ({missing_pct:.1f}%)",
                       "detail": df.isnull().sum()[df.isnull().sum() > 0].to_dict()})

    # Duplicates
    n_dup = df.duplicated().sum()
    if n_dup > 0:
        issues.append({"type": "duplicates", "severity": "warning",
                       "message": f"{n_dup} ligne(s) en doublon"})

    # Empty columns
    empty_cols = [c for c in df.columns if df[c].isnull().all()]
    if empty_cols:
        issues.append({"type": "empty_cols", "severity": "critical",
                       "message": f"{len(empty_cols)} colonne(s) entièrement vide(s)",
                       "detail": empty_cols})

    # Bad column names
    bad_names = []
    for c in df.columns:
        s = str(c)
        if s.startswith("Unnamed") or len(s) <= 2 or re.match(r'^col\d+$', s.lower()):
            bad_names.append(s)
    if bad_names:
        issues.append({"type": "bad_names", "severity": "warning",
                       "message": f"{len(bad_names)} nom(s) de colonne(s) mal défini(s)",
                       "detail": bad_names})

    # Inconsistent formats
    for col in df.columns:
        serie = df[col].dropna()
        if len(serie) == 0:
            continue
        if pd.api.types.is_object_dtype(serie):
            vals = serie.astype(str).str.strip().str.lower().unique()
            # Mixed binary
            bin_vals = {"oui","non","yes","no","0","1","true","false","vrai","faux","o","n"}
            if len(vals) <= 6 and len(set(vals) & bin_vals) >= 2:
                oui_forms = set(vals) & {"oui","yes","1","true","o","vrai"}
                non_forms = set(vals) & {"non","no","0","false","n","faux"}
                if len(oui_forms) > 1 or len(non_forms) > 1:
                    issues.append({"type": "inconsistent", "severity": "warning",
                                   "message": f"Colonne '{col}' : codage binaire incohérent ({', '.join(vals)})"})

    # Date format issues
    for col in df.columns:
        col_lower = str(col).lower()
        if any(k in col_lower for k in ["date","annee","année","mois","year","period"]):
            serie = df[col].dropna().astype(str)
            patterns_found = set()
            for v in serie.head(50):
                v = v.strip()
                if re.search(r'\d{2}/\d{2}/\d{4}', v): patterns_found.add("DD/MM/YYYY")
                if re.search(r'\d{4}-\d{2}-\d{2}', v): patterns_found.add("YYYY-MM-DD")
                if re.search(r'\d{2}-\d{2}-\d{4}', v): patterns_found.add("DD-MM-YYYY")
            if len(patterns_found) > 1:
                issues.append({"type": "date_format", "severity": "warning",
                               "message": f"Colonne '{col}' : formats de date mixtes ({', '.join(patterns_found)})"})

    # Outliers in numeric columns
    for col in df.select_dtypes(include=["number"]).columns:
        serie = df[col].dropna()
        if len(serie) < 10:
            continue
        q1, q3 = serie.quantile(0.25), serie.quantile(0.75)
        iqr = q3 - q1
        if iqr > 0:
            n_outliers = ((serie < q1 - 3*iqr) | (serie > q3 + 3*iqr)).sum()
            if n_outliers > 0:
                issues.append({"type": "outliers", "severity": "info",
                               "message": f"Colonne '{col}' : {n_outliers} valeur(s) potentiellement anormale(s)"})

    return {
        "n_rows": n_rows, "n_cols": n_cols, "n_cells": n_cells,
        "missing_total": int(missing_total), "missing_pct": round(missing_pct, 1),
        "n_duplicates": int(n_dup), "empty_cols": empty_cols,
        "issues": issues,
        "col_types": df.dtypes.astype(str).to_dict(),
        "missing_per_col": df.isnull().sum().to_dict(),
    }


# ═══════════════════════════════════════════════════════════════
# FAIR SCORE
# ═══════════════════════════════════════════════════════════════

def compute_fair_score(df, metadata, variable_docs):
    scores = {"F": 0, "A": 0, "I": 0, "R": 0}
    details = {"F": [], "A": [], "I": [], "R": []}
    max_scores = {"F": 25, "A": 25, "I": 25, "R": 25}

    # F - Findable (25 pts)
    if metadata.get("title"):
        scores["F"] += 5; details["F"].append(("ok", "Titre renseigné"))
    else:
        details["F"].append(("missing", "Titre manquant"))

    if metadata.get("description"):
        scores["F"] += 5; details["F"].append(("ok", "Description renseignée"))
    else:
        details["F"].append(("missing", "Description manquante"))

    if metadata.get("keywords"):
        scores["F"] += 5; details["F"].append(("ok", "Mots-clés renseignés"))
    else:
        details["F"].append(("missing", "Mots-clés manquants"))

    if metadata.get("author"):
        scores["F"] += 5; details["F"].append(("ok", "Auteur renseigné"))
    else:
        details["F"].append(("missing", "Auteur manquant"))

    if metadata.get("version"):
        scores["F"] += 5; details["F"].append(("ok", "Version renseignée"))
    else:
        details["F"].append(("missing", "Version manquante"))

    # A - Accessible (25 pts)
    if metadata.get("license"):
        scores["A"] += 8; details["A"].append(("ok", "Licence définie"))
    else:
        details["A"].append(("missing", "Licence manquante"))

    if metadata.get("access_conditions"):
        scores["A"] += 7; details["A"].append(("ok", "Conditions d'accès définies"))
    else:
        details["A"].append(("missing", "Conditions d'accès manquantes"))

    if metadata.get("contact"):
        scores["A"] += 5; details["A"].append(("ok", "Contact renseigné"))
    else:
        details["A"].append(("missing", "Contact manquant"))

    if metadata.get("citation"):
        scores["A"] += 5; details["A"].append(("ok", "Citation recommandée définie"))
    else:
        details["A"].append(("missing", "Citation recommandée manquante"))

    # I - Interoperable (25 pts)
    # Column names quality
    good_names = sum(1 for c in df.columns if len(str(c)) > 3 and not str(c).startswith("Unnamed"))
    name_ratio = good_names / len(df.columns) if len(df.columns) > 0 else 0
    name_score = int(name_ratio * 8)
    scores["I"] += name_score
    details["I"].append(("ok" if name_ratio > 0.8 else "missing", f"Noms de colonnes explicites : {good_names}/{len(df.columns)}"))

    # Data types coherent
    n_object = df.select_dtypes(include=["object"]).shape[1]
    type_ratio = 1 - (n_object / len(df.columns)) if len(df.columns) > 0 else 0
    type_score = int(type_ratio * 7)
    scores["I"] += type_score
    details["I"].append(("ok" if type_ratio > 0.5 else "missing", f"Colonnes avec types structurés : {len(df.columns) - n_object}/{len(df.columns)}"))

    # Standard format (CSV/Excel)
    scores["I"] += 5; details["I"].append(("ok", "Format standard (CSV/Excel)"))

    # Documentation of variables
    doc_ratio = len(variable_docs) / len(df.columns) if len(df.columns) > 0 else 0
    doc_score = int(doc_ratio * 5)
    scores["I"] += doc_score
    details["I"].append(("ok" if doc_ratio > 0.5 else "missing", f"Variables documentées : {len(variable_docs)}/{len(df.columns)}"))

    # R - Reusable (25 pts)
    if metadata.get("license"):
        scores["R"] += 6; details["R"].append(("ok", "Licence définie pour réutilisation"))
    else:
        details["R"].append(("missing", "Licence nécessaire pour la réutilisation"))

    if metadata.get("collection_method"):
        scores["R"] += 5; details["R"].append(("ok", "Méthode de collecte documentée"))
    else:
        details["R"].append(("missing", "Méthode de collecte manquante"))

    if metadata.get("geographic_area"):
        scores["R"] += 4; details["R"].append(("ok", "Zone géographique renseignée"))
    else:
        details["R"].append(("missing", "Zone géographique manquante"))

    missing_pct = df.isnull().sum().sum() / (df.shape[0] * df.shape[1]) * 100 if df.shape[0] * df.shape[1] > 0 else 100
    if missing_pct < 5:
        scores["R"] += 5; details["R"].append(("ok", f"Complétude élevée ({100-missing_pct:.1f}%)"))
    elif missing_pct < 20:
        scores["R"] += 3; details["R"].append(("partial", f"Complétude moyenne ({100-missing_pct:.1f}%)"))
    else:
        details["R"].append(("missing", f"Complétude faible ({100-missing_pct:.1f}%)"))

    doc_score_r = int(doc_ratio * 5)
    scores["R"] += doc_score_r
    details["R"].append(("ok" if doc_ratio > 0.5 else "missing", f"Dictionnaire de données : {len(variable_docs)}/{len(df.columns)} variables"))

    total = sum(scores.values())
    return {"scores": scores, "details": details, "total": total, "max": 100, "max_scores": max_scores}


# ═══════════════════════════════════════════════════════════════
# AI READINESS SCORE
# ═══════════════════════════════════════════════════════════════

def compute_ai_readiness(df, metadata, variable_docs):
    dims = {}
    details = {}

    # 1. Completeness (20 pts)
    missing_pct = df.isnull().sum().sum() / (df.shape[0] * df.shape[1]) * 100 if df.shape[0]*df.shape[1] > 0 else 100
    if missing_pct == 0: s = 20
    elif missing_pct <= 2: s = 18
    elif missing_pct <= 5: s = 15
    elif missing_pct <= 10: s = 12
    elif missing_pct <= 20: s = 8
    elif missing_pct <= 35: s = 4
    else: s = 0
    dims["Complétude"] = s
    details["Complétude"] = [f"Taux de valeurs manquantes : {missing_pct:.1f}%", f"Score : {s}/20"]

    # 2. Consistency (15 pts)
    n_dup = df.duplicated().sum()
    dup_pct = n_dup / df.shape[0] * 100 if df.shape[0] > 0 else 0
    s2 = 15
    if dup_pct > 20: s2 -= 8
    elif dup_pct > 5: s2 -= 4
    elif dup_pct > 0: s2 -= 2
    # Check type consistency
    for col in df.select_dtypes(include=["object"]).columns:
        try:
            conv = pd.to_numeric(df[col].dropna().astype(str).str.replace(r'[^\d.\-]', '', regex=True), errors='coerce')
            if conv.notna().mean() > 0.7:
                s2 -= 1
        except Exception:
            pass
    s2 = max(0, s2)
    dims["Cohérence"] = s2
    details["Cohérence"] = [f"Doublons : {n_dup} ({dup_pct:.1f}%)", f"Score : {s2}/15"]

    # 3. Documentation (15 pts)
    doc_ratio = len(variable_docs) / len(df.columns) if len(df.columns) > 0 else 0
    s3 = int(doc_ratio * 10)
    if metadata.get("description"): s3 += 3
    if metadata.get("collection_method"): s3 += 2
    s3 = min(15, s3)
    dims["Documentation"] = s3
    details["Documentation"] = [f"Variables documentées : {len(variable_docs)}/{len(df.columns)}", f"Score : {s3}/15"]

    # 4. Variable quality (15 pts)
    good_names = sum(1 for c in df.columns if len(str(c)) > 3 and not str(c).startswith("Unnamed"))
    name_ratio = good_names / len(df.columns) if len(df.columns) > 0 else 0
    n_numeric = df.select_dtypes(include=["number"]).shape[1]
    feat_ratio = n_numeric / len(df.columns) if len(df.columns) > 0 else 0
    s4 = int(name_ratio * 8) + int(feat_ratio * 7)
    s4 = min(15, s4)
    dims["Qualité des variables"] = s4
    details["Qualité des variables"] = [f"Noms explicites : {good_names}/{len(df.columns)}", f"Features numériques : {n_numeric}/{len(df.columns)}", f"Score : {s4}/15"]

    # 5. Target variable (10 pts)
    has_target = False
    target_keywords = ["target","cible","label","classe","class","output","yield","rendement","production"]
    for col in df.columns:
        if any(k in str(col).lower() for k in target_keywords):
            has_target = True
            break
    # Also check variable docs
    for col, doc in variable_docs.items():
        if doc.get("is_target"):
            has_target = True
            break
    s5 = 10 if has_target else 0
    dims["Variable cible"] = s5
    details["Variable cible"] = [f"Variable cible identifiée : {'Oui' if has_target else 'Non'}", f"Score : {s5}/10"]

    # 6. Structure (15 pts)
    s6 = 15
    empty_cols = sum(1 for c in df.columns if df[c].isnull().all())
    empty_rows = df.isnull().all(axis=1).sum()
    if empty_cols > 0: s6 -= 5
    if empty_rows > 0: s6 -= 3
    if df.shape[0] < 30: s6 -= 4
    elif df.shape[0] < 100: s6 -= 2
    s6 = max(0, s6)
    dims["Structure"] = s6
    details["Structure"] = [f"Colonnes vides : {empty_cols}, Lignes vides : {empty_rows}", f"Nombre d'observations : {df.shape[0]}", f"Score : {s6}/15"]

    # 7. Sensitive data risks (10 pts)
    s7 = 10
    sensitive_keywords = ["nom","name","prenom","surname","telephone","phone","email","adresse","address","ssn","cin","id_person"]
    sensitive_found = [c for c in df.columns if any(k in str(c).lower() for k in sensitive_keywords)]
    if sensitive_found:
        s7 -= min(10, len(sensitive_found) * 3)
    s7 = max(0, s7)
    dims["Données sensibles"] = s7
    details["Données sensibles"] = [f"Colonnes potentiellement sensibles : {', '.join(sensitive_found) if sensitive_found else 'Aucune'}", f"Score : {s7}/10"]

    total = sum(dims.values())
    max_total = 100
    if total <= 39: level = ("Faible", "#C62828")
    elif total <= 69: level = ("Moyen", "#FF6F00")
    else: level = ("Élevé", "#1B5E20")

    return {"dims": dims, "details": details, "total": total, "max": max_total, "level": level,
            "max_dims": {"Complétude": 20, "Cohérence": 15, "Documentation": 15,
                         "Qualité des variables": 15, "Variable cible": 10, "Structure": 15, "Données sensibles": 10}}


# ═══════════════════════════════════════════════════════════════
# RECOMMENDATIONS
# ═══════════════════════════════════════════════════════════════

def generate_recommendations(df, metadata, variable_docs, quality_report, fair_score, ai_score):
    recos = []

    missing_pct = quality_report["missing_pct"]
    if missing_pct > 20:
        recos.append(("urgent", "Compléter les données", f"Taux de valeurs manquantes élevé ({missing_pct}%). Appliquer une stratégie d'imputation ou documenter les raisons."))
    elif missing_pct > 5:
        recos.append(("important", "Réduire les valeurs manquantes", f"{missing_pct}% de valeurs manquantes. Vérifier les colonnes critiques."))

    if quality_report["n_duplicates"] > 0:
        recos.append(("important", "Supprimer les doublons", f"{quality_report['n_duplicates']} ligne(s) en doublon détectée(s)."))

    if quality_report["empty_cols"]:
        recos.append(("urgent", "Supprimer les colonnes vides", f"{len(quality_report['empty_cols'])} colonne(s) entièrement vide(s) : {', '.join(quality_report['empty_cols'][:5])}"))

    # Metadata
    missing_meta = []
    for field in ["title","author","description","license","keywords","contact"]:
        if not metadata.get(field):
            missing_meta.append(field)
    if missing_meta:
        recos.append(("urgent" if len(missing_meta) > 3 else "important", "Compléter les métadonnées", f"Champs manquants : {', '.join(missing_meta)}"))

    # Variable documentation
    n_undoc = len(df.columns) - len(variable_docs)
    if n_undoc > 0:
        recos.append(("important", "Documenter les variables", f"{n_undoc} variable(s) non documentée(s) sur {len(df.columns)}."))

    # License
    if not metadata.get("license"):
        recos.append(("urgent", "Ajouter une licence", "Aucune licence définie. CC-BY 4.0 est recommandée pour les données ouvertes."))

    # Column names
    bad = sum(1 for c in df.columns if len(str(c)) <= 2 or str(c).startswith("Unnamed"))
    if bad > 0:
        recos.append(("important", "Améliorer les noms de colonnes", f"{bad} colonne(s) avec des noms peu explicites."))

    # Sensitive data
    sensitive_keywords = ["nom","name","prenom","telephone","phone","email","adresse","address"]
    sensitive = [c for c in df.columns if any(k in str(c).lower() for k in sensitive_keywords)]
    if sensitive:
        recos.append(("important", "Anonymiser les données sensibles", f"Colonnes potentiellement sensibles : {', '.join(sensitive[:5])}"))

    # FAIR
    recos.append(("improve", "Déposer sur un entrepôt", "Déposer le dataset sur Zenodo, Dataverse ou DataSuds pour obtenir un DOI pérenne (principe FAIR)."))

    order = {"urgent": 0, "important": 1, "improve": 2}
    recos.sort(key=lambda x: order.get(x[0], 3))
    return recos


# ═══════════════════════════════════════════════════════════════
# CHARTS
# ═══════════════════════════════════════════════════════════════

def plot_radar(labels, values, max_values, title=""):
    n = len(labels)
    angles = np.linspace(0, 2*np.pi, n, endpoint=False).tolist()
    angles += angles[:1]
    norm = [v/m if m > 0 else 0 for v, m in zip(values, max_values)]
    norm += norm[:1]

    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
    ax.set_facecolor("#FAFAFA")
    fig.patch.set_facecolor("#FAFAFA")
    for r in [0.2, 0.4, 0.6, 0.8, 1.0]:
        ax.plot(angles, [r]*(n+1), color="#DDD", linewidth=0.5, linestyle="--")
    ax.fill(angles, norm, alpha=0.25, color="#4CAF50")
    ax.plot(angles, norm, color="#1B5E20", linewidth=2)
    for a, v in zip(angles[:-1], norm[:-1]):
        ax.plot(a, v, "o", color="#1B5E20", markersize=7)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, size=8, color="#1B5E20", fontweight="bold")
    ax.set_yticks([])
    ax.set_ylim(0, 1)
    if title:
        ax.set_title(title, size=11, color="#1B5E20", fontweight="bold", pad=15)
    plt.tight_layout()
    return fig


def plot_gauge(score, max_score=100):
    fig, ax = plt.subplots(figsize=(4, 2.5))
    fig.patch.set_facecolor("#FAFAFA")
    ax.set_facecolor("#FAFAFA")
    ax.set_xlim(0, 10); ax.set_ylim(0, 5.5); ax.axis("off")
    theta = np.linspace(np.pi, 0, 200)
    ax.fill_between(5 + 4*np.cos(theta), 4*np.sin(theta), 0, color="#E0E0E0", zorder=1)
    ratio = score / max_score
    theta_s = np.linspace(np.pi, np.pi - ratio*np.pi, 200)
    col = "#C62828" if score <= 39 else "#FF6F00" if score <= 69 else "#1B5E20"
    ax.fill_between(5 + 4*np.cos(theta_s), 4*np.sin(theta_s), 0, color=col, alpha=0.85, zorder=2)
    circle = plt.Circle((5, 0), 2.5, color="#FAFAFA", zorder=3)
    ax.add_patch(circle)
    ax.text(5, 0.8, f"{score}", ha="center", va="center", fontsize=26, fontweight="bold", color="#1B5E20", zorder=4)
    ax.text(5, 0.1, f"/{max_score}", ha="center", va="center", fontsize=10, color="#666", zorder=4)
    plt.tight_layout()
    return fig


# ═══════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════

def generate_html_report(df, metadata, variable_docs, quality_report, fair_score, ai_score, recommendations, edit_history):
    meta_rows = ""
    for k, v in metadata.items():
        if v:
            meta_rows += f"<tr><td><strong>{k}</strong></td><td>{v}</td></tr>\n"

    var_rows = ""
    for col in df.columns:
        doc = variable_docs.get(col, {})
        var_rows += f"""<tr>
            <td>{col}</td><td>{str(df[col].dtype)}</td>
            <td>{doc.get('description','')}</td><td>{doc.get('unit','')}</td>
            <td>{doc.get('format','')}</td><td>{doc.get('example','')}</td>
        </tr>"""

    fair_rows = ""
    for letter in ["F","A","I","R"]:
        s = fair_score["scores"][letter]
        m = fair_score["max_scores"][letter]
        color = "#C62828" if s/m < 0.4 else "#FF6F00" if s/m < 0.7 else "#1B5E20"
        fair_rows += f'<tr><td style="font-weight:bold">{letter}</td><td style="color:{color};font-weight:bold">{s}/{m}</td></tr>\n'

    ai_rows = ""
    for dim, s in ai_score["dims"].items():
        m = ai_score["max_dims"][dim]
        color = "#C62828" if s/m < 0.4 else "#FF6F00" if s/m < 0.7 else "#1B5E20"
        ai_rows += f'<tr><td>{dim}</td><td style="color:{color};font-weight:bold">{s}/{m}</td></tr>\n'

    issue_rows = ""
    for issue in quality_report["issues"]:
        issue_rows += f"<tr><td>{issue['severity']}</td><td>{issue['message']}</td></tr>\n"

    reco_rows = ""
    for prio, title, desc in recommendations:
        color = "#C62828" if prio == "urgent" else "#FF6F00" if prio == "important" else "#1B5E20"
        reco_rows += f'<tr><td style="color:{color};font-weight:bold">{prio.upper()}</td><td><strong>{title}</strong><br>{desc}</td></tr>\n'

    history_rows = ""
    for h in edit_history:
        history_rows += f"<tr><td>{h.get('time','')}</td><td>{h.get('action','')}</td><td>{h.get('detail','')}</td></tr>\n"

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><title>Rapport AfriData Ready</title>
<style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; max-width: 1000px; margin: 0 auto; padding: 2rem; color: #333; }}
h1 {{ color: #1B5E20; border-bottom: 3px solid #4CAF50; padding-bottom: 0.5rem; }}
h2 {{ color: #2E7D32; margin-top: 2rem; }}
table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
th {{ background: #1B5E20; color: white; padding: 0.6rem; text-align: left; }}
td {{ padding: 0.5rem; border-bottom: 1px solid #E0E0E0; }}
tr:nth-child(even) {{ background: #F5F5F5; }}
.score-box {{ display: inline-block; padding: 1rem 2rem; border-radius: 10px; text-align: center; margin: 0.5rem; }}
.header {{ background: linear-gradient(135deg, #1B5E20, #43A047); color: white; padding: 2rem; border-radius: 12px; text-align: center; }}
.header h1 {{ color: white; border: none; }}
</style></head>
<body>
<div class="header">
<h1>AfriData Ready - Rapport Final</h1>
<p><em>From Raw Data to FAIR & AI-Ready Data</em></p>
<p>Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>
</div>

<h2>1. Métadonnées du jeu de données</h2>
<table><tr><th>Champ</th><th>Valeur</th></tr>{meta_rows}</table>

<h2>2. Aperçu des données</h2>
<p><strong>Lignes :</strong> {df.shape[0]} | <strong>Colonnes :</strong> {df.shape[1]}</p>

<h2>3. Rapport qualité</h2>
<p>Valeurs manquantes : {quality_report['missing_total']} ({quality_report['missing_pct']}%) | Doublons : {quality_report['n_duplicates']}</p>
<table><tr><th>Sévérité</th><th>Problème</th></tr>{issue_rows}</table>

<h2>4. Dictionnaire de données</h2>
<table><tr><th>Variable</th><th>Type</th><th>Description</th><th>Unité</th><th>Format</th><th>Exemple</th></tr>{var_rows}</table>

<h2>5. Score FAIR</h2>
<div class="score-box" style="background:#E8F5E9;font-size:2rem;font-weight:800;color:#1B5E20">{fair_score['total']}/100</div>
<table><tr><th>Principe</th><th>Score</th></tr>{fair_rows}</table>

<h2>6. Score AI Readiness</h2>
<div class="score-box" style="background:#E8F5E9;font-size:2rem;font-weight:800;color:#1B5E20">{ai_score['total']}/100</div>
<table><tr><th>Dimension</th><th>Score</th></tr>{ai_rows}</table>

<h2>7. Recommandations</h2>
<table><tr><th>Priorité</th><th>Recommandation</th></tr>{reco_rows}</table>

<h2>8. Historique des modifications</h2>
<table><tr><th>Date</th><th>Action</th><th>Détail</th></tr>{history_rows}</table>

<hr><p style="text-align:center;color:#888;font-size:0.8rem">AfriData Ready &mdash; From Raw Data to FAIR & AI-Ready Data</p>
</body></html>"""
    return html


def create_export_zip(df, metadata, variable_docs, quality_report, fair_score, ai_score, recommendations, edit_history):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Corrected data CSV
        csv_buf = io.StringIO()
        df.to_csv(csv_buf, index=False, encoding="utf-8")
        zf.writestr("donnees_corrigees.csv", csv_buf.getvalue())

        # Metadata JSON
        zf.writestr("metadonnees.json", json.dumps(metadata, ensure_ascii=False, indent=2))

        # Data dictionary JSON
        dict_data = {}
        for col in df.columns:
            dict_data[col] = variable_docs.get(col, {"description": "", "type": str(df[col].dtype)})
            dict_data[col]["type_detected"] = str(df[col].dtype)
        zf.writestr("dictionnaire_donnees.json", json.dumps(dict_data, ensure_ascii=False, indent=2))

        # Data dictionary CSV
        dict_rows = []
        for col in df.columns:
            doc = variable_docs.get(col, {})
            dict_rows.append({
                "variable": col, "type": str(df[col].dtype),
                "description": doc.get("description", ""), "unit": doc.get("unit", ""),
                "format": doc.get("format", ""), "values": doc.get("values", ""),
                "example": doc.get("example", ""), "validation": doc.get("validation", ""),
            })
        dict_df = pd.DataFrame(dict_rows)
        dict_csv = io.StringIO()
        dict_df.to_csv(dict_csv, index=False)
        zf.writestr("dictionnaire_donnees.csv", dict_csv.getvalue())

        # Quality report JSON
        qr = {k: v for k, v in quality_report.items() if k != "issues"}
        qr["issues"] = [{"type": i["type"], "severity": i["severity"], "message": i["message"]} for i in quality_report["issues"]]
        zf.writestr("rapport_qualite.json", json.dumps(qr, ensure_ascii=False, indent=2))

        # FAIR score JSON
        zf.writestr("score_fair.json", json.dumps({"total": fair_score["total"], "scores": fair_score["scores"],
            "details": {k: [(s, m) for s, m in v] for k, v in fair_score["details"].items()}}, ensure_ascii=False, indent=2))

        # AI readiness JSON
        zf.writestr("score_ai_readiness.json", json.dumps({"total": ai_score["total"], "dims": ai_score["dims"],
            "level": ai_score["level"][0], "details": ai_score["details"]}, ensure_ascii=False, indent=2))

        # Recommendations JSON
        reco_data = [{"priority": p, "title": t, "description": d} for p, t, d in recommendations]
        zf.writestr("recommandations.json", json.dumps(reco_data, ensure_ascii=False, indent=2))

        # Edit history JSON
        zf.writestr("historique_modifications.json", json.dumps(edit_history, ensure_ascii=False, indent=2))

        # HTML report
        html = generate_html_report(df, metadata, variable_docs, quality_report, fair_score, ai_score, recommendations, edit_history)
        zf.writestr("rapport_final.html", html)

    buf.seek(0)
    return buf


# ═══════════════════════════════════════════════════════════════
# UI: SIDEBAR
# ═══════════════════════════════════════════════════════════════

def render_sidebar():
    with st.sidebar:
        st.markdown("## Navigation")
        for i, step_name in enumerate(STEPS, 1):
            if i == st.session_state.step:
                css = "active"
                icon = "▶"
            elif st.session_state.df is not None and i < st.session_state.step:
                css = "done"
                icon = "✓"
            else:
                css = ""
                icon = f"{i}"
            if st.button(f"{icon}  {step_name}", key=f"nav_{i}", use_container_width=True,
                         disabled=(st.session_state.df is None and i > 1)):
                st.session_state.step = i
                st.rerun()

        st.markdown("---")
        if st.session_state.df is not None:
            st.markdown(f"**Fichier :** {st.session_state.file_name}")
            st.markdown(f"**Lignes :** {st.session_state.df.shape[0]}")
            st.markdown(f"**Colonnes :** {st.session_state.df.shape[1]}")
            st.markdown(f"**Modifications :** {len(st.session_state.edit_history)}")


# ═══════════════════════════════════════════════════════════════
# STEP 1: IMPORT
# ═══════════════════════════════════════════════════════════════

def step_import():
    st.markdown("### Étape 1 : Importer les données")
    st.markdown("Déposez votre fichier de données brut. L'application affichera un aperçu immédiat.")

    uploaded = st.file_uploader("Choisir un fichier", type=["csv", "xlsx", "xls", "json"],
                                help="Formats acceptés : CSV, Excel (.xlsx, .xls), JSON")

    if uploaded:
        sheets = load_file(uploaded)
        if sheets:
            st.session_state.sheets = sheets
            st.session_state.file_name = uploaded.name

            sheet_names = list(sheets.keys())
            if len(sheet_names) > 1:
                selected = st.selectbox("Sélectionner la feuille à analyser :", sheet_names)
            else:
                selected = sheet_names[0]
            st.session_state.selected_sheet = selected
            df = sheets[selected]
            st.session_state.df = df.copy()
            st.session_state.df_original = df.copy()

            st.success(f"Fichier chargé : **{uploaded.name}**")

            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f'<div class="metric-card"><div class="metric-val">{df.shape[0]}</div><div class="metric-label">Lignes</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-card"><div class="metric-val">{df.shape[1]}</div><div class="metric-label">Colonnes</div></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-card"><div class="metric-val">{df.isnull().sum().sum()}</div><div class="metric-label">Valeurs manquantes</div></div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="metric-card"><div class="metric-val">{df.duplicated().sum()}</div><div class="metric-label">Doublons</div></div>', unsafe_allow_html=True)

            st.markdown("**Aperçu des données :**")
            st.dataframe(df.head(10), use_container_width=True)

            st.markdown("**Types des colonnes :**")
            type_df = pd.DataFrame({"Colonne": df.columns, "Type": df.dtypes.astype(str).values,
                                     "Non-null": df.notnull().sum().values,
                                     "Manquants (%)": (df.isnull().mean()*100).round(1).values})
            st.dataframe(type_df, use_container_width=True, hide_index=True)

            if st.button("Passer à l'analyse qualité →", type="primary"):
                st.session_state.step = 2
                st.rerun()


# ═══════════════════════════════════════════════════════════════
# STEP 2: QUALITY
# ═══════════════════════════════════════════════════════════════

def step_quality():
    st.markdown("### Étape 2 : Problèmes de qualité détectés")
    df = st.session_state.df
    if df is None:
        st.warning("Veuillez d'abord importer un fichier.")
        return

    report = analyze_quality(df)
    st.session_state.quality_report = report

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Valeurs manquantes", f"{report['missing_total']} ({report['missing_pct']}%)")
    c2.metric("Doublons", report['n_duplicates'])
    c3.metric("Colonnes vides", len(report['empty_cols']))
    c4.metric("Problèmes détectés", len(report['issues']))

    if not report["issues"]:
        st.markdown('<div class="quality-issue good"><strong>Aucun problème majeur détecté.</strong></div>', unsafe_allow_html=True)
    else:
        for issue in report["issues"]:
            css = "critical" if issue["severity"] == "critical" else ""
            icon = "🔴" if issue["severity"] == "critical" else "🟡" if issue["severity"] == "warning" else "ℹ️"
            st.markdown(f'<div class="quality-issue {css}"><strong>{icon} {issue["message"]}</strong></div>', unsafe_allow_html=True)
            if "detail" in issue:
                if isinstance(issue["detail"], dict):
                    with st.expander("Voir le détail"):
                        for k, v in list(issue["detail"].items())[:10]:
                            st.write(f"- `{k}` : {v}")
                elif isinstance(issue["detail"], list):
                    with st.expander("Voir le détail"):
                        st.write(", ".join(str(x) for x in issue["detail"][:10]))

    # Missing values heatmap
    if report["missing_total"] > 0:
        st.markdown("**Valeurs manquantes par colonne :**")
        miss_data = df.isnull().sum()
        miss_data = miss_data[miss_data > 0].sort_values(ascending=True)
        if len(miss_data) > 0:
            fig, ax = plt.subplots(figsize=(8, max(2, len(miss_data)*0.4)))
            fig.patch.set_facecolor("#FAFAFA")
            colors = ["#C62828" if v/df.shape[0] > 0.5 else "#FF6F00" if v/df.shape[0] > 0.1 else "#4CAF50" for v in miss_data.values]
            ax.barh(miss_data.index, miss_data.values, color=colors)
            for i, (v, name) in enumerate(zip(miss_data.values, miss_data.index)):
                ax.text(v + 0.5, i, f"{v} ({v/df.shape[0]*100:.0f}%)", va='center', fontsize=8)
            ax.set_xlabel("Nombre de valeurs manquantes")
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            plt.tight_layout()
            st.pyplot(fig)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Retour", key="q_back"):
            st.session_state.step = 1; st.rerun()
    with col2:
        if st.button("Modifier les données →", type="primary", key="q_next"):
            st.session_state.step = 3; st.rerun()


# ═══════════════════════════════════════════════════════════════
# STEP 3: EDIT DATA
# ═══════════════════════════════════════════════════════════════

def step_edit():
    st.markdown("### Étape 3 : Modifier les données")
    df = st.session_state.df
    if df is None:
        st.warning("Veuillez d'abord importer un fichier.")
        return

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Éditer les cellules", "Colonnes", "Lignes", "Valeurs manquantes", "Doublons"])

    with tab1:
        st.markdown("Modifiez directement les valeurs dans le tableau ci-dessous :")
        edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="data_editor")
        if st.button("Appliquer les modifications", key="apply_edit"):
            changes = (edited_df != df).sum().sum() if edited_df.shape == df.shape else -1
            st.session_state.df = edited_df
            st.session_state.edit_history.append({"time": datetime.now().strftime("%H:%M:%S"), "action": "Édition directe", "detail": f"Modifications appliquées"})
            st.success("Modifications appliquées.")
            st.rerun()

    with tab2:
        st.markdown("**Renommer une colonne :**")
        col_to_rename = st.selectbox("Colonne à renommer :", df.columns, key="rename_col")
        new_name = st.text_input("Nouveau nom :", key="new_col_name")
        if st.button("Renommer", key="btn_rename"):
            if new_name and new_name != col_to_rename:
                st.session_state.df = st.session_state.df.rename(columns={col_to_rename: new_name})
                st.session_state.edit_history.append({"time": datetime.now().strftime("%H:%M:%S"), "action": "Renommer colonne", "detail": f"{col_to_rename} → {new_name}"})
                st.success(f"Colonne renommée : {col_to_rename} → {new_name}")
                st.rerun()

        st.markdown("**Supprimer une colonne :**")
        cols_to_delete = st.multiselect("Colonnes à supprimer :", df.columns, key="del_cols")
        if st.button("Supprimer", key="btn_del_col") and cols_to_delete:
            st.session_state.df = st.session_state.df.drop(columns=cols_to_delete)
            st.session_state.edit_history.append({"time": datetime.now().strftime("%H:%M:%S"), "action": "Supprimer colonnes", "detail": ", ".join(cols_to_delete)})
            st.success(f"Colonnes supprimées : {', '.join(cols_to_delete)}")
            st.rerun()

        st.markdown("**Standardiser les noms de colonnes :**")
        preview = {c: re.sub(r'[^a-z0-9]+', '_', str(c).lower().strip()).strip('_') for c in df.columns}
        st.json(preview)
        if st.button("Appliquer la standardisation", key="btn_std"):
            st.session_state.df = st.session_state.df.rename(columns=preview)
            st.session_state.edit_history.append({"time": datetime.now().strftime("%H:%M:%S"), "action": "Standardiser noms", "detail": f"{len(preview)} colonnes"})
            st.success("Noms standardisés.")
            st.rerun()

    with tab3:
        st.markdown("**Supprimer des lignes :**")
        row_indices = st.text_input("Indices des lignes à supprimer (séparés par des virgules) :", key="del_rows")
        if st.button("Supprimer les lignes", key="btn_del_rows") and row_indices:
            try:
                indices = [int(i.strip()) for i in row_indices.split(",")]
                valid = [i for i in indices if i in st.session_state.df.index]
                st.session_state.df = st.session_state.df.drop(index=valid).reset_index(drop=True)
                st.session_state.edit_history.append({"time": datetime.now().strftime("%H:%M:%S"), "action": "Supprimer lignes", "detail": f"Lignes {valid}"})
                st.success(f"{len(valid)} ligne(s) supprimée(s).")
                st.rerun()
            except ValueError:
                st.error("Format invalide. Utilisez des nombres séparés par des virgules.")

        st.markdown("**Supprimer les lignes entièrement vides :**")
        n_empty = df.isnull().all(axis=1).sum()
        st.write(f"{n_empty} ligne(s) entièrement vide(s)")
        if n_empty > 0 and st.button("Supprimer les lignes vides", key="btn_empty_rows"):
            st.session_state.df = st.session_state.df.dropna(how='all').reset_index(drop=True)
            st.session_state.edit_history.append({"time": datetime.now().strftime("%H:%M:%S"), "action": "Supprimer lignes vides", "detail": f"{n_empty} lignes"})
            st.success(f"{n_empty} ligne(s) vide(s) supprimée(s).")
            st.rerun()

    with tab4:
        st.markdown("**Traitement des valeurs manquantes :**")
        cols_with_missing = [c for c in df.columns if df[c].isnull().any()]
        if not cols_with_missing:
            st.success("Aucune valeur manquante.")
        else:
            col_fill = st.selectbox("Colonne :", cols_with_missing, key="fill_col")
            method = st.selectbox("Méthode :", ["Moyenne", "Médiane", "Mode", "Valeur personnalisée", "Supprimer les lignes"], key="fill_method")
            custom_val = None
            if method == "Valeur personnalisée":
                custom_val = st.text_input("Valeur :", key="custom_fill")
            if st.button("Appliquer", key="btn_fill"):
                if method == "Moyenne" and pd.api.types.is_numeric_dtype(df[col_fill]):
                    st.session_state.df[col_fill] = st.session_state.df[col_fill].fillna(df[col_fill].mean())
                elif method == "Médiane" and pd.api.types.is_numeric_dtype(df[col_fill]):
                    st.session_state.df[col_fill] = st.session_state.df[col_fill].fillna(df[col_fill].median())
                elif method == "Mode":
                    mode_val = df[col_fill].mode()
                    if len(mode_val) > 0:
                        st.session_state.df[col_fill] = st.session_state.df[col_fill].fillna(mode_val.iloc[0])
                elif method == "Valeur personnalisée" and custom_val is not None:
                    st.session_state.df[col_fill] = st.session_state.df[col_fill].fillna(custom_val)
                elif method == "Supprimer les lignes":
                    st.session_state.df = st.session_state.df.dropna(subset=[col_fill]).reset_index(drop=True)
                st.session_state.edit_history.append({"time": datetime.now().strftime("%H:%M:%S"), "action": f"Valeurs manquantes ({method})", "detail": col_fill})
                st.success(f"Valeurs manquantes traitées pour '{col_fill}'.")
                st.rerun()

    with tab5:
        n_dup = df.duplicated().sum()
        st.write(f"**{n_dup}** ligne(s) en doublon")
        if n_dup > 0:
            st.dataframe(df[df.duplicated(keep='first')].head(20), use_container_width=True)
            if st.button("Supprimer les doublons", key="btn_dup"):
                st.session_state.df = st.session_state.df.drop_duplicates().reset_index(drop=True)
                st.session_state.edit_history.append({"time": datetime.now().strftime("%H:%M:%S"), "action": "Supprimer doublons", "detail": f"{n_dup} doublons"})
                st.success(f"{n_dup} doublon(s) supprimé(s).")
                st.rerun()

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Retour", key="e_back"):
            st.session_state.step = 2; st.rerun()
    with col2:
        if st.button("Documenter les variables →", type="primary", key="e_next"):
            st.session_state.step = 4; st.rerun()


# ═══════════════════════════════════════════════════════════════
# STEP 4: VARIABLE DOCUMENTATION
# ═══════════════════════════════════════════════════════════════

def step_variable_docs():
    st.markdown("### Étape 4 : Documenter les variables")
    df = st.session_state.df
    if df is None:
        st.warning("Veuillez d'abord importer un fichier.")
        return

    st.markdown("Pour chaque variable, renseignez sa description, son type, son unité et d'autres informations utiles.")

    n_documented = len(st.session_state.variable_docs)
    n_total = len(df.columns)
    st.progress(n_documented / n_total if n_total > 0 else 0, text=f"{n_documented}/{n_total} variables documentées")

    selected_col = st.selectbox("Sélectionner une variable :", df.columns, key="doc_col_select")

    existing = st.session_state.variable_docs.get(selected_col, {})

    with st.expander(f"Aperçu de '{selected_col}'", expanded=True):
        serie = df[selected_col]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Type détecté", str(serie.dtype))
        c2.metric("Non-null", int(serie.notnull().sum()))
        c3.metric("Uniques", int(serie.nunique()))
        c4.metric("Manquants", int(serie.isnull().sum()))
        if pd.api.types.is_numeric_dtype(serie):
            st.write(serie.describe().round(2))
        else:
            st.write(f"Valeurs fréquentes : {', '.join(str(v) for v in serie.value_counts().head(5).index)}")

    with st.form(f"doc_form_{selected_col}"):
        description = st.text_area("Description de la variable :", value=existing.get("description", ""), key=f"desc_{selected_col}")
        c1, c2 = st.columns(2)
        with c1:
            data_type = st.selectbox("Type de donnée :", ["Numérique continu", "Numérique discret", "Catégoriel nominal", "Catégoriel ordinal", "Date/Temps", "Texte libre", "Binaire", "Identifiant"],
                                     index=["Numérique continu", "Numérique discret", "Catégoriel nominal", "Catégoriel ordinal", "Date/Temps", "Texte libre", "Binaire", "Identifiant"].index(existing.get("data_type", "Numérique continu")) if existing.get("data_type") in ["Numérique continu", "Numérique discret", "Catégoriel nominal", "Catégoriel ordinal", "Date/Temps", "Texte libre", "Binaire", "Identifiant"] else 0,
                                     key=f"dtype_{selected_col}")
            unit = st.text_input("Unité de mesure :", value=existing.get("unit", ""), key=f"unit_{selected_col}")
            fmt = st.text_input("Format attendu :", value=existing.get("format", ""), placeholder="ex: YYYY-MM-DD, nombre entier...", key=f"fmt_{selected_col}")
        with c2:
            values = st.text_input("Valeurs possibles :", value=existing.get("values", ""), placeholder="ex: 0-100, Oui/Non...", key=f"vals_{selected_col}")
            validation = st.text_input("Règle de validation :", value=existing.get("validation", ""), placeholder="ex: > 0, non vide...", key=f"valid_{selected_col}")
            example = st.text_input("Exemple de valeur :", value=existing.get("example", ""), key=f"ex_{selected_col}")

        utility = st.text_input("Utilité pour l'analyse / l'IA :", value=existing.get("utility", ""), key=f"util_{selected_col}")
        is_target = st.checkbox("Variable cible (target) pour l'IA", value=existing.get("is_target", False), key=f"target_{selected_col}")

        if st.form_submit_button("Enregistrer la documentation", type="primary"):
            st.session_state.variable_docs[selected_col] = {
                "description": description, "data_type": data_type, "unit": unit,
                "format": fmt, "values": values, "validation": validation,
                "example": example, "utility": utility, "is_target": is_target,
            }
            st.success(f"Documentation enregistrée pour '{selected_col}'.")
            st.rerun()

    # Summary table
    if st.session_state.variable_docs:
        st.markdown("**Résumé de la documentation :**")
        rows = []
        for col in df.columns:
            doc = st.session_state.variable_docs.get(col, {})
            rows.append({"Variable": col, "Description": doc.get("description", "❌"), "Type": doc.get("data_type", "—"), "Unité": doc.get("unit", "—")})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Retour", key="d_back"):
            st.session_state.step = 3; st.rerun()
    with col2:
        if st.button("Métadonnées →", type="primary", key="d_next"):
            st.session_state.step = 5; st.rerun()


# ═══════════════════════════════════════════════════════════════
# STEP 5: METADATA
# ═══════════════════════════════════════════════════════════════

def step_metadata():
    st.markdown("### Étape 5 : Métadonnées du jeu de données")
    st.markdown("Renseignez les informations générales sur votre jeu de données.")

    meta = st.session_state.metadata

    with st.form("metadata_form"):
        c1, c2 = st.columns(2)
        with c1:
            title = st.text_input("Titre du jeu de données :", value=meta.get("title", ""))
            author = st.text_input("Auteur(s) :", value=meta.get("author", ""))
            organization = st.text_input("Organisation :", value=meta.get("organization", ""))
            country = st.text_input("Pays :", value=meta.get("country", ""))
            geographic_area = st.text_input("Zone géographique :", value=meta.get("geographic_area", ""))
            collection_period = st.text_input("Période de collecte :", value=meta.get("collection_period", ""), placeholder="ex: Janvier - Mars 2024")
            version = st.text_input("Version :", value=meta.get("version", ""), placeholder="ex: 1.0")

        with c2:
            description = st.text_area("Description :", value=meta.get("description", ""), height=100)
            collection_method = st.text_area("Méthode de collecte :", value=meta.get("collection_method", ""), height=68)
            target_population = st.text_input("Population cible :", value=meta.get("target_population", ""))
            license_val = st.selectbox("Licence :", ["", "CC-BY 4.0", "CC-BY-SA 4.0", "CC-BY-NC 4.0", "CC0 1.0", "ODC-ODbL", "Autre"],
                                       index=["", "CC-BY 4.0", "CC-BY-SA 4.0", "CC-BY-NC 4.0", "CC0 1.0", "ODC-ODbL", "Autre"].index(meta.get("license", "")) if meta.get("license", "") in ["", "CC-BY 4.0", "CC-BY-SA 4.0", "CC-BY-NC 4.0", "CC0 1.0", "ODC-ODbL", "Autre"] else 0)
            access_conditions = st.text_input("Conditions d'accès :", value=meta.get("access_conditions", ""), placeholder="ex: Libre, Sur demande...")
            keywords = st.text_input("Mots-clés :", value=meta.get("keywords", ""), placeholder="séparés par des virgules")
            contact = st.text_input("Contact :", value=meta.get("contact", ""))

        citation = st.text_area("Citation recommandée :", value=meta.get("citation", ""), height=68)

        if st.form_submit_button("Enregistrer les métadonnées", type="primary"):
            st.session_state.metadata = {
                "title": title, "author": author, "organization": organization,
                "country": country, "geographic_area": geographic_area,
                "collection_period": collection_period, "description": description,
                "collection_method": collection_method, "target_population": target_population,
                "license": license_val, "access_conditions": access_conditions,
                "keywords": keywords, "contact": contact, "version": version, "citation": citation,
            }
            st.success("Métadonnées enregistrées.")
            st.rerun()

    # Progress
    filled = sum(1 for v in st.session_state.metadata.values() if v)
    total_fields = 15
    st.progress(filled / total_fields, text=f"{filled}/{total_fields} champs renseignés")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Retour", key="m_back"):
            st.session_state.step = 4; st.rerun()
    with col2:
        if st.button("Score FAIR →", type="primary", key="m_next"):
            st.session_state.step = 6; st.rerun()


# ═══════════════════════════════════════════════════════════════
# STEP 6: FAIR SCORE
# ═══════════════════════════════════════════════════════════════

def step_fair():
    st.markdown("### Étape 6 : Évaluation de la conformité FAIR")
    df = st.session_state.df
    if df is None:
        st.warning("Veuillez d'abord importer un fichier.")
        return

    fair = compute_fair_score(df, st.session_state.metadata, st.session_state.variable_docs)
    st.session_state.fair_score = fair

    # Total score
    col_g, col_d = st.columns([1, 2])
    with col_g:
        fig = plot_gauge(fair["total"])
        st.pyplot(fig)

    with col_d:
        st.markdown("**Scores par principe FAIR :**")
        for letter, full_name in [("F","Findable (Trouvable)"), ("A","Accessible"), ("I","Interoperable (Interopérable)"), ("R","Reusable (Réutilisable)")]:
            s = fair["scores"][letter]
            m = fair["max_scores"][letter]
            pct = s/m if m > 0 else 0
            color = "#C62828" if pct < 0.4 else "#FF6F00" if pct < 0.7 else "#1B5E20"
            bg_color = "#FFEBEE" if pct < 0.4 else "#FFF3E0" if pct < 0.7 else "#E8F5E9"
            st.markdown(f"""<div style="background:{bg_color};border-left:4px solid {color};padding:0.5rem 1rem;border-radius:0 8px 8px 0;margin:0.3rem 0">
                <span class="fair-letter" style="background:{color};font-size:1.2rem;width:40px;height:40px;line-height:40px">{letter}</span>
                <strong>{full_name}</strong> : <span style="color:{color};font-weight:bold">{s}/{m}</span>
            </div>""", unsafe_allow_html=True)

    # Details
    for letter, full_name in [("F","Findable"), ("A","Accessible"), ("I","Interoperable"), ("R","Reusable")]:
        with st.expander(f"{letter} — {full_name}"):
            for status, msg in fair["details"][letter]:
                icon = "✅" if status == "ok" else "⚠️" if status == "partial" else "❌"
                st.write(f"{icon} {msg}")

    # Radar
    labels = ["Findable", "Accessible", "Interoperable", "Reusable"]
    values = [fair["scores"][l[0]] for l in labels]
    maxs = [fair["max_scores"][l[0]] for l in labels]
    fig_r = plot_radar(labels, values, maxs, "Profil FAIR")
    st.pyplot(fig_r)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Retour", key="f_back"):
            st.session_state.step = 5; st.rerun()
    with col2:
        if st.button("Score AI Readiness →", type="primary", key="f_next"):
            st.session_state.step = 7; st.rerun()


# ═══════════════════════════════════════════════════════════════
# STEP 7: AI READINESS
# ═══════════════════════════════════════════════════════════════

def step_ai_readiness():
    st.markdown("### Étape 7 : Évaluation AI Readiness")
    df = st.session_state.df
    if df is None:
        st.warning("Veuillez d'abord importer un fichier.")
        return

    ai = compute_ai_readiness(df, st.session_state.metadata, st.session_state.variable_docs)
    st.session_state.ai_score = ai

    col_g, col_d = st.columns([1, 2])
    with col_g:
        fig = plot_gauge(ai["total"])
        st.pyplot(fig)
        level_name, level_color = ai["level"]
        st.markdown(f'<div style="text-align:center"><span style="background:{level_color};color:white;padding:6px 20px;border-radius:20px;font-weight:bold">{level_name}</span></div>', unsafe_allow_html=True)

    with col_d:
        for dim, score in ai["dims"].items():
            m = ai["max_dims"][dim]
            pct = score/m if m > 0 else 0
            color = "#C62828" if pct < 0.4 else "#FF6F00" if pct < 0.7 else "#1B5E20"
            st.markdown(f"""<div style="display:flex;align-items:center;margin:0.3rem 0;gap:0.5rem">
                <div style="width:180px;font-weight:600;font-size:0.85rem">{dim}</div>
                <div style="flex:1;background:#E0E0E0;border-radius:10px;height:14px">
                    <div style="background:{color};width:{pct*100:.0f}%;height:14px;border-radius:10px"></div>
                </div>
                <div style="width:50px;text-align:right;font-weight:bold;color:{color}">{score}/{m}</div>
            </div>""", unsafe_allow_html=True)

    # Radar
    labels = list(ai["dims"].keys())
    values = list(ai["dims"].values())
    maxs = [ai["max_dims"][l] for l in labels]
    fig_r = plot_radar(labels, values, maxs, "Profil AI Readiness")
    st.pyplot(fig_r)

    # Details
    for dim in ai["dims"]:
        with st.expander(f"{dim} — {ai['dims'][dim]}/{ai['max_dims'][dim]}"):
            for line in ai["details"][dim]:
                st.write(line)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Retour", key="ai_back"):
            st.session_state.step = 6; st.rerun()
    with col2:
        if st.button("Recommandations →", type="primary", key="ai_next"):
            st.session_state.step = 8; st.rerun()


# ═══════════════════════════════════════════════════════════════
# STEP 8: RECOMMENDATIONS
# ═══════════════════════════════════════════════════════════════

def step_recommendations():
    st.markdown("### Étape 8 : Recommandations")
    df = st.session_state.df
    if df is None:
        st.warning("Veuillez d'abord importer un fichier.")
        return

    if st.session_state.quality_report is None:
        st.session_state.quality_report = analyze_quality(df)
    if st.session_state.fair_score is None:
        st.session_state.fair_score = compute_fair_score(df, st.session_state.metadata, st.session_state.variable_docs)
    if st.session_state.ai_score is None:
        st.session_state.ai_score = compute_ai_readiness(df, st.session_state.metadata, st.session_state.variable_docs)

    recos = generate_recommendations(df, st.session_state.metadata, st.session_state.variable_docs,
                                      st.session_state.quality_report, st.session_state.fair_score, st.session_state.ai_score)
    st.session_state.recommendations = recos

    n_urgent = sum(1 for r in recos if r[0] == "urgent")
    n_important = sum(1 for r in recos if r[0] == "important")
    n_improve = sum(1 for r in recos if r[0] == "improve")

    c1, c2, c3 = st.columns(3)
    c1.metric("Urgentes", n_urgent)
    c2.metric("Importantes", n_important)
    c3.metric("Améliorations", n_improve)

    for prio, title, desc in recos:
        if prio == "urgent":
            css, icon = "reco-urgent", "🔴"
        elif prio == "important":
            css, icon = "reco-important", "🟡"
        else:
            css, icon = "reco-improve", "🟢"
        st.markdown(f'<div class="reco-card {css}"><strong>{icon} {title}</strong><br>{desc}</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Retour", key="r_back"):
            st.session_state.step = 7; st.rerun()
    with col2:
        if st.button("Exporter →", type="primary", key="r_next"):
            st.session_state.step = 9; st.rerun()


# ═══════════════════════════════════════════════════════════════
# STEP 9: EXPORT
# ═══════════════════════════════════════════════════════════════

def step_export():
    st.markdown("### Étape 9 : Exporter la version finale")
    df = st.session_state.df
    if df is None:
        st.warning("Veuillez d'abord importer un fichier.")
        return

    # Ensure all scores are computed
    if st.session_state.quality_report is None:
        st.session_state.quality_report = analyze_quality(df)
    if st.session_state.fair_score is None:
        st.session_state.fair_score = compute_fair_score(df, st.session_state.metadata, st.session_state.variable_docs)
    if st.session_state.ai_score is None:
        st.session_state.ai_score = compute_ai_readiness(df, st.session_state.metadata, st.session_state.variable_docs)
    if not st.session_state.recommendations:
        st.session_state.recommendations = generate_recommendations(df, st.session_state.metadata, st.session_state.variable_docs,
                                                                     st.session_state.quality_report, st.session_state.fair_score, st.session_state.ai_score)

    st.markdown("Le dossier d'export contient :")
    items = [
        "La base de données corrigée (CSV)",
        "Les métadonnées (JSON)",
        "Le dictionnaire de données (CSV + JSON)",
        "Le rapport qualité (JSON)",
        "Le score FAIR (JSON)",
        "Le score AI Readiness (JSON)",
        "Les recommandations (JSON)",
        "L'historique des modifications (JSON)",
        "Le rapport final complet (HTML)",
    ]
    for item in items:
        st.markdown(f"- {item}")

    # Summary
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    fair_total = st.session_state.fair_score["total"]
    ai_total = st.session_state.ai_score["total"]
    c1.metric("Lignes", df.shape[0])
    c2.metric("Colonnes", df.shape[1])
    c3.metric("Score FAIR", f"{fair_total}/100")
    c4.metric("Score AI Readiness", f"{ai_total}/100")

    st.markdown("---")

    # Download ZIP
    zip_buf = create_export_zip(df, st.session_state.metadata, st.session_state.variable_docs,
                                 st.session_state.quality_report, st.session_state.fair_score,
                                 st.session_state.ai_score, st.session_state.recommendations,
                                 st.session_state.edit_history)

    st.download_button(
        label="Télécharger le dossier complet (ZIP)",
        data=zip_buf,
        file_name=f"agridata_ready_{datetime.now().strftime('%Y%m%d_%H%M')}.zip",
        mime="application/zip",
        use_container_width=True,
        type="primary"
    )

    # Individual exports
    st.markdown("**Exports individuels :**")
    c1, c2, c3 = st.columns(3)
    with c1:
        csv_buf = io.StringIO()
        df.to_csv(csv_buf, index=False)
        st.download_button("Données corrigées (CSV)", csv_buf.getvalue().encode("utf-8-sig"),
                           "donnees_corrigees.csv", "text/csv", key="dl_csv")
    with c2:
        st.download_button("Métadonnées (JSON)", json.dumps(st.session_state.metadata, ensure_ascii=False, indent=2),
                           "metadonnees.json", "application/json", key="dl_meta")
    with c3:
        html = generate_html_report(df, st.session_state.metadata, st.session_state.variable_docs,
                                     st.session_state.quality_report, st.session_state.fair_score,
                                     st.session_state.ai_score, st.session_state.recommendations,
                                     st.session_state.edit_history)
        st.download_button("Rapport final (HTML)", html, "rapport_final.html", "text/html", key="dl_html")

    if st.button("← Retour", key="x_back"):
        st.session_state.step = 8; st.rerun()


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def logo_data_uri():
    logo_path = Path(__file__).parent / "assets" / "logo_afridata_ready_white.png"
    if not logo_path.exists():
        return ""
    encoded = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def main():
    logo_uri = logo_data_uri()
    logo_html = f'<img src="{logo_uri}" alt="AfriData Ready">' if logo_uri else '<h1>AfriData Ready</h1>'
    st.markdown(f"""
    <div class="main-header">
        {logo_html}
        <p class="slogan">From Raw Data to FAIR & AI-Ready Data</p>
        <p class="sub">Transformez vos données brutes en données propres, documentées et exploitables</p>
    </div>
    """, unsafe_allow_html=True)

    render_sidebar()

    step_funcs = {
        1: step_import, 2: step_quality, 3: step_edit,
        4: step_variable_docs, 5: step_metadata, 6: step_fair,
        7: step_ai_readiness, 8: step_recommendations, 9: step_export,
    }
    step_funcs[st.session_state.step]()

if __name__ == "__main__":
    main()
