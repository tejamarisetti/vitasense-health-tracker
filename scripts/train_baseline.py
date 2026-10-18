"""
Baseline Training and Evaluation Pipeline for VitaSense AI (PROTOTYPE - SUPERSEDED)
PRD Sections 26 & 28

NOTE: This script generated the initial prototype model artifact (vitasense_rf_model.joblib),
which is now marked as "prototype, superseded" in models/inventory.json.
It used global listwise dropna() and single holdout split.
All paper-grade workflows use scripts/prepare_datasets.py with leak-free sklearn Pipelines
(imputer + scaler fit on train folds only, zero rows dropped, 5x10 RepeatedStratifiedKFold).
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, brier_score_loss
)
import joblib

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "raw" / "uci_heart_disease" / "uci_heart_disease.csv"
MODEL_DIR = ROOT / "models"
METADATA_DIR = ROOT / "data" / "metadata"


def train_eval():
    if not DATA_PATH.exists():
        print(f"[ERROR] Missing dataset: {DATA_PATH}")
        return

    df = pd.read_csv(DATA_PATH)
    # Target in UCI ID 45: 0 = healthy, 1-4 = presence of heart disease
    target_col = "target" if "target" in df.columns else "num"
    X = df.drop(columns=[target_col]).dropna()
    y = (df.loc[X.index, target_col] > 0).astype(int)

    # Train / test split (80 / 20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # 1. Simple Threshold / Logistic Regression Baseline
    log_reg = LogisticRegression(max_iter=1000, random_state=42)
    log_reg.fit(X_train, y_train)
    y_pred_lr = log_reg.predict(X_test)
    y_prob_lr = log_reg.predict_proba(X_test)[:, 1]

    # 2. Random Forest Classifier
    rf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    rf.fit(X_train, y_train)
    y_pred_rf = rf.predict(X_test)
    y_prob_rf = rf.predict_proba(X_test)[:, 1]

    # Metrics
    metrics_lr = {
        "model": "LogisticRegression_Baseline",
        "accuracy": float(accuracy_score(y_test, y_pred_lr)),
        "precision": float(precision_score(y_test, y_pred_lr)),
        "recall": float(recall_score(y_test, y_pred_lr)),
        "f1": float(f1_score(y_test, y_pred_lr)),
        "auroc": float(roc_auc_score(y_test, y_prob_lr)),
        "brier_score": float(brier_score_loss(y_test, y_prob_lr))
    }

    metrics_rf = {
        "model": "RandomForest_Classifier",
        "accuracy": float(accuracy_score(y_test, y_pred_rf)),
        "precision": float(precision_score(y_test, y_pred_rf)),
        "recall": float(recall_score(y_test, y_pred_rf)),
        "f1": float(f1_score(y_test, y_pred_rf)),
        "auroc": float(roc_auc_score(y_test, y_prob_rf)),
        "brier_score": float(brier_score_loss(y_test, y_prob_rf)),
        "feature_importances": {
            col: float(imp) for col, imp in zip(X.columns, rf.feature_importances_)
        }
    }

    # Save artifacts
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODEL_DIR / "vitasense_rf_model.joblib"
    joblib.dump(rf, model_path)

    report_path = METADATA_DIR / "model_evaluation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "task": "tabular_heart_disease_baseline",
            "dataset": "UCI Heart Disease (ID 45)",
            "sample_size": len(df),
            "features": list(X.columns),
            "metrics": {
                "logistic_regression": metrics_lr,
                "random_forest": metrics_rf
            },
            "disclaimer": "Educational and research prototype. Not intended as medical diagnosis or device."
        }, f, indent=2)

    print("[SUCCESS] Models trained and evaluated successfully!")
    print(f"  Random Forest AUROC: {metrics_rf['auroc']:.4f}, F1: {metrics_rf['f1']:.4f}")
    print(f"  Artifact saved to {model_path}")
    print(f"  Evaluation report saved to {report_path}")


if __name__ == "__main__":
    train_eval()
