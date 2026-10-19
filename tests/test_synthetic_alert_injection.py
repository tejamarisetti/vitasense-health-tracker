"""
Unit Tests for Synthetic Resting Tachycardia Injection
Protocol Section 8 (Amendment 2 Option (a)) - Frozen Protocol v2.0.0

Tests:
1. episode count (5 to 10 per subject)
2. HR range (105 to 135 bpm)
3. ramp rate (+2 to +4 bpm/s over 15s)
4. duration (plateau 45 to 120s, total 80 to 155s)
5. no injection outside resting segments
6. reproducibility (deterministic seeded output)
7. natural events are untouched
8. tag enforcement (SYNTHETIC / SYNTHETIC_RESTING_TACHYCARDIA)
9. minimum inter-episode gap (>= 60.0s across all 15 subjects)
"""

import pickle
from pathlib import Path
import numpy as np
import pytest
from vitasense.quality.event_prevalence import (
    compute_enmo,
    align_activity_to_windows,
    RESTING_ACTIVITY_CODES,
)
from vitasense.benchmarks.synthetic_alert_injection import (
    SyntheticTachycardiaInjector,
    SyntheticTachycardiaResult,
    InjectedEpisode,
)


@pytest.fixture
def synthetic_subject_data():
    """
    Creates a realistic synthetic subject recording:
    - 3000 windows (100 minutes at 2s step)
    - Active periods and resting periods
    - A natural tachycardia event during rest
    """
    n_windows = 3000
    step_sec = 2.0
    rng = np.random.default_rng(12345)

    # Base heart rate around 70 bpm with natural variability
    hr_series = 70.0 + 3.0 * np.sin(np.linspace(0, 20 * np.pi, n_windows)) + rng.normal(0, 1.0, n_windows)

    # Resting mask: 3 distinct resting blocks (each 500-800 windows = 16-26 min)
    is_resting = np.zeros(n_windows, dtype=bool)
    is_resting[200:800] = True    # 600 windows = 1200s (20 min)
    is_resting[1100:1600] = True  # 500 windows = 1000s (16.6 min)
    is_resting[2000:2700] = True  # 700 windows = 1400s (23.3 min)

    tau_i = 102.5

    # Introduce one natural resting tachycardia event in the first resting block (windows 300-330 = 60s)
    hr_series[300:330] = 115.0 + rng.normal(0, 0.5, 30)

    return {
        "hr_series": hr_series,
        "is_resting": is_resting,
        "tau_i": tau_i,
        "step_sec": step_sec,
        "natural_event_slice": slice(300, 330),
    }


def test_episode_count_and_tagging(synthetic_subject_data):
    """Verify episode count is within [5, 10] and tags are strictly SYNTHETIC."""
    injector = SyntheticTachycardiaInjector(seed=42)
    res = injector.inject(
        hr_series=synthetic_subject_data["hr_series"],
        is_resting=synthetic_subject_data["is_resting"],
        tau_i=synthetic_subject_data["tau_i"],
        subject_id="S_TEST",
    )

    assert isinstance(res, SyntheticTachycardiaResult)
    assert res.tag == "SYNTHETIC"
    assert res.is_synthetic()
    assert 5 <= len(res.episodes) <= 10

    for ep in res.episodes:
        assert isinstance(ep, InjectedEpisode)
        assert ep.tag == "SYNTHETIC"
        assert ep.event_type == "SYNTHETIC_RESTING_TACHYCARDIA"
        assert ep.is_synthetic is True


def test_hr_range_compliance(synthetic_subject_data):
    """Verify peak HR for every episode is within [105, 135] bpm."""
    injector = SyntheticTachycardiaInjector(seed=42)
    res = injector.inject(
        hr_series=synthetic_subject_data["hr_series"],
        is_resting=synthetic_subject_data["is_resting"],
        tau_i=synthetic_subject_data["tau_i"],
        subject_id="S_TEST",
    )

    for ep in res.episodes:
        assert 105.0 <= ep.peak_hr <= 135.0, f"Episode {ep.episode_id} peak HR {ep.peak_hr} out of [105, 135]"
        # Check plateau window values in the injected stream
        plat_start = ep.start_window + int(np.ceil(15.0 / 2.0))
        plat_end = ep.start_window + int(np.floor((15.0 + ep.plateau_duration_sec) / 2.0))
        plat_hr = res.hr_injected[plat_start:plat_end]
        assert np.all(plat_hr >= 105.0)
        assert np.all(plat_hr <= 135.0)


