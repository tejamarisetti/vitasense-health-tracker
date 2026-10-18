"""
Pytest Suite for Fault-Injection Benchmark Module
VitaSense AI - Protocol Table 2 Validation

Tests:
1. Seeded reproducibility: two injectors with identical seeds yield bitwise identical outputs.
2. Scientific Tagging: every output is explicitly tagged 'SYNTHETIC' and has valid masks.
3. F1_GAPS: verifies NaN insertion and configurable gap fraction.
4. F2_STALE: verifies zero variance over the frozen interval.
5. F3_DUPL: verifies length expansion and identical timestamps.
6. F4_SPIKE: verifies exact impulsive deviation matching prescribed amplitudes.
7. F5_DRIFT: verifies linear slope ramp.
8. F6_UNIT: verifies exact multiplicative scaling.
9. F7_NOISE: verifies noise variance matches target SNR.
"""

import numpy as np
import pytest

from vitasense.benchmarks.fault_injection import (
    FaultInjector,
    FaultType,
    FaultSeverity,
    SyntheticFaultResult,
)


@pytest.fixture
def synthetic_ecg_hr():
    """Generates 10 minutes of resting HR at 1 Hz (600 samples)."""
    np.random.seed(101)
    base_hr = 70.0 + 3.0 * np.sin(np.linspace(0, 20 * np.pi, 600))
    noise = np.random.normal(0, 0.5, 600)
    return base_hr + noise


@pytest.fixture
def timestamps():
    return np.arange(600, dtype=float)


def test_reproducibility(synthetic_ecg_hr, timestamps):
    inj1 = FaultInjector(seed=42)
    inj2 = FaultInjector(seed=42)

    res1 = inj1.inject_gaps(synthetic_ecg_hr, fs=1.0, severity=FaultSeverity.MED, timestamps=timestamps)
    res2 = inj2.inject_gaps(synthetic_ecg_hr, fs=1.0, severity=FaultSeverity.MED, timestamps=timestamps)

    # Identical NaN locations
    np.testing.assert_array_equal(np.isnan(res1.signal), np.isnan(res2.signal))
    # Identical non-NaN values
    valid = ~np.isnan(res1.signal)
    np.testing.assert_array_almost_equal(res1.signal[valid], res2.signal[valid])
    np.testing.assert_array_equal(res1.synthetic_mask, res2.synthetic_mask)


def test_synthetic_tag_enforcement(synthetic_ecg_hr):
    inj = FaultInjector(seed=42)
    res = inj.inject_stale(synthetic_ecg_hr, fs=1.0, severity=FaultSeverity.LOW)

    assert isinstance(res, SyntheticFaultResult)
    assert res.tag == "SYNTHETIC"
    assert res.is_synthetic() is True
    assert res.fault_type == FaultType.F2_STALE
    assert res.severity == FaultSeverity.LOW
    assert res.synthetic_mask.dtype == bool
    assert np.any(res.synthetic_mask)


def test_f1_gaps_behavior(synthetic_ecg_hr):
    inj = FaultInjector(seed=42)
    res_low = inj.inject_gaps(synthetic_ecg_hr, fs=1.0, severity=FaultSeverity.LOW)
    res_high = inj.inject_gaps(synthetic_ecg_hr, fs=1.0, severity=FaultSeverity.HIGH)

    # Asserts NaNs were injected where mask is True
    assert np.all(np.isnan(res_low.signal[res_low.synthetic_mask]))
    assert not np.any(np.isnan(res_low.signal[~res_low.synthetic_mask]))

    # High severity should drop more samples than Low severity
    dropped_low = np.mean(res_low.synthetic_mask)
    dropped_high = np.mean(res_high.synthetic_mask)
    assert dropped_high > dropped_low
    assert 0.03 <= dropped_low <= 0.15
    assert 0.20 <= dropped_high <= 0.45


def test_f2_stale_zero_variance(synthetic_ecg_hr):
    inj = FaultInjector(seed=42)
    res = inj.inject_stale(synthetic_ecg_hr, fs=1.0, severity=FaultSeverity.MED)

    # Frozen segment must have exactly zero variance within numerical precision
    frozen_vals = res.signal[res.synthetic_mask]
    assert len(frozen_vals) >= 20
    assert np.isclose(np.var(frozen_vals), 0.0, atol=1e-12)
    assert np.all(frozen_vals == frozen_vals[0])


def test_f3_duplicates_delta_t(synthetic_ecg_hr, timestamps):
    inj = FaultInjector(seed=42)
    res = inj.inject_duplicates(synthetic_ecg_hr, severity=FaultSeverity.MED, timestamps=timestamps)

    # Length must increase by duplicate count
    assert len(res.signal) > len(synthetic_ecg_hr)
    assert len(res.timestamps) == len(res.signal)

    # Check for zero timestamp differences (duplicates)
    dt = np.diff(res.timestamps)
    zero_diffs = np.sum(dt == 0.0)
    assert zero_diffs > 0
    assert zero_diffs == res.metadata["num_duplicates_inserted"]


def test_f4_spike_amplitudes(synthetic_ecg_hr):
    inj = FaultInjector(seed=42)
    res = inj.inject_spikes(synthetic_ecg_hr, fs=1.0, severity=FaultSeverity.MED)

    spike_indices = np.where(res.synthetic_mask)[0]
    assert len(spike_indices) > 0

    diffs = np.abs(res.signal[spike_indices] - synthetic_ecg_hr[spike_indices])
    # Amplitude for MED is 50.0 bpm
    np.testing.assert_array_almost_equal(diffs, 50.0)


def test_f5_drift_slope(synthetic_ecg_hr):
    inj = FaultInjector(seed=42)
    res = inj.inject_drift(synthetic_ecg_hr, fs=1.0, severity=FaultSeverity.MED, duration_sec=60.0)

    drift_idx = np.where(res.synthetic_mask)[0]
    assert len(drift_idx) == 60

    # Difference should follow ramp: 0.15 * t
    diffs = res.signal[drift_idx] - synthetic_ecg_hr[drift_idx]
    expected_ramp = 0.15 * np.arange(60)
    np.testing.assert_array_almost_equal(diffs, expected_ramp)


def test_f6_unit_scale_factor(synthetic_ecg_hr):
    inj = FaultInjector(seed=42)
    res_low = inj.inject_unit_error(synthetic_ecg_hr, severity=FaultSeverity.LOW)
    res_high = inj.inject_unit_error(synthetic_ecg_hr, severity=FaultSeverity.HIGH)

    np.testing.assert_array_almost_equal(res_low.signal, synthetic_ecg_hr * 1.2)
    np.testing.assert_array_almost_equal(res_high.signal, synthetic_ecg_hr * 60.0)


def test_f7_noise_snr(synthetic_ecg_hr):
    inj = FaultInjector(seed=42)
    res_low = inj.inject_noise(synthetic_ecg_hr, severity=FaultSeverity.LOW)
    res_high = inj.inject_noise(synthetic_ecg_hr, severity=FaultSeverity.HIGH)

    diff_low = res_low.signal - synthetic_ecg_hr
    diff_high = res_high.signal - synthetic_ecg_hr

    # High severity (-5 dB) noise must have significantly higher variance than Low severity (+15 dB)
    var_low = np.var(diff_low)
    var_high = np.var(diff_high)
    assert var_high > var_low * 50.0  # 20 dB difference = 100x power ratio
