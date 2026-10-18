"""
Pytest Suite for Rule-Based Data-Quality and Trust-Score Module
VitaSense AI - Component B & C Rule Validation

Tests:
1. Strict determinism: multiple evaluations on identical inputs yield bitwise identical results.
2. High fidelity on clean resting signal (trust >= 0.90, abstain = False).
3. Hard-gate zeroing on excessive missing gaps (NaN ratio >= 50%).
4. Hard-gate zeroing on flatlined/stale sensor lockup (variance < eps).
5. Hard-gate zeroing on non-physiological range violations (HR < 35 or > 220 bpm).
6. Non-physiological rate of change penalty (> 40 bpm/s jump).
7. Motion attenuation: high wrist accelerometer ENMO (> 0.30g) degrades trust score.
"""

import numpy as np
import pytest

from vitasense.quality.trust_score import RuleBasedTrustScorer, TrustScoreResult


@pytest.fixture
def scorer():
    return RuleBasedTrustScorer(abstention_threshold=0.70)


@pytest.fixture
def clean_resting_hr():
    # 30 seconds of clean resting HR (around 72 bpm, natural sinus variability)
    np.random.seed(42)
    return 72.0 + 1.5 * np.sin(np.linspace(0, 4 * np.pi, 30)) + np.random.normal(0, 0.2, 30)


@pytest.fixture
def resting_acc():
    # 30 seconds @ 32 Hz of static resting wrist acceleration (1.0g gravity, low dynamic energy)
    np.random.seed(42)
    n = 30 * 32
    acc = np.zeros((n, 3))
    acc[:, 2] = 0.98 + np.random.normal(0, 0.01, n)
    acc[:, 0] = np.random.normal(0, 0.01, n)
    acc[:, 1] = np.random.normal(0, 0.01, n)
    return acc


def test_scorer_determinism(scorer, clean_resting_hr, resting_acc):
    res1 = scorer.evaluate_window(clean_resting_hr, fs_hr=1.0, acc_window=resting_acc, fs_acc=32.0)
    res2 = scorer.evaluate_window(clean_resting_hr, fs_hr=1.0, acc_window=resting_acc, fs_acc=32.0)

    assert res1.trust_score == res2.trust_score
    assert res1.sub_scores == res2.sub_scores
    assert res1.abstain == res2.abstain
    assert res1.reasons == res2.reasons


def test_clean_resting_signal_high_trust(scorer, clean_resting_hr, resting_acc):
    res = scorer.evaluate_window(clean_resting_hr, fs_hr=1.0, acc_window=resting_acc, fs_acc=32.0)

    assert res.trust_score >= 0.90
    assert res.abstain is False
    assert res.sub_scores["gap"] == 1.0
    assert res.sub_scores["stale"] == 1.0
    assert res.sub_scores["phys"] == 1.0
    assert res.sub_scores["motion"] == 1.0


def test_excessive_gap_hard_zero(scorer, clean_resting_hr):
    corrupted = clean_resting_hr.copy()
    corrupted[:18] = np.nan  # 18 / 30 = 60% missing

    res = scorer.evaluate_window(corrupted, fs_hr=1.0)
    assert res.sub_scores["gap"] == 0.0
    assert res.trust_score == 0.0
    assert res.abstain is True
    assert any("excessive_missing_gaps" in r for r in res.reasons)


def test_flatline_stale_hard_zero(scorer):
    flatline = np.full(30, 75.0)  # Exactly constant across 30s
    res = scorer.evaluate_window(flatline, fs_hr=1.0)

    assert res.sub_scores["stale"] == 0.0
    assert res.trust_score == 0.0
    assert res.abstain is True
    assert any("flatline" in r for r in res.reasons)


def test_physiological_range_violation(scorer, clean_resting_hr):
    corrupted = clean_resting_hr.copy()
    corrupted[10] = 260.0  # Impossible human heart rate

    res = scorer.evaluate_window(corrupted, fs_hr=1.0)
    assert res.sub_scores["phys"] == 0.0
    assert res.trust_score == 0.0
    assert res.abstain is True
    assert any("physiological_range_violation" in r for r in res.reasons)


def test_rate_of_change_penalty(scorer, clean_resting_hr):
    corrupted = clean_resting_hr.copy()
    corrupted[15] = corrupted[14] + 55.0  # +55 bpm jump in 1 second

    res = scorer.evaluate_window(corrupted, fs_hr=1.0)
    assert res.sub_scores["phys"] < 1.0
    assert any("non_physiological_rate_of_change" in r for r in res.reasons)


def test_severe_motion_penalty(scorer, clean_resting_hr):
    # Severe running/exercise accelerometer data: ENMO ~ 0.8g
    np.random.seed(42)
    n = 30 * 32
    acc_running = np.zeros((n, 3))
    acc_running[:, 0] = np.random.normal(0, 1.2, n)
    acc_running[:, 1] = np.random.normal(0, 1.0, n)
    acc_running[:, 2] = np.random.normal(1.0, 1.5, n)

    res = scorer.evaluate_window(clean_resting_hr, fs_hr=1.0, acc_window=acc_running, fs_acc=32.0)
    assert res.sub_scores["motion"] <= 0.30
    assert res.trust_score < 0.70
    assert res.abstain is True
    assert any("severe_motion_artifact" in r for r in res.reasons)