def test_ramp_rate_compliance(synthetic_subject_data):
    """Verify onset ramp rate is within [+2.0, +4.0] bpm/s over 15s."""
    injector = SyntheticTachycardiaInjector(seed=42)
    res = injector.inject(
        hr_series=synthetic_subject_data["hr_series"],
        is_resting=synthetic_subject_data["is_resting"],
        tau_i=synthetic_subject_data["tau_i"],
        subject_id="S_TEST",
    )

    for ep in res.episodes:
        assert 2.0 <= ep.ramp_rate_bpm_s <= 4.0, f"Episode {ep.episode_id} ramp rate {ep.ramp_rate_bpm_s} out of [2.0, 4.0]"


def test_duration_compliance(synthetic_subject_data):
    """Verify plateau duration in [45, 120]s and total duration in [80, 155]s."""
    injector = SyntheticTachycardiaInjector(seed=42)
    res = injector.inject(
        hr_series=synthetic_subject_data["hr_series"],
        is_resting=synthetic_subject_data["is_resting"],
        tau_i=synthetic_subject_data["tau_i"],
        subject_id="S_TEST",
    )

    for ep in res.episodes:
        assert 45.0 <= ep.plateau_duration_sec <= 120.0, f"Episode {ep.episode_id} plateau {ep.plateau_duration_sec}s out of [45, 120]"
        assert 80.0 <= ep.duration_sec <= 155.0, f"Episode {ep.episode_id} total duration {ep.duration_sec}s out of [80, 155]"


def test_no_injection_outside_resting_segments(synthetic_subject_data):
    """Verify 100% of injected windows occur strictly during resting segments."""
    injector = SyntheticTachycardiaInjector(seed=42)
    res = injector.inject(
        hr_series=synthetic_subject_data["hr_series"],
        is_resting=synthetic_subject_data["is_resting"],
        tau_i=synthetic_subject_data["tau_i"],
        subject_id="S_TEST",
    )

    is_resting = synthetic_subject_data["is_resting"]
    # Every True window in synthetic_mask must be True in is_resting
    assert np.all(is_resting[res.synthetic_mask]), "Synthetic window found outside resting segment!"

    # Signal outside synthetic windows must be untouched
    assert np.all(res.hr_injected[~res.synthetic_mask] == synthetic_subject_data["hr_series"][~res.synthetic_mask])


def test_reproducibility(synthetic_subject_data):
    """Verify that identical seed produces identical results."""
    inj1 = SyntheticTachycardiaInjector(seed=42)
    res1 = inj1.inject(
        hr_series=synthetic_subject_data["hr_series"],
        is_resting=synthetic_subject_data["is_resting"],
        tau_i=synthetic_subject_data["tau_i"],
        subject_id="S1",
    )

    inj2 = SyntheticTachycardiaInjector(seed=42)
    res2 = inj2.inject(
        hr_series=synthetic_subject_data["hr_series"],
        is_resting=synthetic_subject_data["is_resting"],
        tau_i=synthetic_subject_data["tau_i"],
        subject_id="S1",
    )

    assert np.array_equal(res1.hr_injected, res2.hr_injected)
    assert np.array_equal(res1.synthetic_mask, res2.synthetic_mask)
    assert len(res1.episodes) == len(res2.episodes)
    for e1, e2 in zip(res1.episodes, res2.episodes):
        assert e1.start_window == e2.start_window
        assert e1.end_window == e2.end_window
        assert np.isclose(e1.peak_hr, e2.peak_hr)
        assert np.isclose(e1.ramp_rate_bpm_s, e2.ramp_rate_bpm_s)


