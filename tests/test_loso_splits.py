"""
Pytest Suite for Subject-Wise (LOSO) Cross-Validation Split Utilities
VitaSense AI - Protocol Section 5: Subject Leakage Prevention

Tests:
1. Strict assertion that train_subjects and test_subjects have ZERO overlap.
2. Complete coverage: every subject is tested exactly once.
3. Complete partition: every sample index is evaluated exactly once in test folds.
4. GroupKFoldBySubject asserts zero leakage across multi-subject folds.
5. Independent validator function correctly catches intentional leakage.
"""

import numpy as np
import pandas as pd
import pytest

from vitasense.utils.splits import (
    LeaveOneSubjectOutSplitter,
    SubjectGroupKFoldSplitter,
    validate_zero_subject_leakage,
)


@pytest.fixture
def mock_dataset():
    """Generates 15 subjects with 100 samples each (1500 rows)."""
    np.random.seed(42)
    subjects = [f"S{i}" for i in range(1, 16)]
    rows = []
    for s in subjects:
        for i in range(100):
            rows.append({
                "subject_id": s,
                "hr_wrist": 70.0 + np.random.normal(0, 5),
                "hr_ecg": 70.0 + np.random.normal(0, 1),
                "acc_energy": np.random.uniform(0.01, 0.40),
            })
    return pd.DataFrame(rows)


def test_loso_zero_subject_leakage(mock_dataset):
    splitter = LeaveOneSubjectOutSplitter(subject_col="subject_id")
    unique_subjects = mock_dataset["subject_id"].unique()

    tested_subjects = []
    all_test_indices = []

    for train_idx, test_idx, test_subject in splitter.split(mock_dataset):
        train_subjects = mock_dataset.iloc[train_idx]["subject_id"].unique()
        test_subjects = mock_dataset.iloc[test_idx]["subject_id"].unique()

        # Strict assertion: intersection MUST be empty
        assert len(set(train_subjects).intersection(set(test_subjects))) == 0
        assert test_subject not in train_subjects
        assert set(test_subjects) == {test_subject}

        # Validate with independent validator
        assert validate_zero_subject_leakage(train_subjects, test_subjects) is True

        tested_subjects.append(test_subject)
        all_test_indices.extend(test_idx)

    # Every subject tested exactly once
    assert len(tested_subjects) == len(unique_subjects)
    assert set(tested_subjects) == set(unique_subjects)

    # Every index tested exactly once
    assert len(all_test_indices) == len(mock_dataset)
    assert len(set(all_test_indices)) == len(mock_dataset)


def test_group_kfold_zero_subject_leakage(mock_dataset):
    splitter = SubjectGroupKFoldSplitter(n_splits=5, subject_col="subject_id", seed=42)
    unique_subjects = set(mock_dataset["subject_id"].unique())

    all_test_subjects = set()
    all_test_indices = []

    for train_idx, test_idx, test_subject_group in splitter.split(mock_dataset):
        train_subjects = set(mock_dataset.iloc[train_idx]["subject_id"].unique())
        test_subjects = set(mock_dataset.iloc[test_idx]["subject_id"].unique())

        # Strict zero-leakage check
        assert len(train_subjects.intersection(test_subjects)) == 0
        assert validate_zero_subject_leakage(list(train_subjects), list(test_subjects)) is True

        all_test_subjects.update(test_subjects)
        all_test_indices.extend(test_idx)

    # All subjects and all rows partitioned cleanly
    assert all_test_subjects == unique_subjects
    assert len(all_test_indices) == len(mock_dataset)
    assert len(set(all_test_indices)) == len(mock_dataset)


def test_leakage_validator_catches_overlap():
    train_subjs = ["S1", "S2", "S3", "S4"]
    test_subjs_clean = ["S5", "S6"]
    test_subjs_leaked = ["S4", "S5"]

    assert validate_zero_subject_leakage(train_subjs, test_subjs_clean) is True

    with pytest.raises(AssertionError, match="Subject leakage detected"):
        validate_zero_subject_leakage(train_subjs, test_subjs_leaked)
