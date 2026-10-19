"""
VitaSense AI - Benchmark Alerting Scoring & Evaluation Module
Protocol Section 3 & Section 4 (Amendment 3) - Standardized Alert Evaluation

Implements:
1. Event-Level Performance on Injected Synthetic Episodes:
   - True Positive (TP), False Negative (FN), and Detection Delay (seconds)
   - Event Recall = TP / (TP + FN)
2. False Alerts and False Alerts per Hour (FA/hr):
   - Defined strictly per Amendment 3: alerts occurring outside all injected episodes AND
     outside all natural events (expanded by +/- 30s buffer).
   - Alerts inside fault windows ARE counted as false alerts (not excluded).
   - Alerts inside natural events (+/- 30s buffer) are tracked separately as natural_alerts.
   - Non-event time strictly excludes both injected episodes and buffered natural events.
   - FA/hr = Clean False Alerts / Total Non-Event Hours.
3. Signal Coverage:
   - Fraction of evaluated windows where the system produced an assessment (did not abstain).
4. Disaggregated Fault-Type Reporting:
   - Tracks false alerts and FA/hr across individual fault types (F0=No-Fault, F1..F7).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple, Union, Any
import numpy as np


@dataclass(frozen=True)
class InjectedInterval:
    """Represents a target event interval in seconds."""
    start_sec: float
    end_sec: float
    episode_id: Optional[int] = None
    event_type: str = "SYNTHETIC"


@dataclass(frozen=True)
class EventScoringResult:
    """Event-level detection outcome for synthetic episodes."""
    n_injected_episodes: int
    true_positives: int
    false_negatives: int
    recall: float
    mean_delay_sec: Optional[float]
    median_delay_sec: Optional[float]
    delays_sec: Tuple[float, ...] = ()
    detected_episode_ids: Tuple[int, ...] = ()
    missed_episode_ids: Tuple[int, ...] = ()


@dataclass(frozen=True)
class AlertRateResult:
    """False alert rate accounting per Amendment 3."""
    total_alerts: int
    true_alerts: int            # Alerts inside synthetic episodes
    natural_alerts: int         # Alerts inside natural events (+/-30s buffer)
    false_alerts: int           # Alerts outside synthetic episodes AND outside natural events (+/-30s)
    total_hours: float
    non_event_hours: float
    false_alerts_per_hour: float
    fault_disaggregated_fa: Dict[str, int] = field(default_factory=dict)
    fault_disaggregated_hours: Dict[str, float] = field(default_factory=dict)
    fault_disaggregated_fa_per_hour: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class BenchmarkScoringResult:
    """Complete evaluation outcome for an alerting arm."""
    subject_id: Optional[str]
    event_scoring: EventScoringResult
    alert_rate: AlertRateResult
    coverage: float
    metadata: Dict[str, Any] = field(default_factory=dict)


def score_alert_stream(
    alert_mask: np.ndarray,
    injected_episodes: Sequence[Any],
    natural_events: Optional[Sequence[Any]] = None,
    step_sec: float = 2.0,
    abstain_mask: Optional[np.ndarray] = None,
    fault_types: Optional[Sequence[str]] = None,
    natural_buffer_sec: float = 30.0,
    subject_id: Optional[str] = None,
) -> BenchmarkScoringResult:
    """
    Evaluates an arm's binary alert mask against injected and natural event ground truth.

    Parameters
    ----------
    alert_mask : np.ndarray of bool
        Boolean array of length N_windows where True indicates an active alert.
    injected_episodes : Sequence of episode objects or dicts
        Must provide start_time_sec (or start_sec) and end_time_sec (or end_sec).
    natural_events : Sequence of event objects or dicts, optional
        Amendment 1 natural resting tachycardia events with start and end times in seconds.
    step_sec : float
        Time step per analysis window in seconds (nominal 2.0s).
    abstain_mask : np.ndarray of bool, optional
        Boolean array where True indicates the arm abstained / was unable to assess.
    fault_types : Sequence of str, optional
        Array of length N_windows assigning fault label (e.g. 'F0', 'F1', ..., 'F7') per window.
    natural_buffer_sec : float
        Temporal expansion buffer around natural events (nominal 30.0s).
    subject_id : str, optional
        Identifier of the evaluated subject.
    """
    alert_arr = np.asarray(alert_mask, dtype=bool)
    n_windows = len(alert_arr)
    timestamps = np.arange(n_windows, dtype=np.float64) * step_sec

    # 1. Standardize Injected Episodes
    parsed_injected: List[InjectedInterval] = []
    for idx, ep in enumerate(injected_episodes, start=1):
        if hasattr(ep, "start_time_sec") and hasattr(ep, "end_time_sec"):
            s = float(ep.start_time_sec)
            e = float(ep.end_time_sec)
            eid = getattr(ep, "episode_id", idx)
        elif isinstance(ep, dict):
            s = float(ep.get("start_time_sec", ep.get("start_sec", 0.0)))
            e = float(ep.get("end_time_sec", ep.get("end_sec", 0.0)))
            eid = ep.get("episode_id", idx)
        elif isinstance(ep, (tuple, list)) and len(ep) >= 2:
            s = float(ep[0])
            e = float(ep[1])
            eid = idx
        else:
            raise ValueError(f"Unrecognized episode format: {ep}")
        parsed_injected.append(InjectedInterval(start_sec=s, end_sec=e, episode_id=eid))

    # 2. Standardize Natural Events with Buffer
    parsed_natural_buffered: List[Tuple[float, float]] = []
    if natural_events is not None:
        for ev in natural_events:
            if hasattr(ev, "start_time_sec") and hasattr(ev, "end_time_sec"):
                s = float(ev.start_time_sec)
                e = float(ev.end_time_sec)
            elif isinstance(ev, dict):
                s = float(ev.get("start_time_sec", ev.get("start_sec", 0.0)))
                e = float(ev.get("end_time_sec", ev.get("end_sec", 0.0)))
            elif isinstance(ev, (tuple, list)) and len(ev) >= 2:
                s = float(ev[0])
                e = float(ev[1])
            else:
                continue
            parsed_natural_buffered.append((s - natural_buffer_sec, e + natural_buffer_sec))

    # 3. Classify Each Window as Injected, Natural-Buffered, or Non-Event
    is_injected_window = np.zeros(n_windows, dtype=bool)
    for ep in parsed_injected:
        # Window midpoint or timestamp within [s, e]
        w_mask = (timestamps >= ep.start_sec) & (timestamps <= ep.end_sec)
        is_injected_window |= w_mask

    is_natural_window = np.zeros(n_windows, dtype=bool)
    for s_buf, e_buf in parsed_natural_buffered:
        w_mask = (timestamps >= s_buf) & (timestamps <= e_buf)
        is_natural_window |= w_mask

    # Injected episodes take precedence over natural buffer in case of any overlap
    is_non_event_window = (~is_injected_window) & (~is_natural_window)

    # 4. Event-Level Injected Episode Scoring (TP, FN, Delay)
    delays: List[float] = []
    detected_ids: List[int] = []
    missed_ids: List[int] = []

    for ep in parsed_injected:
        ep_mask = (timestamps >= ep.start_sec) & (timestamps <= ep.end_sec)
        ep_alerts = np.where(ep_mask & alert_arr)[0]
        if len(ep_alerts) > 0:
            first_alert_idx = ep_alerts[0]
            first_alert_time = timestamps[first_alert_idx]
            delay = max(0.0, float(first_alert_time - ep.start_sec))
            delays.append(delay)
            if ep.episode_id is not None:
                detected_ids.append(ep.episode_id)
        else:
            if ep.episode_id is not None:
                missed_ids.append(ep.episode_id)

    tp_count = len(delays)
    fn_count = len(parsed_injected) - tp_count
    recall = float(tp_count / len(parsed_injected)) if parsed_injected else 0.0
    mean_delay = float(np.mean(delays)) if delays else None
    median_delay = float(np.median(delays)) if delays else None

    event_result = EventScoringResult(
        n_injected_episodes=len(parsed_injected),
        true_positives=tp_count,
        false_negatives=fn_count,
        recall=recall,
        mean_delay_sec=mean_delay,
        median_delay_sec=median_delay,
        delays_sec=tuple(delays),
        detected_episode_ids=tuple(detected_ids),
        missed_episode_ids=tuple(missed_ids),
    )

    # 5. Alert Accounting & FA/hr
    total_alerts = int(np.sum(alert_arr))
    true_alerts = int(np.sum(alert_arr & is_injected_window))
    natural_alerts = int(np.sum(alert_arr & (~is_injected_window) & is_natural_window))
    clean_false_alerts = int(np.sum(alert_arr & is_non_event_window))

    total_hours = float((n_windows * step_sec) / 3600.0)
    non_event_sec = float(np.sum(is_non_event_window) * step_sec)
    non_event_hours = float(non_event_sec / 3600.0)

    if non_event_hours > 0.0:
        fa_per_hour = float(clean_false_alerts / non_event_hours)
    else:
        fa_per_hour = 0.0

    # 6. Disaggregated Fault-Type Reporting
    fault_fa: Dict[str, int] = {}
    fault_hours: Dict[str, float] = {}
    fault_fa_rate: Dict[str, float] = {}

    if fault_types is not None:
        ft_arr = np.asarray(fault_types)
        unique_faults = sorted(list(set(ft_arr)))
        for ft in unique_faults:
            ft_mask = (ft_arr == ft) & is_non_event_window
            fa_in_ft = int(np.sum(alert_arr & ft_mask))
            h_in_ft = float(np.sum(ft_mask) * step_sec / 3600.0)
            rate_in_ft = float(fa_in_ft / h_in_ft) if h_in_ft > 0.0 else 0.0

            fault_fa[ft] = fa_in_ft
            fault_hours[ft] = h_in_ft
            fault_fa_rate[ft] = rate_in_ft

    alert_result = AlertRateResult(
        total_alerts=total_alerts,
        true_alerts=true_alerts,
        natural_alerts=natural_alerts,
        false_alerts=clean_false_alerts,
        total_hours=total_hours,
        non_event_hours=non_event_hours,
        false_alerts_per_hour=fa_per_hour,
        fault_disaggregated_fa=fault_fa,
        fault_disaggregated_hours=fault_hours,
        fault_disaggregated_fa_per_hour=fault_fa_rate,
    )

    # 7. Coverage Tracking
    if abstain_mask is not None:
        abstain_arr = np.asarray(abstain_mask, dtype=bool)
        assessed_windows = int(np.sum(~abstain_arr))
        coverage = float(assessed_windows / n_windows) if n_windows > 0 else 1.0
    else:
        coverage = 1.0

    return BenchmarkScoringResult(
        subject_id=subject_id,
        event_scoring=event_result,
        alert_rate=alert_result,
        coverage=coverage,
        metadata={
            "step_sec": step_sec,
            "n_windows": n_windows,
            "natural_buffer_sec": natural_buffer_sec,
        },
    )
