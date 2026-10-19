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
