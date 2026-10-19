"""
VitaSense AI - Unit Tests for Benchmark Scoring Module (Amendment 3)
Tests event-level TP/FN/delay, buffered natural event exclusion, fault-window false alerts,
coverage tracking, and fault-disaggregated false alert rates with hand-computed expectations.
"""

import numpy as np
import pytest
from vitasense.benchmarks.scoring import (
    InjectedInterval,
    EventScoringResult,
    AlertRateResult,
    BenchmarkScoringResult,
    score_alert_stream,
)


def test_hand_computed_event_scoring_and_delays():
    """
    Hand-computed test case:
    Total time: 1000s (500 windows at 2s step, t = 0, 2, ..., 998).
    Injected episodes:
      - Ep 1: [100.0, 200.0]s (windows 50..100)
      - Ep 2: [300.0, 400.0]s (windows 150..200)
      - Ep 3: [500.0, 600.0]s (windows 250..300)

    Alerts:
      - t = 110.0s (w=55): inside Ep 1 -> TP, delay = 10.0s
      - t = 120.0s (w=60): inside Ep 1 -> second alert in same ep; does not double-count TP, delay is still 10.0s
      - (Ep 2 has NO alerts) -> FN
      - t = 500.0s (w=250): inside Ep 3 at onset -> TP, delay = 0.0s

    Expectations:
      - TP = 2, FN = 1
      - Recall = 2/3 = ~0.6667
      - Delays = (10.0, 0.0)
      - Mean delay = 5.0s
      - Median delay = 5.0s
      - Detected IDs: (1, 3)
      - Missed IDs: (2,)
    """
    n_windows = 500
    step_sec = 2.0
    alert_mask = np.zeros(n_windows, dtype=bool)

    # Set alerts
    alert_mask[55] = True   # t = 110s
    alert_mask[60] = True   # t = 120s
    alert_mask[250] = True  # t = 500s

    episodes = [
        {"start_sec": 100.0, "end_sec": 200.0, "episode_id": 1},
        {"start_sec": 300.0, "end_sec": 400.0, "episode_id": 2},
        {"start_sec": 500.0, "end_sec": 600.0, "episode_id": 3},
    ]

    res = score_alert_stream(
        alert_mask=alert_mask,
        injected_episodes=episodes,
        natural_events=[],
        step_sec=step_sec,
        subject_id="S_TEST",
    )

    ev = res.event_scoring
    assert ev.n_injected_episodes == 3
    assert ev.true_positives == 2
    assert ev.false_negatives == 1
    assert pytest.approx(ev.recall, rel=1e-4) == 2.0 / 3.0
    assert ev.delays_sec == (10.0, 0.0)
    assert pytest.approx(ev.mean_delay_sec, rel=1e-4) == 5.0
    assert pytest.approx(ev.median_delay_sec, rel=1e-4) == 5.0
    assert ev.detected_episode_ids == (1, 3)
    assert ev.missed_episode_ids == (2,)


def test_hand_computed_false_alerts_and_natural_buffering():
    """
    Hand-computed test case for Amendment 3 alert accounting:
    Total time: 1000s (500 windows at 2s step, t = 0..998s).
    Total hours = 1000 / 3600 = 0.27777... hr.

    Injected episode:
      - Ep 1: [100.0, 200.0]s (51 windows: 50..100)

    Natural event:
      - Nat 1: [800.0, 860.0]s (windows 400..430)
      - With +/- 30s buffer: [770.0, 890.0]s (windows 385..445, 61 windows)

    Total non-event windows = 500 - 51 (injected) - 61 (natural buffered) = 388 windows.
    Non-event time = 388 * 2.0 = 776.0s = 776 / 3600 = 0.21555... hr.

    Alert placements:
      - t = 110s (w=55): inside Ep 1 -> true alert (1)
      - t = 780s (w=390): inside natural buffer (770-800s) -> natural alert (1)
      - t = 850s (w=425): inside natural event core -> natural alert (2)
      - t = 880s (w=440): inside natural buffer (860-890s) -> natural alert (3)
      - t = 20s  (w=10):  outside all events -> clean false alert (1)
      - t = 600s (w=300): outside all events -> clean false alert (2)
      - t = 950s (w=475): outside all events -> clean false alert (3)

    Expectations:
      - total_alerts = 7
      - true_alerts = 1
      - natural_alerts = 3
      - false_alerts = 3
      - non_event_hours = 776 / 3600 = 0.21555...
      - false_alerts_per_hour = 3 / (776 / 3600) = 3 * 3600 / 776 = 13.9175...
    """
    n_windows = 500
    step_sec = 2.0
    alert_mask = np.zeros(n_windows, dtype=bool)

    # Injected alert
    alert_mask[55] = True

    # Natural alerts (core + buffer)
    alert_mask[390] = True
    alert_mask[425] = True
    alert_mask[440] = True

    # Clean false alerts
    alert_mask[10] = True
    alert_mask[300] = True
    alert_mask[475] = True

    episodes = [{"start_sec": 100.0, "end_sec": 200.0, "episode_id": 1}]
    natural = [{"start_sec": 800.0, "end_sec": 860.0}]

    res = score_alert_stream(
        alert_mask=alert_mask,
        injected_episodes=episodes,
        natural_events=natural,
        step_sec=step_sec,
        natural_buffer_sec=30.0,
    )

    ar = res.alert_rate
    assert ar.total_alerts == 7
    assert ar.true_alerts == 1
    assert ar.natural_alerts == 3
    assert ar.false_alerts == 3
    expected_non_event_h = 776.0 / 3600.0
    assert pytest.approx(ar.non_event_hours, rel=1e-5) == expected_non_event_h
    expected_fa_hr = 3.0 / expected_non_event_h
    assert pytest.approx(ar.false_alerts_per_hour, rel=1e-5) == expected_fa_hr


