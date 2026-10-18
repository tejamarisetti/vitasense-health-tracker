"""
Experiment A: Paper-Grade Clinical Tabular Baseline (UCI Cleveland Heart Disease)
PRD Sections 23-28 | Target Publication: IEEE EMBC / JBHI

Models Evaluated:
1. Fixed-Threshold Rule Baseline (Clinical heuristic)
2. Logistic Regression (L2 penalty, lbfgs)
3. Random Forest Classifier
4. Gradient Boosting Classifier

Validation Strategy:
- 5x10 Repeated Stratified K-Fold Cross-Validation (50 folds)
- Preprocessing (Imputation + Scaling + OneHotEncoding) fit strictly on train folds
- 95% Bootstrap Confidence Intervals (1,000 resamples) computed on pooled out-of-fold predictions
- Brier Score and Calibration Curves
- Permutation Feature Importance & SHAP Tree Explainer
- Strict artifact saving to models/v0.2.0/ with full metadata

LABEL: "clinical tabular baseline, not wearable data, no clinical validity"
"""

import sys
import platform
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any
import numpy as np
import pandas as pd
import joblib

from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    precision_score,
    recall_score,
    f1_score,
    brier_score_loss,
    confusion_matrix,
)
import sklearn
import shap

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "models" / "v0.2.0"
INVENTORY_PATH = ROOT / "models" / "inventory.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prepare_datasets import (
    load_uci_cleveland,
    build_tabular_preprocessor,
    build_model_pipeline,
    get_cv_splitter,
    CONTINUOUS_FEATURES,
    CATEGORICAL_FEATURES,
)


