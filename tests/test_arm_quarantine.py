"""
VitaSense AI - Unit Tests for Arm Input Quarantine (Protocol Amendment 3 Section 4)
Verifies that alerting arms strictly reject prohibited inputs:
- Ground-truth activity labels (activity)
- Synthetic injector resting mask (is_resting)
- ECG-derived personal baseline threshold (tau_i)
- Injected episode ground-truth times/objects (injected_episodes, episodes)
"""

import numpy as np
import pytest
from vitasense.benchmarks.alerting_arms import (
    Arm1FixedThreshold,
    Arm2PersonalBaselineShrinkage,
    Arm3aKinematicGate,
    Arm3bTrustScoreGate,
    Arm3bNoMotionGate,
    validate_arm_inputs,
)



def test_validate_arm_inputs_quarantine():
    """Verify validate_arm_inputs raises TypeError on any prohibited keyword."""
    prohibited = ["activity", "is_resting", "tau_i", "injected_episodes", "episodes", "synthetic_mask"]
    for key in prohibited:
        with pytest.raises(TypeError, match="Prohibited input detected"):
            validate_arm_inputs(**{key: np.zeros(10)})

    # Allowed inputs must not raise
    validate_arm_inputs(hr_series=np.zeros(10), enmo_10s=np.zeros(10))


def test_arm1_quarantine_initialization():
    """Arm 1 must reject prohibited inputs during constructor."""
    with pytest.raises(TypeError, match="Prohibited input detected"):
        Arm1FixedThreshold(tau_pop=100.0, tau_i=105.0)

    with pytest.raises(TypeError, match="Prohibited input detected"):
        Arm1FixedThreshold(tau_pop=100.0, activity=np.ones(10))


def test_arm1_quarantine_predict():
    """Arm 1 must reject prohibited inputs during predict call."""
    arm = Arm1FixedThreshold(tau_pop=100.0)
    hr = np.full(50, 80.0)

    with pytest.raises(TypeError, match="Prohibited input detected"):
        arm.predict(hr, is_resting=np.ones(50, dtype=bool))

    with pytest.raises(TypeError, match="Prohibited input detected"):
        arm.predict(hr, tau_i=110.0)

    with pytest.raises(TypeError, match="Prohibited input detected"):
        arm.predict(hr, injected_episodes=[(10, 20)])

    # Permitted prediction must succeed
    out = arm.predict(hr)
    assert len(out.alert_mask) == 50
    assert not np.any(out.alert_mask)


def test_arm2_quarantine_initialization():
    """Arm 2 must reject prohibited inputs during constructor."""
    with pytest.raises(TypeError, match="Prohibited input detected"):
        Arm2PersonalBaselineShrinkage(k=2.5, tau_i=105.0)

    with pytest.raises(TypeError, match="Prohibited input detected"):
        Arm2PersonalBaselineShrinkage(k=2.5, is_resting=np.ones(10, dtype=bool))


def test_arm2_quarantine_predict():
    """Arm 2 must reject prohibited inputs during predict call."""
    arm = Arm2PersonalBaselineShrinkage(k=2.5, kappa_hours=1.0)
    hr = np.full(50, 80.0)
    enmo = np.full(50, 0.02)

    with pytest.raises(TypeError, match="Prohibited input detected"):
        arm.predict(hr, enmo, activity=np.ones(50))

    with pytest.raises(TypeError, match="Prohibited input detected"):
        arm.predict(hr, enmo, is_resting=np.ones(50, dtype=bool))

    with pytest.raises(TypeError, match="Prohibited input detected"):
        arm.predict(hr, enmo, tau_i=110.0)

    with pytest.raises(TypeError, match="Prohibited input detected"):
        arm.predict(hr, enmo, episodes=[])

    # Permitted prediction must succeed
    out = arm.predict(hr, enmo)
    assert len(out.alert_mask) == 50


