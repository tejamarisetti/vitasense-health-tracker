"""
Canonical Ground Truth Event Prevalence Module
VitaSense AI - Protocol Section 3.1 & Amendment 1

Provides unified, rigorously validated functions for:
- Computing ENMO (Euclidean Norm Minus One) with unit safety and moving average.
- Aligning 4 Hz protocol activity tags to 8s/2s shifted label windows.
- Detecting continuous physiological and kinematic events.
- Computing ground-truth event prevalence across wearable datasets.
"""

from typing import Dict, List, Optional, Set, Tuple, Any
import numpy as np


RESTING_ACTIVITY_CODES: Set[int] = {1, 5, 6, 8}  # BASELINE, DRIVING, LUNCH, WORKING


def compute_enmo(
    acc_wrist: np.ndarray,
    fs_acc: float = 32.0,
    step_sec: float = 2.0,
    ma_sec: float = 10.0,
    n_windows: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute ENMO dynamic energy from wrist 3D accelerometer data.

    ENMO(t) = max(0, ||a(t)|| - 1.0g)

    Parameters
    ----------
    acc_wrist : np.ndarray, shape (N, 3)
        Raw 3-axis accelerometer values. Handled defensively: if median norm > 10.0,
        values are assumed to be in Empatica raw 1/64g units and scaled by 1/64;
        otherwise values are assumed to already be in units of g.
    fs_acc : float
        Sampling frequency of accelerometer in Hz (nominal 32 Hz).
    step_sec : float
        Window step size in seconds (nominal 2.0 s).
    ma_sec : float
        Moving average smoothing window in seconds (nominal 10.0 s).
    n_windows : int, optional
        Target number of label windows to match.

    Returns
    -------
    enmo_step : np.ndarray
        Mean ENMO per step_sec window.
    enmo_ma : np.ndarray
        Moving-average smoothed ENMO matching n_windows.
    """
    acc = np.asarray(acc_wrist, dtype=float)
    if acc.ndim != 2 or acc.shape[1] != 3:
        raise ValueError(f"acc_wrist must have shape (N, 3), got {acc.shape}")

    # Explicit check against dataset specifications:
    # Per PPG-DaLiA readme.pdf (Section III.2 and Section III.3), wrist ACC in SX.pkl is provided
    # in units of g with Empatica E4 hardware sensor range [-2.0, +2.0]g (raw ACC.csv is in 1/64g).
    acc_min = float(np.nanmin(acc))
    acc_max = float(np.nanmax(acc))
    if acc_min < -3.0 or acc_max > 3.0:
        raise ValueError(
            f"Wrist accelerometer values outside expected physical range [-2.0, +2.0]g: "
            f"min={acc_min:.2f}g, max={acc_max:.2f}g. "
            f"Data must be in units of g (as provided in PPG-DaLiA SX.pkl), not raw unscaled integer counts."
        )

    norms = np.linalg.norm(acc, axis=1)
    enmo_instant = np.maximum(0.0, norms - 1.0)

    samples_per_step = int(round(step_sec * fs_acc))
    if samples_per_step <= 0:
        raise ValueError("samples_per_step must be positive")

    total_steps = int(np.ceil(len(enmo_instant) / samples_per_step))
    if n_windows is not None:
        total_steps = n_windows

    step_vals = []
    for i in range(total_steps):
        s_idx = i * samples_per_step
        e_idx = s_idx + samples_per_step
        if s_idx < len(enmo_instant):
            chunk = enmo_instant[s_idx:min(e_idx, len(enmo_instant))]
            step_vals.append(float(np.mean(chunk)))
        else:
            step_vals.append(0.0)

    enmo_step = np.array(step_vals, dtype=float)

    # Moving average over ma_sec using edge padding to avoid boundary zero-decay
    k = max(1, int(round(ma_sec / step_sec)))
    if k > 1 and len(enmo_step) >= k:
        from scipy.ndimage import uniform_filter1d
        enmo_ma = uniform_filter1d(enmo_step, size=k, mode="nearest")
    else:
        enmo_ma = enmo_step.copy()

    return enmo_step, enmo_ma


def align_activity_to_windows(
    activity: np.ndarray,
    n_windows: int,
    fs_act: float = 4.0,
    step_sec: float = 2.0,
    window_sec: float = 8.0,
    method: str = "midpoint",
) -> np.ndarray:
    """
    Align a 4 Hz activity stream to 8-second / 2-second shifted label windows.

    Parameters
    ----------
    activity : np.ndarray
        Activity codes sampled at fs_act Hz.
    n_windows : int
        Number of label windows.
    fs_act : float
        Sampling frequency of activity stream (nominal 4 Hz).
    step_sec : float
        Window shift in seconds (nominal 2.0 s).
    window_sec : float
        Window length in seconds (nominal 8.0 s).
    method : str
        'midpoint' (evaluates activity at window center t = i*step + window/2)
        or 'mode' (majority activity across the 8s window span).

    Returns
    -------
    act_aligned : np.ndarray of shape (n_windows,), dtype int
    """
    act = np.asarray(activity).flatten()
    aligned = np.zeros(n_windows, dtype=int)

    for i in range(n_windows):
        t_start = i * step_sec
        t_end = t_start + window_sec
        if method == "midpoint":
            t_mid = t_start + 0.5 * window_sec
            idx = min(len(act) - 1, int(round(t_mid * fs_act)))
            aligned[i] = int(round(act[idx]))
        elif method == "mode":
            s_idx = min(len(act) - 1, int(round(t_start * fs_act)))
            e_idx = min(len(act), max(s_idx + 1, int(round(t_end * fs_act))))
            vals, counts = np.unique(np.round(act[s_idx:e_idx]).astype(int), return_counts=True)
            aligned[i] = vals[np.argmax(counts)]
        else:
            raise ValueError(f"Unknown alignment method: {method}")

    return aligned


def find_continuous_events(
    condition_series: np.ndarray,
    step_sec: float = 2.0,
    min_duration_sec: float = 30.0,
) -> List[Tuple[int, int, float]]:
    """
    Identify continuous intervals where condition_series is True for >= min_duration_sec.

    Parameters
    ----------
    condition_series : np.ndarray of bool
    step_sec : float
        Duration of each discrete step/window in seconds.
    min_duration_sec : float
        Minimum continuous persistence duration required.

    Returns
    -------
    List of tuples (start_idx, end_idx, duration_seconds).
    """
    cond = np.asarray(condition_series, dtype=bool)
    min_windows = int(np.ceil(min_duration_sec / step_sec))
    events: List[Tuple[int, int, float]] = []

    in_event = False
    start_idx = 0

    for i, val in enumerate(cond):
        if val and not in_event:
            in_event = True
            start_idx = i
        elif not val and in_event:
            in_event = False
            duration = (i - start_idx) * step_sec
            if (i - start_idx) >= min_windows:
                events.append((start_idx, i - 1, duration))

    if in_event:
        duration = (len(cond) - start_idx) * step_sec
        if (len(cond) - start_idx) >= min_windows:
            events.append((start_idx, len(cond) - 1, duration))

    return events


def compute_subject_prevalence(
    data: Dict[str, Any],
    subject_id: str,
    theta_rest: float = 0.05,
    t_persist: float = 30.0,
    step_sec: float = 2.0,
    window_sec: float = 8.0,
    resting_activities: Optional[Set[int]] = None,
) -> Dict[str, Any]:
    """
    Compute ground truth event prevalence for a single subject under Amendment 1.

    Parameters
    ----------
    data : dict
        Loaded subject dictionary from PPG-DaLiA SX.pkl.
    subject_id : str
        Subject identifier (e.g. 'S1').
    theta_rest : float
        Resting ENMO threshold in g (nominal 0.05g).
    t_persist : float
        Persistence duration in seconds (nominal 30.0s).
    step_sec : float
        Window shift in seconds (2.0s).
    window_sec : float
        Window length in seconds (8.0s).
    resting_activities : Set[int], optional
        Set of resting/sedentary activity codes (default: {1, 5, 6, 8}).

    Returns
    -------
    dict of prevalence metrics.
    """
    if resting_activities is None:
        resting_activities = RESTING_ACTIVITY_CODES

    labels = np.asarray(data["label"]).flatten()
    activity = np.asarray(data["activity"]).flatten()
    acc_wrist = data["signal"]["wrist"]["ACC"]
    n_windows = len(labels)
    total_time_min = (n_windows * step_sec) / 60.0

    # 1. ENMO dynamic energy
    _, enmo_10s = compute_enmo(
        acc_wrist=acc_wrist,
        fs_acc=32.0,
        step_sec=step_sec,
        ma_sec=10.0,
        n_windows=n_windows,
    )

    # 2. Activity alignment
    act_aligned = align_activity_to_windows(
        activity=activity,
        n_windows=n_windows,
        fs_act=4.0,
        step_sec=step_sec,
        window_sec=window_sec,
        method="midpoint",
    )

    # 3. Personal baseline resting HR during BASELINE (activity == 1)
    baseline_mask = (act_aligned == 1)
    if np.sum(baseline_mask) >= 10:
        mu_rest = float(np.mean(labels[baseline_mask]))
        std_rest = float(np.std(labels[baseline_mask], ddof=1))
    else:
        mu_rest = 70.0
        std_rest = 5.0

    tau_i = max(100.0, mu_rest + 2.5 * std_rest)

    # 4. Resting context: resting activity AND kinematic stillness (ENMO <= theta_rest)
    is_resting = np.isin(act_aligned, list(resting_activities)) & (enmo_10s <= theta_rest)
    resting_min = float(np.sum(is_resting) * step_sec / 60.0)

    # 5. Physiological tachycardia
    is_tachy = (labels > tau_i)

    # 6. Joint condition
    joint_alert = is_resting & is_tachy

    amend1_events = find_continuous_events(
        condition_series=joint_alert,
        step_sec=step_sec,
        min_duration_sec=t_persist,
    )
    uncontext_events = find_continuous_events(
        condition_series=is_tachy,
        step_sec=step_sec,
        min_duration_sec=t_persist,
    )

    event_time_min = float(sum(e[2] for e in amend1_events) / 60.0)

    return {
        "subject": subject_id,
        "total_min": total_time_min,
        "resting_min": resting_min,
        "pct_resting": (resting_min / total_time_min) * 100.0 if total_time_min > 0 else 0.0,
        "mu_rest": mu_rest,
        "std_rest": std_rest,
        "tau_i": tau_i,
        "uncontext_events": len(uncontext_events),
        "amend1_events": len(amend1_events),
        "event_time_min": event_time_min,
    }
