"""
VitaSense AI - Unit Tests for StandardAlertEmitter (Protocol Amendment 4)
Tests:
1. Alert fires only after P seconds of continuous condition (runs < P never fire; run == P fires).
2. None during refractory (R = 60s hold-off suppresses triggers).
3. Same emitter used by every arm (Arm 1 and Arm 2 use identical emitter logic and produce identical filtering).
"""

import numpy as np
import pytest
from vitasense.benchmarks.alert_emitter import StandardAlertEmitter, AlertEmitterConfig
from vitasense.benchmarks.alerting_arms import (
    Arm1FixedThreshold,
    Arm2PersonalBaselineShrinkage,
)


def test_alert_fires_only_after_p_seconds():
    """
    Protocol Amendment 4 Section 1.1:
    An alert is emitted if and only if the arm's criteria hold continuously
    for at least P consecutive seconds (W_p = P / step_sec contiguous windows).
    Excursions shorter than P seconds must be suppressed.
    """
    step_sec = 2.0

    for p_sec in [10.0, 20.0, 30.0]:
        emitter = StandardAlertEmitter(p_persist_sec=p_sec, r_refractory_sec=60.0, step_sec=step_sec)
        w_p = int(p_sec / step_sec)

        # 1. Condition True for W_p - 1 windows: MUST NOT FIRE
        cond_short = np.zeros(50, dtype=bool)
        cond_short[5: 5 + w_p - 1] = True
        emitted_short = emitter.emit(cond_short)
        assert not np.any(emitted_short), f"Alert fired for run length {w_p - 1} < W_p={w_p} (P={p_sec}s)!"

        # 2. Condition True for exactly W_p windows: MUST FIRE at index 5 + w_p - 1
        cond_exact = np.zeros(50, dtype=bool)
        cond_exact[5: 5 + w_p] = True
        emitted_exact = emitter.emit(cond_exact)
        expected_fire_idx = 5 + w_p - 1
        assert np.sum(emitted_exact) == 1, f"Expected exactly 1 alert for W_p={w_p}, got {np.sum(emitted_exact)}"
        assert emitted_exact[expected_fire_idx], f"Expected alert at index {expected_fire_idx}"

        # 3. Interrupted runs (3 True, 1 False, 3 True): MUST NOT FIRE if each run < W_p
        cond_interrupted = np.zeros(50, dtype=bool)
        cond_interrupted[10: 10 + w_p - 1] = True
        cond_interrupted[10 + w_p - 1] = False
        cond_interrupted[10 + w_p: 10 + 2 * w_p - 1] = True
        emitted_interrupted = emitter.emit(cond_interrupted)
        assert not np.any(emitted_interrupted), "Interrupted excursions should not accumulate persistence!"


def test_none_during_refractory():
    """
    Protocol Amendment 4 Section 1.2:
    Following any emitted alert, an alarm refractory hold-off of R = 60s
    (W_r = R / step_sec windows) is enforced, during which subsequent triggers are suppressed.
    """
    step_sec = 2.0
    p_sec = 10.0  # W_p = 5
    r_sec = 60.0  # W_r = 30
    emitter = StandardAlertEmitter(p_persist_sec=p_sec, r_refractory_sec=r_sec, step_sec=step_sec)

    w_p = int(p_sec / step_sec)  # 5
    w_r = int(r_sec / step_sec)  # 30

    # Continuous True for 100 windows
    n_windows = 100
    cond = np.ones(n_windows, dtype=bool)
    emitted = emitter.emit(cond)

    fire_indices = np.where(emitted)[0]
    assert len(fire_indices) >= 2, "Expected multiple alerts over 100 windows"

    # First alert must fire at index w_p - 1 = 4
    assert fire_indices[0] == w_p - 1, f"First alert should fire at index {w_p - 1}"

    # During refractory (windows 5 to 33, exactly 29 windows), ZERO alerts must fire
    refractory_start = fire_indices[0] + 1
    refractory_end = fire_indices[0] + w_r  # 4 + 30 = 34
    assert not np.any(emitted[refractory_start:refractory_end]), (
        f"Alert fired during refractory window [{refractory_start}, {refractory_end})!"
    )

    # Next alert can only fire at index >= refractory_end
    assert fire_indices[1] >= refractory_end, (
        f"Second alert at {fire_indices[1]} fired before refractory elapsed ({refractory_end})!"
    )
    assert fire_indices[1] == refractory_end

    # Verify inter-alert intervals are all >= W_r
    intervals = np.diff(fire_indices)
    assert np.all(intervals >= w_r), f"Some alert intervals violate refractory hold-off: {intervals} < {w_r}"


def test_same_emitter_used_by_every_arm():
    """
    Protocol Amendment 4 Section 1.3:
    The alert emitter is standardized and shared universally across all arms.
    Verifies that Arm 1 and Arm 2 yield results matching direct emitter.emit(raw_mask).
    """
    p_sec = 10.0
    r_sec = 60.0
    step_sec = 2.0
    emitter = StandardAlertEmitter(p_persist_sec=p_sec, r_refractory_sec=r_sec, step_sec=step_sec)

    n_windows = 120
    # Construct a synthetic HR sequence with bursts of tachycardia
    hr = np.full(n_windows, 70.0)
    # Burst 1: 3 windows above 120 (6s) -> should be suppressed (P=10s)
    hr[10:13] = 130.0
    # Burst 2: 7 windows above 120 (14s) -> should fire once at window 20+5-1 = 24
    hr[20:27] = 135.0
    # Burst 3: inside refractory of burst 2 (e.g. at window 35) -> should be suppressed
    hr[35:45] = 140.0
    # Burst 4: after refractory (window 65 onwards) -> should fire at window 65+5-1 = 69
    hr[65:75] = 130.0

    enmo = np.full(n_windows, 0.02)  # Low motion for Arm 2

    arm1 = Arm1FixedThreshold(tau_pop=120.0)
    out1 = arm1.predict(hr, emitter=emitter)

    # Test Arm 1 output matches direct emitter.emit
    expected_arm1_emitted = emitter.emit(out1.raw_alert_mask)
    np.testing.assert_array_equal(out1.alert_mask, expected_arm1_emitted)
    assert np.sum(out1.alert_mask) == 2  # exactly bursts 2 and 4
    assert out1.alert_mask[24]
    assert out1.alert_mask[69]

    # Test Arm 2 uses the exact same emitter
    arm2 = Arm2PersonalBaselineShrinkage(
        k=2.5,
        kappa_hours=1.0,
        mu_pop=70.0,
        sigma_pop=10.0,
        tau_floor=100.0,
    )
    out2 = arm2.predict(hr, enmo, emitter=emitter)

    expected_arm2_emitted = emitter.emit(out2.raw_alert_mask)
    np.testing.assert_array_equal(out2.alert_mask, expected_arm2_emitted)