def test_fault_windows_count_as_false_alerts_and_disaggregation():
    """
    Amendment 3 Rule:
    Alerts occurring inside fault windows (outside injected episodes & natural buffer)
    ARE COUNTED AS FALSE ALERTS (not excluded).
    Also checks fault-type disaggregated metrics.
    """
    n_windows = 400
    step_sec = 2.0
    alert_mask = np.zeros(n_windows, dtype=bool)
    fault_types = ["F0"] * n_windows  # Default: no fault

    # Inject a fault window for F4_SPIKE at w=100..109 (20s)
    for w in range(100, 110):
        fault_types[w] = "F4_SPIKE"

    # Inject a fault window for F2_STALE at w=200..214 (30s)
    for w in range(200, 215):
        fault_types[w] = "F2_STALE"

    # No injected episodes or natural events
    # Place an alert inside F4_SPIKE (w=105)
    alert_mask[105] = True
    # Place two alerts inside F2_STALE (w=202, w=208)
    alert_mask[202] = True
    alert_mask[208] = True
    # Place one alert in clean F0 background (w=50)
    alert_mask[50] = True

    res = score_alert_stream(
        alert_mask=alert_mask,
        injected_episodes=[],
        natural_events=[],
        step_sec=step_sec,
        fault_types=fault_types,
    )

    ar = res.alert_rate
    # All 4 alerts must count as false alerts
    assert ar.false_alerts == 4
    assert ar.total_alerts == 4

    # Disaggregated counts
    assert ar.fault_disaggregated_fa["F4_SPIKE"] == 1
    assert ar.fault_disaggregated_fa["F2_STALE"] == 2
    assert ar.fault_disaggregated_fa["F0"] == 1

    # Disaggregated hours
    h_f4 = 10 * 2.0 / 3600.0
    h_f2 = 15 * 2.0 / 3600.0
    h_f0 = (400 - 10 - 15) * 2.0 / 3600.0
    assert pytest.approx(ar.fault_disaggregated_hours["F4_SPIKE"], rel=1e-5) == h_f4
    assert pytest.approx(ar.fault_disaggregated_hours["F2_STALE"], rel=1e-5) == h_f2
    assert pytest.approx(ar.fault_disaggregated_hours["F0"], rel=1e-5) == h_f0

    # Disaggregated FA/hr
    assert pytest.approx(ar.fault_disaggregated_fa_per_hour["F4_SPIKE"], rel=1e-5) == 1.0 / h_f4
    assert pytest.approx(ar.fault_disaggregated_fa_per_hour["F2_STALE"], rel=1e-5) == 2.0 / h_f2
    assert pytest.approx(ar.fault_disaggregated_fa_per_hour["F0"], rel=1e-5) == 1.0 / h_f0


def test_coverage_computation():
    """Verify coverage calculation when arm abstains."""
    n_windows = 100
    alert_mask = np.zeros(n_windows, dtype=bool)
    abstain_mask = np.zeros(n_windows, dtype=bool)

    # 20 abstained windows
    abstain_mask[10:30] = True

    res = score_alert_stream(
        alert_mask=alert_mask,
        injected_episodes=[],
        abstain_mask=abstain_mask,
    )

    # 80 assessed out of 100 -> 0.80 coverage
    assert pytest.approx(res.coverage, rel=1e-5) == 0.80

    # Default without abstain_mask is 1.0
    res_default = score_alert_stream(
        alert_mask=alert_mask,
        injected_episodes=[],
    )
    assert res_default.coverage == 1.0
