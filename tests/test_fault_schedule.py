"""
VitaSense AI - Unit Tests for Fault Schedule Engine (Protocol Amendment 3 Section 5)
Tests:
1. Determinism: identical seed produces bitwise identical fault placement and values.
2. Zero Overlap with Injected Episodes: episodes are 100% protected and untouched.
3. Duty Cycles Within Tolerance:
   - Regime A: ~10% total faulted background time (8% - 13% tolerance)
   - Regime B: ~25-30% total faulted background time (23% - 35% tolerance)
4. Condition 0: No-Fault produces 0.0% faulted time and bitwise identity.
"""

import numpy as np
import pytest
from vitasense.benchmarks.fault_schedule import (
    FaultRegime,
    apply_fault_schedule,
)


@pytest.fixture
def sample_hr_stream():
    """Constructs a realistic 5000-window (10,000s) HR stream with 4 injected episodes."""
    n_windows = 5000
    step_sec = 2.0
    rng = np.random.default_rng(1234)
    hr = rng.normal(72.0, 5.0, size=n_windows)

    # 4 non-overlapping injected episodes
    injected_episodes = [
        {"episode_id": 1, "start_sec": 200.0, "end_sec": 280.0},
        {"episode_id": 2, "start_sec": 1500.0, "end_sec": 1580.0},
        {"episode_id": 3, "start_sec": 3000.0, "end_sec": 3090.0},
        {"episode_id": 4, "start_sec": 7000.0, "end_sec": 7100.0},
    ]

    for ep in injected_episodes:
        w_s = int(ep["start_sec"] / step_sec)
        w_e = int(ep["end_sec"] / step_sec)
        hr[w_s : w_e + 1] = 125.0

    return hr, injected_episodes, step_sec


def test_fault_schedule_determinism(sample_hr_stream):
    """Protocol Amendment 3 Section 5: Fault schedule must be 100% deterministic given seed."""
    hr, episodes, step_sec = sample_hr_stream

    res1 = apply_fault_schedule(hr, episodes, regime=FaultRegime.REGIME_A, seed=42, step_sec=step_sec)
    res2 = apply_fault_schedule(hr, episodes, regime=FaultRegime.REGIME_A, seed=42, step_sec=step_sec)

    # Assert bitwise equality of outputs
    np.testing.assert_array_equal(res1.fault_types, res2.fault_types)
    np.testing.assert_array_equal(res1.fault_mask, res2.fault_mask)
    np.testing.assert_array_equal(
        np.nan_to_num(res1.hr_faulted, nan=-999.0),
        np.nan_to_num(res2.hr_faulted, nan=-999.0),
    )

    # Different seed must alter placement
    res_diff = apply_fault_schedule(hr, episodes, regime=FaultRegime.REGIME_A, seed=99, step_sec=step_sec)
    assert not np.array_equal(res1.fault_mask, res_diff.fault_mask)


def test_fault_schedule_no_overlap_with_injected_episodes(sample_hr_stream):
    """
    Protocol Amendment 3 Section 5.4:
    Faults NEVER overlap active synthetic tachycardia episodes.
    Injected episode HR values must be strictly untouched.
    """
    hr, episodes, step_sec = sample_hr_stream

    for regime in [FaultRegime.REGIME_A, FaultRegime.REGIME_B]:
        res = apply_fault_schedule(hr, episodes, regime=regime, seed=42, step_sec=step_sec)

        for ep in episodes:
            w_s = int(ep["start_sec"] / step_sec)
            w_e = int(ep["end_sec"] / step_sec)

            # Injected episode slice
            ep_slice_mask = res.fault_mask[w_s : w_e + 1]
            ep_slice_types = res.fault_types[w_s : w_e + 1]
            ep_slice_hr = res.hr_faulted[w_s : w_e + 1]
            orig_slice_hr = hr[w_s : w_e + 1]

            assert not np.any(ep_slice_mask), f"Fault overlapped episode {ep['episode_id']} in {regime}!"
            assert np.all(ep_slice_types == "F0_CLEAN"), f"Non-clean fault type in episode {ep['episode_id']}!"
            np.testing.assert_array_equal(ep_slice_hr, orig_slice_hr, err_msg=f"Episode HR altered in {regime}!")


def test_fault_schedule_duty_cycles_within_tolerance(sample_hr_stream):
    """
    Protocol Amendment 3 Section 5.2:
    - Regime A: ~10% total faulted background time (8% - 13% tolerance)
    - Regime B: ~25-30% total faulted background time (23% - 35% tolerance)
    """
    hr, episodes, step_sec = sample_hr_stream

    # Test Regime A
    res_a = apply_fault_schedule(hr, episodes, regime=FaultRegime.REGIME_A, seed=42, step_sec=step_sec)
    assert 0.08 <= res_a.fault_duty_fraction <= 0.13, (
        f"Regime A duty cycle {res_a.fault_duty_fraction:.1%} outside ~10% tolerance [8%, 13%]"
    )
    # Check individual faults are non-empty
    for ft in ["F1_GAPS", "F2_STALE", "F3_DUPL", "F4_SPIKE", "F5_DRIFT", "F6_UNIT"]:
        assert res_a.fault_disaggregated_windows.get(ft, 0) > 0, f"Regime A missing fault {ft}!"

    # Test Regime B
    res_b = apply_fault_schedule(hr, episodes, regime=FaultRegime.REGIME_B, seed=42, step_sec=step_sec)
    assert 0.23 <= res_b.fault_duty_fraction <= 0.35, (
        f"Regime B duty cycle {res_b.fault_duty_fraction:.1%} outside ~25-30% tolerance [23%, 35%]"
    )
    for ft in ["F1_GAPS", "F2_STALE", "F3_DUPL", "F4_SPIKE", "F5_DRIFT", "F6_UNIT"]:
        assert res_b.fault_disaggregated_windows.get(ft, 0) > 0, f"Regime B missing fault {ft}!"


def test_no_fault_condition(sample_hr_stream):
    """Condition 0: No-Fault produces 0% faulted time and bitwise identity."""
    hr, episodes, step_sec = sample_hr_stream

    res = apply_fault_schedule(hr, episodes, regime=FaultRegime.NO_FAULT, seed=42, step_sec=step_sec)
    assert res.fault_duty_fraction == 0.0
    assert not np.any(res.fault_mask)
    assert np.all(res.fault_types == "F0_CLEAN")
    np.testing.assert_array_equal(res.hr_faulted, hr)
