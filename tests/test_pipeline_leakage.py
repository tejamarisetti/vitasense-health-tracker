"""
Pytest Suite for Data Leakage Prevention and Preprocessor Integrity
VitaSense AI - PRD Sections 23-28

Tests:
1. Strict assertions that imputer medians and scaler mean/std in a fitted pipeline
   equal statistics computed on the training rows ONLY, and strictly DIFFER from
   statistics computed on the full dataset.
2. Asserts that zero rows are dropped (all 303 UCI instances preserved).
3. Asserts that test set inference never mutates fitted preprocessor parameters.
"""

import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression

from scripts.prepare_datasets import (
    load_uci_cleveland,
    build_tabular_preprocessor,
    build_model_pipeline,
    CONTINUOUS_FEATURES,
    CATEGORICAL_FEATURES,
)


@pytest.fixture
def uci_data():
    X, y, meta = load_uci_cleveland()
    return X, y, meta


def test_zero_row_dropping_preserves_all_instances(uci_data):
    X, y, meta = uci_data
    assert len(X) == 303, f"Expected 303 instances, got {len(X)}"
    assert len(y) == 303, f"Expected 303 target labels, got {len(y)}"
    assert meta["missing_counts"] == {"ca": 4, "thal": 2}, "Expected missingness in ca and thal only"

    # Ensure preprocessor transforms all rows into 28 feature columns
    preprocessor = build_tabular_preprocessor()
    X_trans = preprocessor.fit_transform(X)
    assert X_trans.shape == (303, 28), f"Expected shape (303, 28), got {X_trans.shape}"
    assert not np.isnan(X_trans).any(), "Found NaN in preprocessed output"


def test_imputer_and_scaler_learned_strictly_from_train_split(uci_data):
    X, y, _ = uci_data

    # Use a split where training statistics differ from full dataset statistics
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    # 1. Compute ground-truth statistics on full data
    full_medians = X[CONTINUOUS_FEATURES].median().values.astype(float)
    full_means = X[CONTINUOUS_FEATURES].mean().values.astype(float)
    full_stds = X[CONTINUOUS_FEATURES].std(ddof=0).values.astype(float)

    # 2. Compute ground-truth statistics on training split only
    train_medians = X_train[CONTINUOUS_FEATURES].median().values.astype(float)
    train_means = X_train[CONTINUOUS_FEATURES].mean().values.astype(float)
    train_stds = X_train[CONTINUOUS_FEATURES].std(ddof=0).values.astype(float)

    # CRITICAL PRE-CONDITION: Verify that training stats actually differ from full dataset stats
    # (If they did not differ, this test would not be discriminative against data leakage)
    assert not np.allclose(train_means, full_means, atol=1e-3), (
        "Train means and full means are identical; test cannot detect leakage. Change seed or split."
    )
    assert not np.allclose(train_stds, full_stds, atol=1e-3), (
        "Train stds and full stds are identical; test cannot detect leakage."
    )

    # 3. Fit pipeline on training data only
    pipeline = build_model_pipeline(LogisticRegression(max_iter=1000, random_state=42))
    pipeline.fit(X_train, y_train)

    preprocessor = pipeline.named_steps["preprocessor"]
    fitted_num_imputer = preprocessor.named_transformers_["num"].named_steps["imputer"]
    fitted_scaler = preprocessor.named_transformers_["num"].named_steps["scaler"]
    fitted_cat_imputer = preprocessor.named_transformers_["cat"].named_steps["imputer"]

    # 4. ASSERT: Pipeline statistics match training rows EXACTLY
    np.testing.assert_allclose(
        fitted_num_imputer.statistics_,
        train_medians,
        err_msg="Numeric imputer medians must equal training split medians exactly."
    )
    np.testing.assert_allclose(
        fitted_scaler.mean_,
        train_means,
        err_msg="StandardScaler mean must equal training split mean exactly."
    )
    np.testing.assert_allclose(
        fitted_scaler.scale_,
        train_stds,
        err_msg="StandardScaler scale (std) must equal training split std exactly."
    )

    # 5. ASSERT: Pipeline statistics DIFFER from full dataset statistics (proving no leakage)
    assert not np.allclose(fitted_scaler.mean_, full_means, atol=1e-3), (
        "LEAKAGE DETECTED: StandardScaler mean equals full dataset mean!"
    )
    assert not np.allclose(fitted_scaler.scale_, full_stds, atol=1e-3), (
        "LEAKAGE DETECTED: StandardScaler scale equals full dataset std!"
    )

    # 6. Categorical imputer mode check
    train_cat_modes = []
    for col in CATEGORICAL_FEATURES:
        mode_val = X_train[col].dropna().mode().iloc[0]
        train_cat_modes.append(float(mode_val))
    np.testing.assert_allclose(
        fitted_cat_imputer.statistics_.astype(float),
        train_cat_modes,
        err_msg="Categorical imputer modes must match training split modes exactly."
    )


def test_inference_does_not_mutate_pipeline_state(uci_data):
    X, y, _ = uci_data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    pipeline = build_model_pipeline(LogisticRegression(max_iter=1000, random_state=42))
    pipeline.fit(X_train, y_train)

    preprocessor = pipeline.named_steps["preprocessor"]
    scaler = preprocessor.named_transformers_["num"].named_steps["scaler"]

    mean_before = np.copy(scaler.mean_)
    scale_before = np.copy(scaler.scale_)

    # Run inference on test data multiple times
    _ = pipeline.predict(X_test)
    _ = pipeline.predict_proba(X_test)

    # State must be completely immutable during evaluation
    np.testing.assert_array_equal(scaler.mean_, mean_before, "Inference mutated scaler mean!")
    np.testing.assert_array_equal(scaler.scale_, scale_before, "Inference mutated scaler scale!")