def test_arm2_causality_future_spike_does_not_affect_past_tau():
    """
    Protocol Amendment 3 & 4 Verification:
    Assert that Arm 2's personal baseline threshold at time t uses strictly and exclusively
    windows strictly before t (indices 0 .. t-1).
    Feeding an acute future spike at window T_spike must NOT alter tau_i for any window t <= T_spike.
    """
    n_windows = 100
    hr_clean = np.full(n_windows, 70.0)
    enmo_clean = np.full(n_windows, 0.02)  # Low motion (calibrates)

    arm = Arm2PersonalBaselineShrinkage(
        k=2.5,
        kappa_hours=1.0,
        mu_pop=75.0,
        sigma_pop=15.0,
        tau_floor=100.0,
    )

    out_clean = arm.predict(hr_clean, enmo_clean)
    tau_clean = out_clean.threshold_series

    # Inject an acute spike of 180 bpm at window 40
    spike_idx = 40
    hr_spiked = hr_clean.copy()
    hr_spiked[spike_idx] = 180.0

    out_spiked = arm.predict(hr_spiked, enmo_clean)
    tau_spiked = out_spiked.threshold_series

    # Windows 0 through spike_idx MUST be bitwise identical
    # Window spike_idx uses windows 0..spike_idx-1, so it cannot be affected by hr_spiked[spike_idx]
    np.testing.assert_array_equal(
        tau_spiked[:spike_idx + 1],
        tau_clean[:spike_idx + 1],
        err_msg="Future spike corrupted past or current threshold values! Violates causal baseline rule.",
    )

    assert tau_spiked[spike_idx + 1] > tau_clean[spike_idx + 1]


def test_arm3a_quarantine():
    """Arm 3a must reject prohibited inputs during constructor and predict."""
    with pytest.raises(TypeError, match="Prohibited input detected"):
        Arm3aKinematicGate(theta_rest=0.05, tau_i=105.0)

    with pytest.raises(TypeError, match="Prohibited input detected"):
        Arm3aKinematicGate(theta_rest=0.05, activity=np.ones(10))

    arm = Arm3aKinematicGate(theta_rest=0.05)
    hr = np.full(50, 80.0)
    enmo = np.full(50, 0.02)

    with pytest.raises(TypeError, match="Prohibited input detected"):
        arm.predict(hr, enmo, is_resting=np.ones(50, dtype=bool))

    with pytest.raises(TypeError, match="Prohibited input detected"):
        arm.predict(hr, enmo, episodes=[])

    # Valid execution must succeed
    out = arm.predict(hr, enmo)
    assert len(out.alert_mask) == 50


def test_arm3b_quarantine():
    """Arm 3b must reject prohibited inputs during constructor and predict."""
    with pytest.raises(TypeError, match="Prohibited input detected"):
        Arm3bTrustScoreGate(theta_trust=0.70, tau_i=105.0)

    with pytest.raises(TypeError, match="Prohibited input detected"):
        Arm3bTrustScoreGate(theta_trust=0.70, activity=np.ones(10))

    arm = Arm3bTrustScoreGate(theta_trust=0.70)
    hr = np.full(50, 80.0)
    enmo = np.full(50, 0.02)
    trust = np.full(50, 0.85)

    with pytest.raises(TypeError, match="Prohibited input detected"):
        arm.predict(hr, enmo, trust, is_resting=np.ones(50, dtype=bool))

    with pytest.raises(TypeError, match="Prohibited input detected"):
        arm.predict(hr, enmo, trust, episodes=[])

    # Valid execution must succeed
    out = arm.predict(hr, enmo, trust)
    assert len(out.alert_mask) == 50


def test_arm3b_nomotion_quarantine():
    """Arm 3b-noMotion must reject prohibited inputs during constructor and predict."""
    with pytest.raises(TypeError, match="Prohibited input detected"):
        Arm3bNoMotionGate(theta_trust=0.70, tau_i=105.0)

    with pytest.raises(TypeError, match="Prohibited input detected"):
        Arm3bNoMotionGate(theta_trust=0.70, activity=np.ones(10))

    arm = Arm3bNoMotionGate(theta_trust=0.70)
    hr = np.full(50, 80.0)
    enmo = np.full(50, 0.02)
    trust_nomot = np.full(50, 0.85)

    with pytest.raises(TypeError, match="Prohibited input detected"):
        arm.predict(hr, enmo, trust_nomot, is_resting=np.ones(50, dtype=bool))

    with pytest.raises(TypeError, match="Prohibited input detected"):
        arm.predict(hr, enmo, trust_nomot, episodes=[])

    # Valid execution must succeed
    out = arm.predict(hr, enmo, trust_nomot)
    assert len(out.alert_mask) == 50

