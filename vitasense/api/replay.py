"""
VitaSense AI - Replay Engine for Signal Lab
Reads ONLY from data/processed caches. No model training at runtime.
Complying with: "REPLAY: public dataset, not live"
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vitasense.benchmarks.fault_injection import (
    FaultInjector,
    FaultType,
    FaultSeverity,
)
from vitasense.quality.trust_score import RuleBasedTrustScorer

PROCESSED_DIR = ROOT / "data" / "processed"


def list_available_subjects() -> List[Dict[str, Any]]:
    """Lists all available subjects S1 to S15 with basic cache stats."""
    subjects = []
    ecg_cache_path = PROCESSED_DIR / "ecg_reference_cache.npz"
    ecg_data = np.load(ecg_cache_path) if ecg_cache_path.exists() else {}

    for i in range(1, 16):
        sid = f"S{i}"
        ppg_cache_path = PROCESSED_DIR / f"{sid}_ppg_cache.npz"
        if ppg_cache_path.exists():
            ppg_data = np.load(ppg_cache_path)
            n_win = int(ppg_data["n_windows"])
            dur_sec = n_win * 2.0
            subjects.append({
                "id": sid,
                "label": f"Subject {sid}",
                "n_windows": n_win,
                "duration_sec": dur_sec,
                "duration_min": round(dur_sec / 60.0, 1),
                "notice": "REPLAY: public dataset, not live",
            })
    return subjects


def get_replay_stream(
    subject: str = "S1",
    fault_type: str = "NONE",
    offset: int = 0,
    limit: int = 300,
) -> Dict[str, Any]:
    """
    Streams synchronized wrist-PPG HR, ECG reference HR, trust score, and ENMO
    from data/processed caches with optional SYNTHETIC fault injection.
    """
    sid = subject.upper()
    if sid not in [f"S{i}" for i in range(1, 16)]:
        sid = "S1"

    # Select cache file based on fault
    use_f7 = (fault_type == "F7_NOISE" or fault_type == "F7")
    cache_file = PROCESSED_DIR / (f"{sid}_f7_ppg_cache.npz" if use_f7 else f"{sid}_ppg_cache.npz")
    if not cache_file.exists():
        cache_file = PROCESSED_DIR / f"{sid}_ppg_cache.npz"

    ppg_cache = np.load(cache_file)
    n_windows = int(ppg_cache["n_windows"])

    # Load ECG reference cache
    ecg_cache_path = PROCESSED_DIR / "ecg_reference_cache.npz"
    ecg_ref_full = np.load(ecg_cache_path)[sid] if ecg_cache_path.exists() else np.full(n_windows, 75.0)

    hr_ppg_clean = np.asarray(ppg_cache["hr_ppg"], dtype=np.float64).copy()
    enmo_10s = np.asarray(ppg_cache["enmo_10s"], dtype=np.float64)
    spectral_sqi = np.asarray(ppg_cache["spectral_sqi"], dtype=np.float64)
    timestamps = (
        np.asarray(ppg_cache["timestamps_sec"], dtype=np.float64)
        if "timestamps_sec" in ppg_cache
        else (np.arange(n_windows, dtype=np.float64) * 2.0)
    )

    # Slice indices
    start_idx = max(0, min(offset, n_windows - 1))
    end_idx = min(start_idx + limit, n_windows)

    win_slice = slice(start_idx, end_idx)
    hr_stream = hr_ppg_clean[win_slice].copy()
    ecg_stream = ecg_ref_full[win_slice].copy()
    enmo_stream = enmo_10s[win_slice].copy()
    sqi_stream = spectral_sqi[win_slice].copy()
    ts_stream = timestamps[win_slice].copy()

    fault_applied = fault_type.upper()
    is_synthetic = fault_applied not in ["NONE", "CLEAN", ""]
    synthetic_mask = np.zeros(len(hr_stream), dtype=bool)

    # Apply synthetic fault if requested
    if is_synthetic and not use_f7:
        injector = FaultInjector(seed=42 + start_idx)
        fs = 0.5  # 1 sample every 2.0 s

        if fault_applied in ["F1_GAPS", "F1"]:
            res = injector.inject_gaps(hr_stream, fs=fs, severity=FaultSeverity.MED)
            hr_stream = res.signal
            synthetic_mask = res.synthetic_mask
        elif fault_applied in ["F2_STALE", "F2"]:
            res = injector.inject_stale(hr_stream, fs=fs, severity=FaultSeverity.MED)
            hr_stream = res.signal
            synthetic_mask = res.synthetic_mask
        elif fault_applied in ["F3_DUPL", "F3"]:
            # Duplicate values in place to maintain fixed window length
            res = injector.inject_stale(hr_stream, fs=fs, severity=FaultSeverity.LOW)
            hr_stream = res.signal
            synthetic_mask = res.synthetic_mask
        elif fault_applied in ["F4_SPIKE", "F4"]:
            res = injector.inject_spikes(hr_stream, fs=fs, severity=FaultSeverity.HIGH)
            hr_stream = res.signal
            synthetic_mask = res.synthetic_mask
        elif fault_applied in ["F5_DRIFT", "F5"]:
            res = injector.inject_drift(hr_stream, fs=fs, severity=FaultSeverity.MED)
            hr_stream = res.signal
            synthetic_mask = res.synthetic_mask
        elif fault_applied in ["F6_UNIT", "F6"]:
            # Unit error: scale by 1.6
            hr_stream = hr_stream * 1.6
            synthetic_mask[:] = True
    elif use_f7:
        synthetic_mask[:] = True

    # Re-evaluate dynamic trust score and alert state on the stream
    scorer = RuleBasedTrustScorer()
    trust_scores = np.zeros(len(hr_stream), dtype=np.float64)
    alert_states = np.zeros(len(hr_stream), dtype=bool)
    alert_suppressed = np.zeros(len(hr_stream), dtype=bool)

    tau_threshold = 100.0  # Population threshold (Arm 1 baseline)

    for j in range(len(hr_stream)):
        # 30-second rolling window (up to 15 windows)
        sub_hr = hr_stream[max(0, j - 14) : j + 1]
        eval_res = scorer.evaluate_window(sub_hr)

        # Motion attenuation
        enmo_val = float(enmo_stream[j])
        if enmo_val <= scorer.rest_motion_threshold_g:
            mot_score = 1.0
        elif enmo_val >= scorer.severe_motion_threshold_g:
            mot_score = 0.20
        else:
            norm_m = (enmo_val - scorer.rest_motion_threshold_g) / (
                scorer.severe_motion_threshold_g - scorer.rest_motion_threshold_g
            )
            mot_score = float(1.0 - 0.60 * norm_m)

        g = eval_res.sub_scores["gap"]
        st = eval_res.sub_scores["stale"]
        ph = eval_res.sub_scores["phys"]

        if g == 0.0 or st == 0.0 or ph == 0.0:
            final_trust = 0.0
        else:
            final_trust = float(np.clip(g * st * ph * mot_score, 0.0, 1.0))

        trust_scores[j] = round(final_trust, 3)

        curr_hr = hr_stream[j]
        raw_alert = bool(not np.isnan(curr_hr) and curr_hr >= tau_threshold)

        # Trust gate: suppresses alert if trust < 0.60
        if raw_alert and final_trust < 0.60:
            alert_states[j] = False
            alert_suppressed[j] = True
        elif raw_alert:
            alert_states[j] = True
            alert_suppressed[j] = False
        else:
            alert_states[j] = False
            alert_suppressed[j] = False

    # Format points
    points = []
    for k in range(len(hr_stream)):
        val_ppg = float(hr_stream[k]) if not np.isnan(hr_stream[k]) else None
        val_ecg = float(ecg_stream[k]) if not np.isnan(ecg_stream[k]) else None
        points.append({
            "idx": start_idx + k,
            "timestamp_sec": round(float(ts_stream[k]), 1),
            "hr_ppg": round(val_ppg, 1) if val_ppg is not None else None,
            "hr_ecg": round(val_ecg, 1) if val_ecg is not None else None,
            "trust_score": float(trust_scores[k]),
            "enmo": round(float(enmo_stream[k]), 4),
            "is_alert": bool(alert_states[k]),
            "alert_suppressed": bool(alert_suppressed[k]),
            "fault_active": bool(synthetic_mask[k]),
        })

    return {
        "notice": "REPLAY: public dataset, not live",
        "subject": sid,
        "fault_type": fault_applied,
        "is_synthetic": is_synthetic,
        "tag": "SYNTHETIC" if is_synthetic else "REAL_REPLAY",
        "offset": start_idx,
        "limit": limit,
        "total_windows": n_windows,
        "step_sec": 2.0,
        "data": points,
    }