def test_natural_events_are_untouched(synthetic_subject_data):
    """Verify that natural tachycardia events are not overwritten or overlapped."""
    injector = SyntheticTachycardiaInjector(seed=42)
    res = injector.inject(
        hr_series=synthetic_subject_data["hr_series"],
        is_resting=synthetic_subject_data["is_resting"],
        tau_i=synthetic_subject_data["tau_i"],
        subject_id="S_TEST",
    )

    nat_slice = synthetic_subject_data["natural_event_slice"]
    # Natural event windows must NOT be marked synthetic
    assert not np.any(res.synthetic_mask[nat_slice]), "Synthetic injection overlapped with natural event!"

    # Values during natural event must be bit-for-bit identical to original
    assert np.array_equal(
        res.hr_injected[nat_slice],
        synthetic_subject_data["hr_series"][nat_slice]
    )


def test_error_when_no_resting_blocks():
    """Verify ValueError is raised if there are no eligible resting blocks."""
    injector = SyntheticTachycardiaInjector(seed=42)
    hr = np.full(500, 70.0)
    resting = np.zeros(500, dtype=bool)  # Zero resting time

    with pytest.raises(ValueError, match="No resting blocks of duration"):
        injector.inject(hr, resting, tau_i=100.0)


@pytest.mark.slow
def test_min_inter_episode_gap_on_all_15_subjects():
    """
    Protocol Amendment 3: Assert minimum inter-episode gap >= 60.0s between
    all consecutive injected episodes across all 15 subjects.
    Also verifies cohort total episode count is exactly 112.
    """
    data_dir = Path(__file__).resolve().parents[1] / "data" / "raw" / "ppg_dalia" / "extracted" / "PPG_FieldStudy"
    if not data_dir.exists():
        pytest.skip("PPG-DaLiA raw data directory not found.")

    injector = SyntheticTachycardiaInjector(seed=42)
    assert injector.min_inter_event_gap_sec == 60.0

    total_episodes = 0
    per_subject_counts = {}

    for i in range(1, 16):
        sid = f"S{i}"
        pkl_path = data_dir / sid / f"{sid}.pkl"
        if not pkl_path.exists():
            pytest.skip(f"Subject data {pkl_path} not found.")

        with open(pkl_path, "rb") as f:
            data = pickle.load(f, encoding="latin1")

        labels = np.asarray(data["label"]).flatten()
        activity = np.asarray(data["activity"]).flatten()
        acc = data["signal"]["wrist"]["ACC"]
        del data
        n_windows = len(labels)

        _, enmo_10s = compute_enmo(acc, n_windows=n_windows)
        del acc
        act_aligned = align_activity_to_windows(activity, n_windows=n_windows)
        del activity

        baseline_mask = (act_aligned == 1)
        if np.sum(baseline_mask) >= 10:
            mu_rest = float(np.mean(labels[baseline_mask]))
            std_rest = float(np.std(labels[baseline_mask], ddof=1))
        else:
            mu_rest = 70.0
            std_rest = 5.0
        tau_i = max(100.0, mu_rest + 2.5 * std_rest)

        is_resting = np.isin(act_aligned, list(RESTING_ACTIVITY_CODES)) & (enmo_10s <= 0.05)

        res = injector.inject(labels, is_resting, tau_i, subject_id=sid)
        episodes = res.episodes
        per_subject_counts[sid] = len(episodes)
        total_episodes += len(episodes)

        # Assert minimum inter-episode gap >= 60.0s between all consecutive episodes
        for k in range(len(episodes) - 1):
            ep_curr = episodes[k]
            ep_next = episodes[k + 1]
            gap_sec = ep_next.start_time_sec - ep_curr.end_time_sec
            gap_win = ep_next.start_window - ep_curr.end_window
            assert gap_sec >= 60.0, (
                f"{sid}: Gap between Episode {ep_curr.episode_id} (ends {ep_curr.end_time_sec}s) "
                f"and Episode {ep_next.episode_id} (starts {ep_next.start_time_sec}s) is {gap_sec:.1f}s < 60s"
            )
            assert gap_win >= 30, (
                f"{sid}: Gap windows between Episode {ep_curr.episode_id} and {ep_next.episode_id} is {gap_win} < 30"
            )

    # Subject-specific episode counts under T_gap = 60s
    assert per_subject_counts["S5"] == 4, f"Expected 4 episodes for S5, got {per_subject_counts['S5']}"
    assert per_subject_counts["S6"] == 4, f"Expected 4 episodes for S6, got {per_subject_counts['S6']}"
    assert total_episodes == 112, f"Expected 112 total episodes across 15 subjects under T_gap=60s, got {total_episodes}"