class FixedThresholdRuleClassifier(BaseEstimator, ClassifierMixin):
    """
    Standard clinical guideline threshold rule for cardiovascular risk.
    Evaluates 5 heuristic risk criteria:
    1. Age >= 55 and Resting Blood Pressure (trestbps) >= 140 mm Hg
    2. ST depression (oldpeak) >= 1.5 mm
    3. Exercise-induced angina (exang) == 1
    4. Major vessels colored by fluoroscopy (ca) >= 1
    5. Asymptomatic chest pain (cp) == 4
    
    A patient is flagged high risk if >= 2 criteria are positive.
    Predicted probability is proportional to active criteria count (count / 5.0).
    """

    def __init__(self, threshold_criteria_count: int = 2):
        self.threshold_criteria_count = threshold_criteria_count
        self.classes_ = np.array([0, 1])

    def fit(self, X, y=None):
        # Deterministic heuristic; no parameter optimization
        return self

    def _evaluate_criteria(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        # Resolve DataFrame representation if passed as raw or DataFrame
        if not isinstance(X, pd.DataFrame):
            # If transformed array is passed, fallback to raw features mapped
            # But the rule classifier will be evaluated directly on raw X (with train-fold imputation)
            raise TypeError("FixedThresholdRuleClassifier expects a pandas DataFrame with raw column names")

        c1 = (X["age"] >= 55) & (X["trestbps"] >= 140)
        c2 = X["oldpeak"] >= 1.5
        c3 = X["exang"] == 1
        c4 = X["ca"].fillna(0) >= 1
        c5 = X["cp"] == 4

        active_counts = (c1.astype(int) + c2.astype(int) + c3.astype(int) + c4.astype(int) + c5.astype(int)).values
        probs = active_counts / 5.0
        preds = (active_counts >= self.threshold_criteria_count).astype(int)
        return preds, probs

    def predict(self, X):
        preds, _ = self._evaluate_criteria(X)
        return preds

    def predict_proba(self, X):
        _, probs = self._evaluate_criteria(X)
        return np.column_stack([1.0 - probs, probs])


def compute_bootstrap_ci(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray,
    n_bootstraps: int = 1000,
    seed: int = 42
) -> Dict[str, Dict[str, float]]:
    """
    Compute 95% bootstrap confidence intervals for all metrics on pooled out-of-fold predictions.
    Avoids understating uncertainty compared to fold-spread metrics.
    """
    rng = np.random.RandomState(seed)
    n_samples = len(y_true)
    boot_metrics = {
        "auroc": [],
        "auprc": [],
        "precision": [],
        "recall": [],
        "specificity": [],
        "f1": [],
        "brier_score": [],
    }

    for _ in range(n_bootstraps):
        idx = rng.randint(0, n_samples, n_samples)
        b_true = y_true[idx]
        b_pred = y_pred[idx]
        b_prob = y_prob[idx]

        # Check if both classes are present in sample
        if len(np.unique(b_true)) < 2:
            continue

        tn, fp, fn, tp = confusion_matrix(b_true, b_pred, labels=[0, 1]).ravel()
        spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0

        boot_metrics["auroc"].append(roc_auc_score(b_true, b_prob))
        boot_metrics["auprc"].append(average_precision_score(b_true, b_prob))
        boot_metrics["precision"].append(precision_score(b_true, b_pred, zero_division=0))
        boot_metrics["recall"].append(recall_score(b_true, b_pred, zero_division=0))
        boot_metrics["specificity"].append(spec)
        boot_metrics["f1"].append(f1_score(b_true, b_pred, zero_division=0))
        boot_metrics["brier_score"].append(brier_score_loss(b_true, b_prob))

    ci_summary = {}
    for metric_name, values in boot_metrics.items():
        arr = np.array(values)
        ci_summary[metric_name] = {
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "ci_lower": float(np.percentile(arr, 2.5)),
            "ci_upper": float(np.percentile(arr, 97.5)),
        }

    return ci_summary


def run_experiment_a() -> Dict[str, Any]:
    print("=" * 80)
    print("VitaSense AI - Running Experiment A (Clinical Tabular Baseline)")
    print("Protocol: 5x10 Repeated Stratified K-Fold (50 folds), Pooled Bootstrap CIs")
    print("Label: 'clinical tabular baseline, not wearable data, no clinical validity'")
    print("=" * 80)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    X, y, meta = load_uci_cleveland()
    cv = get_cv_splitter(n_splits=5, n_repeats=10, random_state=42)

    model_factories = {
        "fixed_threshold_rule": lambda: FixedThresholdRuleClassifier(threshold_criteria_count=2),
        "logistic_regression": lambda: build_model_pipeline(
            LogisticRegression(max_iter=1000, random_state=42, solver="lbfgs")
        ),
        "random_forest": lambda: build_model_pipeline(
            RandomForestClassifier(n_estimators=100, max_depth=5, min_samples_split=4, random_state=42)
        ),
        "gradient_boosting": lambda: build_model_pipeline(
            GradientBoostingClassifier(n_estimators=100, learning_rate=0.05, max_depth=3, random_state=42)
        ),
    }

    results = {}
    pooled_predictions = {name: {"y_true": [], "y_pred": [], "y_prob": []} for name in model_factories}
    fold_metrics = {name: {m: [] for m in ["auroc", "auprc", "precision", "recall", "specificity", "f1", "brier_score"]} for name in model_factories}

    print("\n[INFO] Executing 50 evaluation folds...")
    for fold_idx, (train_idx, test_idx) in enumerate(cv.split(X, y)):
        X_train, y_train = X.iloc[train_idx], y.iloc[train_idx]
        X_test, y_test = X.iloc[test_idx], y.iloc[test_idx]

        for model_name, factory in model_factories.items():
            model = factory()
            if model_name == "fixed_threshold_rule":
                # Evaluated directly on raw features
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
                y_prob = model.predict_proba(X_test)[:, 1]
            else:
                # Encapsulated scikit-learn pipeline (imputer + scaler fit on train fold only)
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
                y_prob = model.predict_proba(X_test)[:, 1]

            tn, fp, fn, tp = confusion_matrix(y_test, y_pred, labels=[0, 1]).ravel()
            spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0

            fold_metrics[model_name]["auroc"].append(roc_auc_score(y_test, y_prob))
            fold_metrics[model_name]["auprc"].append(average_precision_score(y_test, y_prob))
            fold_metrics[model_name]["precision"].append(precision_score(y_test, y_pred, zero_division=0))
            fold_metrics[model_name]["recall"].append(recall_score(y_test, y_pred, zero_division=0))
            fold_metrics[model_name]["specificity"].append(spec)
            fold_metrics[model_name]["f1"].append(f1_score(y_test, y_pred, zero_division=0))
            fold_metrics[model_name]["brier_score"].append(brier_score_loss(y_test, y_prob))

            pooled_predictions[model_name]["y_true"].extend(y_test.values)
            pooled_predictions[model_name]["y_pred"].extend(y_pred)
            pooled_predictions[model_name]["y_prob"].extend(y_prob)

    # Compile aggregate performance metrics
    print("\n" + "=" * 80)
    print("EXPERIMENT A - SUMMARY RESULTS (Mean +/- SD across 50 folds & 95% Bootstrap CI on Pooled Out-of-Fold)")
    print("=" * 80)

    final_report = {
        "experiment_id": "experiment_a_clinical_tabular_baseline",
        "label": "clinical tabular baseline, not wearable data, no clinical validity",
        "dataset": {
            "name": meta["dataset_name"],
            "instances": meta["total_instances"],
            "features_count": meta["total_features"],
            "citation": "Detrano et al. (1989)",
            "binarisation_rule": meta["binarisation_rule"],
        },
        "evaluation_protocol": {
            "method": "5x10 Repeated Stratified K-Fold Cross-Validation (50 folds)",
            "n_splits": 5,
            "n_repeats": 10,
            "random_seed": 42,
            "bootstrap_samples": 1000,
        },
        "environment": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "scikit_learn_version": sklearn.__version__,
            "shap_version": shap.__version__,
            "pandas_version": pd.__version__,
            "numpy_version": np.__version__,
        },
        "models": {},
        "calibration": {},
    }

    for model_name in model_factories:
        fold_summary = {}
        for m in fold_metrics[model_name]:
            arr = np.array(fold_metrics[model_name][m])
            fold_summary[m] = {
                "mean": float(np.mean(arr)),
                "std": float(np.std(arr)),
            }

        y_true_pooled = np.array(pooled_predictions[model_name]["y_true"])
        y_pred_pooled = np.array(pooled_predictions[model_name]["y_pred"])
        y_prob_pooled = np.array(pooled_predictions[model_name]["y_prob"])

        bootstrap_ci = compute_bootstrap_ci(y_true_pooled, y_pred_pooled, y_prob_pooled, n_bootstraps=1000, seed=42)

        # Calibration curve (10 bins)
        prob_true, prob_pred = calibration_curve(y_true_pooled, y_prob_pooled, n_bins=10, strategy="uniform")
        final_report["calibration"][model_name] = {
            "prob_true": [float(p) for p in prob_true],
            "prob_pred": [float(p) for p in prob_pred],
        }

        final_report["models"][model_name] = {
            "cross_fold_metrics": fold_summary,
            "pooled_bootstrap_ci": bootstrap_ci,
        }

        print(f"\nMODEL: {model_name.upper()}")
        print(f"  AUROC:       {fold_summary['auroc']['mean']:.4f} +/- {fold_summary['auroc']['std']:.4f} | 95% CI: [{bootstrap_ci['auroc']['ci_lower']:.4f}, {bootstrap_ci['auroc']['ci_upper']:.4f}]")
        print(f"  AUPRC:       {fold_summary['auprc']['mean']:.4f} +/- {fold_summary['auprc']['std']:.4f} | 95% CI: [{bootstrap_ci['auprc']['ci_lower']:.4f}, {bootstrap_ci['auprc']['ci_upper']:.4f}]")
        print(f"  F1-Score:    {fold_summary['f1']['mean']:.4f} +/- {fold_summary['f1']['std']:.4f} | 95% CI: [{bootstrap_ci['f1']['ci_lower']:.4f}, {bootstrap_ci['f1']['ci_upper']:.4f}]")
        print(f"  Sensitivity: {fold_summary['recall']['mean']:.4f} +/- {fold_summary['recall']['std']:.4f} | 95% CI: [{bootstrap_ci['recall']['ci_lower']:.4f}, {bootstrap_ci['recall']['ci_upper']:.4f}]")
        print(f"  Specificity: {fold_summary['specificity']['mean']:.4f} +/- {fold_summary['specificity']['std']:.4f} | 95% CI: [{bootstrap_ci['specificity']['ci_lower']:.4f}, {bootstrap_ci['specificity']['ci_upper']:.4f}]")
        print(f"  Brier Score: {fold_summary['brier_score']['mean']:.4f} +/- {fold_summary['brier_score']['std']:.4f} | 95% CI: [{bootstrap_ci['brier_score']['ci_lower']:.4f}, {bootstrap_ci['brier_score']['ci_upper']:.4f}]")

    # Fit final reference models on complete dataset for interpretability & versioned saving
    print("\n[INFO] Fitting final reference models on full dataset for SHAP & Permutation Analysis...")
    feature_importance_report = {
        "label": "clinical tabular baseline, not wearable data, no clinical validity",
        "permutation_importance": {},
        "shap_importance": {},
        "limitations_note": (
            "Permutation and SHAP importance values are derived exclusively from retrospective tabular "
            "clinical records (UCI Cleveland, N=303, Detrano et al., 1989). These features represent "
            "hospital diagnostic examination measurements and must NEVER be confused with continuous "
            "wearable photoplethysmography or accelerometer telemetry. They provide ZERO clinical diagnostic "
            "validity for wearable edge devices."
        )
    }

    fitted_pipelines = {}
    for name, factory in model_factories.items():
        m = factory()
        m.fit(X, y)
        fitted_pipelines[name] = m
        artifact_path = OUTPUT_DIR / f"{name}_pipeline.joblib"
        joblib.dump(m, artifact_path)

        # Compute permutation importance
        perm = permutation_importance(m, X, y, n_repeats=10, random_state=42)
        feature_importance_report["permutation_importance"][name] = {
            col: {"mean": float(mean), "std": float(std)}
            for col, mean, std in zip(X.columns, perm.importances_mean, perm.importances_std)
        }

    # SHAP Tree Explainer for Random Forest and Gradient Boosting
    preprocessor = fitted_pipelines["random_forest"].named_steps["preprocessor"]
    X_trans = preprocessor.transform(X)
    feature_names = list(preprocessor.get_feature_names_out())

    rf_clf = fitted_pipelines["random_forest"].named_steps["classifier"]
    rf_explainer = shap.TreeExplainer(rf_clf)
    rf_shap_values = rf_explainer.shap_values(X_trans)
    # Binary classification handling in SHAP
    if isinstance(rf_shap_values, list):
        rf_shap_class1 = rf_shap_values[1]
    elif len(rf_shap_values.shape) == 3:
        rf_shap_class1 = rf_shap_values[:, :, 1]
    else:
        rf_shap_class1 = rf_shap_values

    rf_mean_abs_shap = np.mean(np.abs(rf_shap_class1), axis=0)
    feature_importance_report["shap_importance"]["random_forest"] = {
        f_name: float(val) for f_name, val in sorted(zip(feature_names, rf_mean_abs_shap), key=lambda x: x[1], reverse=True)
    }

    gb_clf = fitted_pipelines["gradient_boosting"].named_steps["classifier"]
    gb_explainer = shap.TreeExplainer(gb_clf)
    gb_shap_values = gb_explainer.shap_values(X_trans)
    gb_mean_abs_shap = np.mean(np.abs(gb_shap_values), axis=0)
    feature_importance_report["shap_importance"]["gradient_boosting"] = {
        f_name: float(val) for f_name, val in sorted(zip(feature_names, gb_mean_abs_shap), key=lambda x: x[1], reverse=True)
    }

    # Save artifacts and JSON reports
    report_file = OUTPUT_DIR / "experiment_a_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2)

    fi_file = OUTPUT_DIR / "feature_importance.json"
    with open(fi_file, "w", encoding="utf-8") as f:
        json.dump(feature_importance_report, f, indent=2)

    # Update models/inventory.json
    inventory_entry = {
        "version": "v0.2.0",
        "release_date": "2026-10-16",
        "task": "tabular_heart_disease_baseline",
        "label": "clinical tabular baseline, not wearable data, no clinical validity",
        "dataset_source": "UCI Heart Disease (Cleveland Database, ID 45)",
        "instances": 303,
        "evaluation_protocol": "5x10 Repeated Stratified K-Fold (50 folds) with 95% Bootstrap CIs",
        "artifacts": [
            {
                "model_id": "vitasense_lr_v0.2.0",
                "artifact_file": "models/v0.2.0/logistic_regression_pipeline.joblib",
                "status": "active_benchmark",
                "algorithm": "LogisticRegression(lbfgs, max_iter=1000)",
                "auroc_mean": final_report["models"]["logistic_regression"]["cross_fold_metrics"]["auroc"]["mean"],
                "auroc_ci": [
                    final_report["models"]["logistic_regression"]["pooled_bootstrap_ci"]["auroc"]["ci_lower"],
                    final_report["models"]["logistic_regression"]["pooled_bootstrap_ci"]["auroc"]["ci_upper"],
                ],
                "f1_mean": final_report["models"]["logistic_regression"]["cross_fold_metrics"]["f1"]["mean"],
                "brier_score_mean": final_report["models"]["logistic_regression"]["cross_fold_metrics"]["brier_score"]["mean"],
            },
            {
                "model_id": "vitasense_rf_v0.2.0",
                "artifact_file": "models/v0.2.0/random_forest_pipeline.joblib",
                "status": "active_benchmark",
                "algorithm": "RandomForestClassifier(n_estimators=100, max_depth=5)",
                "auroc_mean": final_report["models"]["random_forest"]["cross_fold_metrics"]["auroc"]["mean"],
                "auroc_ci": [
                    final_report["models"]["random_forest"]["pooled_bootstrap_ci"]["auroc"]["ci_lower"],
                    final_report["models"]["random_forest"]["pooled_bootstrap_ci"]["auroc"]["ci_upper"],
                ],
                "f1_mean": final_report["models"]["random_forest"]["cross_fold_metrics"]["f1"]["mean"],
                "brier_score_mean": final_report["models"]["random_forest"]["cross_fold_metrics"]["brier_score"]["mean"],
            },
            {
                "model_id": "vitasense_gb_v0.2.0",
                "artifact_file": "models/v0.2.0/gradient_boosting_pipeline.joblib",
                "status": "active_benchmark",
                "algorithm": "GradientBoostingClassifier(n_estimators=100, learning_rate=0.05, max_depth=3)",
                "auroc_mean": final_report["models"]["gradient_boosting"]["cross_fold_metrics"]["auroc"]["mean"],
                "auroc_ci": [
                    final_report["models"]["gradient_boosting"]["pooled_bootstrap_ci"]["auroc"]["ci_lower"],
                    final_report["models"]["gradient_boosting"]["pooled_bootstrap_ci"]["auroc"]["ci_upper"],
                ],
                "f1_mean": final_report["models"]["gradient_boosting"]["cross_fold_metrics"]["f1"]["mean"],
                "brier_score_mean": final_report["models"]["gradient_boosting"]["cross_fold_metrics"]["brier_score"]["mean"],
            },
            {
                "model_id": "vitasense_fixed_threshold_rule_v0.2.0",
                "artifact_file": "models/v0.2.0/fixed_threshold_rule_pipeline.joblib",
                "status": "active_benchmark",
                "algorithm": "FixedThresholdRuleClassifier(clinical_heuristic_threshold=2)",
                "auroc_mean": final_report["models"]["fixed_threshold_rule"]["cross_fold_metrics"]["auroc"]["mean"],
                "auroc_ci": [
                    final_report["models"]["fixed_threshold_rule"]["pooled_bootstrap_ci"]["auroc"]["ci_lower"],
                    final_report["models"]["fixed_threshold_rule"]["pooled_bootstrap_ci"]["auroc"]["ci_upper"],
                ],
                "f1_mean": final_report["models"]["fixed_threshold_rule"]["cross_fold_metrics"]["f1"]["mean"],
                "brier_score_mean": final_report["models"]["fixed_threshold_rule"]["cross_fold_metrics"]["brier_score"]["mean"],
            },
        ]
    }

    existing_inventory = {"artifacts": []}
    if INVENTORY_PATH.exists():
        with open(INVENTORY_PATH, "r", encoding="utf-8") as f:
            existing_inventory = json.load(f)

    # Maintain prototype superseded artifact and append v0.2.0 release
    existing_inventory["v0.2.0"] = inventory_entry
    with open(INVENTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(existing_inventory, f, indent=2)

    print("\n[SUCCESS] Experiment A completed successfully!")
    print(f"Report saved to: {report_file}")
    print(f"Feature importance saved to: {fi_file}")
    print(f"Inventory updated at: {INVENTORY_PATH}")
    return final_report


if __name__ == "__main__":
    run_experiment_a()
