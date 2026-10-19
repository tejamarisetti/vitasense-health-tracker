"""
VitaSense AI - F7 Optical Noise Cache Builder
Protocol Amendment 3 Section 5.3: F7 High-Motion Optical BVP Noise

Corrupts raw 64 Hz optical BVP with additive noise modulated by ACC dynamic energy
before passing through Step 3a WristPPGHREstimator, and saves to:
data/processed/{sid}_f7_ppg_cache.npz (strictly preserving the clean no-fault cache).
"""

import sys
import pickle
from pathlib import Path
from typing import Dict, Any
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vitasense.estimators.ppg_hr_estimator import WristPPGHREstimator
from vitasense.benchmarks.fault_injection import FaultInjector, FaultSeverity
from vitasense.quality.event_prevalence import compute_enmo
from vitasense.quality.trust_score import RuleBasedTrustScorer


DATA_RAW_DIR = ROOT / "data" / "raw" / "ppg_dalia" / "extracted" / "PPG_FieldStudy"
DATA_PROCESSED_DIR = ROOT / "data" / "processed"


def build_f7_cache_for_subject(
    sid: str,
    severity: FaultSeverity = FaultSeverity.MED,
    seed: int = 42,
) -> Path:
    """
    Builds and saves F7 corrupted PPG cache for a single subject.
    Does NOT overwrite the clean no-fault cache.
    """
    pkl_path = DATA_RAW_DIR / sid / f"{sid}.pkl"
    if not pkl_path.exists():
        raise FileNotFoundError(f"Subject data file not found: {pkl_path}")

    with open(pkl_path, "rb") as f:
        data = pickle.load(f, encoding="latin1")

    bvp = data["signal"]["wrist"]["BVP"].flatten().astype(float)
    acc = data["signal"]["wrist"]["ACC"].astype(float)
    labels = np.asarray(data["label"]).flatten()
    n_windows = len(labels)
    del data

    # Interpolate 32 Hz ACC to 64 Hz to match BVP sample count
    acc_mag_32hz = np.linalg.norm(acc, axis=1)
    acc_mag_64hz = np.repeat(acc_mag_32hz, 2)[: len(bvp)]

    # Inject F7 additive noise modulated by ACC motion energy
    injector = FaultInjector(seed=seed)
    f7_res = injector.inject_noise(
        bvp,
        severity=severity,
        motion_acc=acc_mag_64hz,
    )
    bvp_corrupted = f7_res.signal

    # Step 3a Spectral Wrist-PPG HR Estimator operating on corrupted BVP
    estimator = WristPPGHREstimator(fs_ppg=64.0, window_sec=8.0, step_sec=2.0)
    estimates = estimator.estimate_stream(bvp_corrupted, total_windows=n_windows)

    hr_ppg = np.array(
        [e.hr_bpm if (e.hr_bpm is not None and e.is_valid) else np.nan for e in estimates],
        dtype=np.float64,
    )
    spectral_sqi = np.array([e.spectral_sqi for e in estimates], dtype=np.float64)
    dominant_freq_hz = np.array([e.dominant_freq_hz for e in estimates], dtype=np.float64)
    is_valid = np.array([e.is_valid for e in estimates], dtype=bool)

    enmo_step, enmo_10s = compute_enmo(acc, n_windows=n_windows)

    # Compute trust scores on corrupted stream
    scorer = RuleBasedTrustScorer(abstention_threshold=0.70)
    s_trust = np.zeros(n_windows, dtype=np.float64)
    s_trust_nomot = np.zeros(n_windows, dtype=np.float64)

    for i in range(n_windows):
        hr_win = hr_ppg[max(0, i - 14) : i + 1]
        res = scorer.evaluate_window(hr_win)

        enmo_val = float(enmo_10s[i])
        if enmo_val <= scorer.rest_motion_threshold_g:
            mot_score = 1.0
        elif enmo_val >= scorer.severe_motion_threshold_g:
            mot_score = 0.20
        else:
            norm_m = (enmo_val - scorer.rest_motion_threshold_g) / (
                scorer.severe_motion_threshold_g - scorer.rest_motion_threshold_g
            )
            mot_score = float(1.0 - 0.60 * norm_m)

        g, st, ph = res.sub_scores["gap"], res.sub_scores["stale"], res.sub_scores["phys"]
        if g == 0.0 or st == 0.0 or ph == 0.0:
            tr = 0.0
            tr_nomot = 0.0
        else:
            tr = float(np.clip(g * st * ph * mot_score, 0.0, 1.0))
            tr_nomot = float(np.clip(g * st * ph, 0.0, 1.0))

        s_trust[i] = tr
        s_trust_nomot[i] = tr_nomot

    out_path = DATA_PROCESSED_DIR / f"{sid}_f7_ppg_cache.npz"
    np.savez_compressed(
        out_path,
        subject_id=sid,
        n_windows=n_windows,
        hr_ppg=hr_ppg,
        spectral_sqi=spectral_sqi,
        dominant_freq_hz=dominant_freq_hz,
        is_valid=is_valid,
        enmo_10s=enmo_10s,
        s_trust=s_trust,
        s_trust_no_motion=s_trust_nomot,
        snr_db=f7_res.metadata.get("snr_db_target", 5.0),
    )
    return out_path


def build_all_f7_cache(severity: FaultSeverity = FaultSeverity.MED, seed: int = 42):
    print("Building separate F7 optical noise cache for all 15 subjects...")
    for sid in [f"S{i}" for i in range(1, 16)]:
        p = build_f7_cache_for_subject(sid, severity=severity, seed=seed)
        print(f"  Saved F7 cache: {p.name}")


if __name__ == "__main__":
    build_all_f7_cache()
