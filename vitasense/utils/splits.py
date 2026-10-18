"""
VitaSense AI - Subject-Wise (LOSO) Cross-Validation Split Utilities
Protocol Section 5: Zero Inter-Subject Leakage Enforcement

Strict Scientific Guarantees:
1. Complete subject-level isolation: train_subjects intersect test_subjects is strictly EMPTY.
2. Every subject appears in the test fold exactly once across the LOSO sweep.
3. Every sample index is uniquely partitioned without duplication or omission.
"""

from typing import Any, Generator, List, Optional, Sequence, Set, Tuple, Union
import numpy as np
import pandas as pd


class LeaveOneSubjectOutSplitter:
    """
    Leave-One-Subject-Out (LOSO) cross-validation generator.
    Yields (train_indices, test_indices, test_subject_id) for each subject.
    """

    def __init__(self, subject_col: str = "subject_id"):
        self.subject_col = subject_col

    def split(
        self,
        data: Union[pd.DataFrame, Sequence[Any], np.ndarray],
        subjects: Optional[Sequence[Any]] = None,
    ) -> Generator[Tuple[np.ndarray, np.ndarray, Any], None, None]:
        """
        Generates train and test indices for each unique subject.
        """
        if isinstance(data, pd.DataFrame):
            if self.subject_col not in data.columns and subjects is None:
                raise ValueError(f"Column '{self.subject_col}' not found in DataFrame.")
            subject_series = data[self.subject_col].values if subjects is None else np.asarray(subjects)
            n_samples = len(data)
        else:
            if subjects is None:
                raise ValueError("When data is not a DataFrame, 'subjects' array must be provided.")
            subject_series = np.asarray(subjects)
            n_samples = len(subject_series)

        if len(subject_series) != n_samples:
            raise ValueError(f"Subjects length ({len(subject_series)}) must match data length ({n_samples}).")

        # Stable unique subjects maintaining appearance order
        unique_subjects = pd.unique(subject_series)

        if len(unique_subjects) < 2:
            raise ValueError(f"LOSO cross-validation requires at least 2 unique subjects, got {len(unique_subjects)}.")

        indices = np.arange(n_samples)

        for test_subject in unique_subjects:
            test_mask = (subject_series == test_subject)
            train_mask = ~test_mask

            train_idx = indices[train_mask]
            test_idx = indices[test_mask]

            # Enforce zero-leakage invariant at runtime
            train_subj_set = set(subject_series[train_idx])
            test_subj_set = set(subject_series[test_idx])
            leakage = train_subj_set.intersection(test_subj_set)
            if leakage:
                raise RuntimeError(f"CRITICAL DATA LEAKAGE: Subject(s) {leakage} found in both train and test splits!")

            yield train_idx, test_idx, test_subject


class SubjectGroupKFoldSplitter:
    """
    K-Fold cross-validation grouped strictly by subject.
    Ensures that all samples of any given subject reside exclusively in one fold.
    """

    def __init__(self, n_splits: int = 5, subject_col: str = "subject_id", seed: int = 42):
        self.n_splits = n_splits
        self.subject_col = subject_col
        self.seed = seed

    def split(
        self,
        data: Union[pd.DataFrame, Sequence[Any], np.ndarray],
        subjects: Optional[Sequence[Any]] = None,
    ) -> Generator[Tuple[np.ndarray, np.ndarray, List[Any]], None, None]:
        if isinstance(data, pd.DataFrame):
            subject_series = data[self.subject_col].values if subjects is None else np.asarray(subjects)
            n_samples = len(data)
        else:
            if subjects is None:
                raise ValueError("When data is not a DataFrame, 'subjects' array must be provided.")
            subject_series = np.asarray(subjects)
            n_samples = len(subject_series)

        unique_subjects = pd.unique(subject_series)
        n_unique = len(unique_subjects)

        if self.n_splits > n_unique:
            raise ValueError(f"Cannot perform {self.n_splits} folds with only {n_unique} unique subjects.")

        rng = np.random.default_rng(self.seed)
        shuffled_subjects = np.array(list(unique_subjects))
        rng.shuffle(shuffled_subjects)

        # Distribute subjects as evenly as possible across folds
        subject_folds = np.array_split(shuffled_subjects, self.n_splits)
        indices = np.arange(n_samples)

        for fold_idx, test_subject_group in enumerate(subject_folds):
            test_subject_set = set(test_subject_group)
            test_mask = np.isin(subject_series, test_subject_group)
            train_mask = ~test_mask

            train_idx = indices[train_mask]
            test_idx = indices[test_mask]

            train_subj_set = set(subject_series[train_idx])
            leakage = train_subj_set.intersection(test_subject_set)
            if leakage:
                raise RuntimeError(f"CRITICAL LEAKAGE in fold {fold_idx}: Subjects {leakage} present in both splits!")

            yield train_idx, test_idx, list(test_subject_group)


def validate_zero_subject_leakage(
    train_subjects: Sequence[Any],
    test_subjects: Sequence[Any],
) -> bool:
    """
    Independent validator asserting zero subject intersection.
    Raises AssertionError if leakage occurs; returns True if clean.
    """
    train_set = set(train_subjects)
    test_set = set(test_subjects)
    intersection = train_set.intersection(test_set)
    if intersection:
        raise AssertionError(
            f"Subject leakage detected: {len(intersection)} subject(s) present in both train and test! "
            f"Overlapping subjects: {intersection}"
        )
    return True
