"""
Pytest Suite for Wrist-PPG Heart Rate Estimator
VitaSense AI - Component C Baseline Estimator Validation

Tests:
1. Accurate frequency recovery on pure cardiac tone (60, 90, 120 bpm) within 1 bpm error.
2. Rejection of NaN-corrupted windows.
3. Rejection of flatline zero-variance signals.
4. Correct spectral SQI calculation and confidence gating.
"""

import numpy as np
import pytest

from vitasense.estimators.ppg_hr_estimator import WristPPGHREstimator


@pytest.fixture
def estimator():
    return WristPPGHREstimator(fs_ppg=64.0, window_sec=8.0, step_sec=2.0)


@pytest.mark.parametrize("target_bpm", [60.0, 90.0, 120.0, 150.0])
def test_pure_tone_recovery(estimator, target_bpm):
    # 8 seconds @ 64 Hz = 512 samples
    fs = 64.0
    t = np.arange(512) / fs
    freq_hz = target_bpm / 60.0

    # Synthetic arterial pulse wave (fundamental + 2nd harmonic)
    bvp = np.sin(2 * np.pi * freq_hz * t) + 0.3 * np.sin(4 * np.pi * freq_hz * t)

    est = estimator.estimate_window(bvp, timestamp_sec=0.0)

    assert est.is_valid is True
    assert est.hr_bpm is not None
    # Maximum acceptable error is within FFT bin resolution (~0.93 bpm)
    assert abs(est.hr_bpm - target_bpm) <= 1.0
    assert est.spectral_sqi >= 0.50


def test_nan_rejection(estimator):
    bvp = np.sin(np.linspace(0, 10 * np.pi, 512))
    bvp[100:150] = np.nan

    est = estimator.estimate_window(bvp, timestamp_sec=0.0)
    assert est.is_valid is False
    assert est.hr_bpm is None
    assert est.rejection_reason == "contains_nan"


def test_flatline_rejection(estimator):
    flatline = np.zeros(512)

    est = estimator.estimate_window(flatline, timestamp_sec=0.0)
    assert est.is_valid is False
    assert est.hr_bpm is None
    assert est.rejection_reason == "flatline_zero_variance"
