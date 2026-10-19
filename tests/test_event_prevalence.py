"""
Unit Tests for Unified Event Prevalence Module
VitaSense AI - Protocol Section 3.1 & Amendment 1 Validation
"""

import numpy as np
import pytest

from vitasense.quality.event_prevalence import (
    compute_enmo,
    align_activity_to_windows,
    find_continuous_events,
    compute_subject_prevalence,
    RESTING_ACTIVITY_CODES,
)


def test_compute_enmo_stationary_and_moving():
    # 1. Pure stationary gravity (1g along z-axis, 32 Hz for 10 seconds = 320 samples)
    acc_stationary = np.zeros((320, 3))
    acc_stationary[:, 2] = 1.0  # 1.0g

    step_vals, ma_vals = compute_enmo(acc_stationary, fs_acc=32.0, step_sec=2.0, ma_sec=10.0)
    assert len(step_vals) == 5
    assert np.allclose(step_vals, 0.0, atol=1e-6)
    assert np.allclose(ma_vals, 0.0, atol=1e-6)

    # 2. Moving wrist (1.5g magnitude, should give ENMO = 0.5g)
    acc_moving = np.zeros((320, 3))
    acc_moving[:, 2] = 1.5

    step_moving, ma_moving = compute_enmo(acc_moving, fs_acc=32.0, step_sec=2.0, ma_sec=10.0)
    assert np.allclose(step_moving, 0.5, atol=1e-6)
    assert np.allclose(ma_moving, 0.5, atol=1e-6)

    # 3. Unit safety check: raw Empatica 1/64g format (stationary = 64.0)
    acc_raw_64 = np.zeros((320, 3))
    acc_raw_64[:, 2] = 64.0
    step_raw, ma_raw = compute_enmo(acc_raw_64, fs_acc=32.0, step_sec=2.0, ma_sec=10.0)
    assert np.allclose(step_raw, 0.0, atol=1e-4)


def test_align_activity_to_windows():
    # 4 Hz activity signal for 40 seconds (160 samples)
    # First 20s (80 samples) is activity 1 (BASELINE)
    # Next 20s (80 samples) is activity 8 (WORKING)
    act = np.zeros(160, dtype=int)
    act[:80] = 1
    act[80:] = 8

    # 8-second windows stepped by 2 seconds: 17 windows
    aligned = align_activity_to_windows(
        activity=act,
        n_windows=17,
        fs_act=4.0,
        step_sec=2.0,
        window_sec=8.0,
        method="midpoint",
    )
    assert len(aligned) == 17
    # Window 0 midpoint: t = 4s (sample 16) -> 1
    assert aligned[0] == 1
    # Window 10 midpoint: t = 24s (sample 96) -> 8
    assert aligned[10] == 8


def test_find_continuous_events_synthetic():
    # 100 windows, 2s step = 200s total duration
    # Persistence threshold: 30s = 15 consecutive windows
    cond = np.zeros(100, dtype=bool)

    # Run 1: 10 windows (20s) -> below 30s threshold -> 0 events
    cond[5:15] = True

    # Run 2: 15 windows (30s) -> exactly threshold -> 1 event
    cond[25:40] = True

    # Run 3: 20 windows (40s) -> above threshold -> 1 event
    cond[60:80] = True

    events = find_continuous_events(cond, step_sec=2.0, min_duration_sec=30.0)

    assert len(events) == 2
    # First event: indices 25..39, duration 30.0s
    assert events[0][0] == 25
    assert events[0][1] == 39
    assert events[0][2] == pytest.approx(30.0)

    # Second event: indices 60..79, duration 40.0s
    assert events[1][0] == 60
    assert events[1][1] == 79
    assert events[1][2] == pytest.approx(40.0)


def test_compute_subject_prevalence_synthetic():
    """
    End-to-end synthetic subject with known ground truth:
    - 100 windows (200s = 3.333 min)
    - Activity: 30 windows BASELINE (1), 35 windows WORKING (8), 35 windows SOCCER (3)
    - Acc: first 65 windows stationary (1g, ENMO=0), last 35 windows active (1.5g, ENMO=0.5)
    - HR:
      - Windows 0..29: 60 bpm (BASELINE) -> mu_rest=60, sd_rest=0, tau_i=100 bpm
      - Windows 30..49 (20 win = 40s): 120 bpm (> tau_i) during WORKING + stationary -> EVENT 1 (40s)
      - Windows 50..64 (15 win = 30s): 75 bpm (normal resting HR) -> No event
      - Windows 65..84 (20 win = 40s): 130 bpm (> tau_i) during SOCCER + active -> EXCLUDED from resting!
      - Windows 85..99 (15 win = 30s): 80 bpm -> No event
    """
    n_windows = 100
    fs_acc = 32.0
    fs_act = 4.0
    step_sec = 2.0
    window_sec = 8.0

    total_acc_samples = int((n_windows * step_sec + window_sec) * fs_acc)
    total_act_samples = int((n_windows * step_sec + window_sec) * fs_act)

    acc = np.zeros((total_acc_samples, 3), dtype=float)
    acc[:, 2] = 1.0  # default 1.0g stationary

    # Active motion during SOCCER (starting at window 65, t = 130s)
    soccer_start_sample = int(65 * step_sec * fs_acc)
    acc[soccer_start_sample:, 2] = 1.5  # 1.5g -> ENMO = 0.5g

    act = np.zeros(total_act_samples, dtype=int)
    # First 30 windows (0..60s) = BASELINE (1)
    act[: int(30 * step_sec * fs_act)] = 1
    # Next 35 windows (60..130s) = WORKING (8)
    act[int(30 * step_sec * fs_act) : int(65 * step_sec * fs_act)] = 8
    # Last 35 windows (130..200s+) = SOCCER (3)
    act[int(65 * step_sec * fs_act) :] = 3

    labels = np.full(n_windows, 60.0, dtype=float)
    # Event 1: At-rest tachycardia during WORKING (windows 30..49, 40s)
    labels[30:50] = 120.0
    # Normal resting
    labels[50:65] = 75.0
    # Exercise tachycardia during SOCCER (windows 65..84, 40s)
    labels[65:85] = 130.0
    # Exercise recovery
    labels[85:100] = 80.0

    data = {
        "label": labels,
        "activity": act,
        "signal": {
            "wrist": {
                "ACC": acc,
            }
        },
    }

    metrics = compute_subject_prevalence(
        data=data,
        subject_id="SYNTH_01",
        theta_rest=0.05,
        t_persist=30.0,
        step_sec=2.0,
        window_sec=8.0,
    )

    # Total time: 100 * 2 / 60 = 3.333 min
    assert metrics["total_min"] == pytest.approx(100 * 2.0 / 60.0)
    # Baseline: 30 windows at 60 bpm -> tau_i = 100.0 (clamped to 100)
    assert metrics["tau_i"] == 100.0

    # Resting windows: windows 0..64 are resting activity (1 or 8) AND stationary -> 65 windows
    # 65 * 2 / 60 = 2.1667 min
    assert metrics["resting_min"] == pytest.approx(65 * 2.0 / 60.0, abs=0.1)

    # Amendment 1 events: exactly 1 event (windows 30..49 = 40s = 0.667 min)
    assert metrics["amend1_events"] == 1
    assert metrics["event_time_min"] == pytest.approx(40.0 / 60.0)

    # Uncontextualized events: includes both resting tachy (40s) and soccer tachy (40s) = 2 events
    assert metrics["uncontext_events"] == 2
