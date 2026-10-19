"""
VitaSense AI - Wrist-PPG Heart Rate & Quality Index Cache Builder
Protocol Section 4 (Amendment 3) - Front-End Feature Caching

Computes and saves for all 15 PPG-DaLiA subjects:
1. Wrist-PPG HR estimate from Step 3a spectral estimator (WristPPGHREstimator)
2. Spectral SQI (spectral purity ratio Q in [0.0, 1.0])
3. Dominant cardiac peak frequency (Hz)
4. ENMO dynamic motion series (2s step and 10s rolling mean)
5. Rule-based trust score inputs and sub-scores (S_gap, S_stale, S_phys, S_motion, S_trust, S_trust_noMotion)

Target Directory: data/processed/ (gitignored, never committed).
Supports verification mode to assert bitwise identical output across runs.
"""

import sys
import json
import pickle
import hashlib
from pathlib import Path
from typing import Dict, Any, Tuple
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vitasense.estimators.ppg_hr_estimator import WristPPGHREstimator
from vitasense.quality.event_prevalence import compute_enmo
from vitasense.quality.trust_score import RuleBasedTrustScorer


DATA_RAW_DIR = ROOT / "data" / "raw" / "ppg_dalia" / "extracted" / "PPG_FieldStudy"
DATA_PROCESSED_DIR = ROOT / "data" / "processed"


def compute_file_sha256(filepath: Path) -> str:
    """Computes SHA-256 hex digest of a binary file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_subject_cache(
    sid: str,
    estimator: WristPPGHREstimator,
    scorer: RuleBasedTrustScorer,
) -> Dict[str, Any]:
    """
    Computes all front-end estimates and trust quality series for a single subject.
    """
    pkl_path = DATA_RAW_DIR / sid / f"{sid}.pkl"
    if not pkl_path.exists():
        raise FileNotFoundError(f"Subject data file not found: {pkl_path}")

    with open(pkl_path, "rb") as f:
        data = pickle.load(f, encoding="latin1")

    bvp = data["signal"]["wrist"]["BVP"].flatten()
    acc = data["signal"]["wrist"]["ACC"]
    labels = np.asarray(data["label"]).flatten()
    n_windows = len(labels)
    del data

    # 1. Step 3a Spectral Wrist-PPG HR Estimator
    estimates = estimator.estimate_stream(bvp, total_windows=n_windows)
    hr_ppg = np.array(
        [e.hr_bpm if (e.hr_bpm is not None and e.is_valid) else np.nan for e in estimates],
        dtype=np.float64,
    )
    spectral_sqi = np.array([e.spectral_sqi for e in estimates], dtype=np.float64)
    dominant_freq_hz = np.array([e.dominant_freq_hz for e in estimates], dtype=np.float64)
    is_valid = np.array([e.is_valid for e in estimates], dtype=bool)

    # 2. ENMO Kinematic Series (2s step and 10s rolling)
    enmo_step, enmo_10s = compute_enmo(acc, n_windows=n_windows)
    del bvp, acc

    # 3. Trust Score Inputs and Precomputed Sub-Scores
    # Using 30-second rolling history buffer (15 windows @ 2s) matching RuleBasedTrustScorer
    s_gap = np.zeros(n_windows, dtype=np.float64)
    s_stale = np.zeros(n_windows, dtype=np.float64)
    s_phys = np.zeros(n_windows, dtype=np.float64)
    s_motion = np.zeros(n_windows, dtype=np.float64)
    s_trust = np.zeros(n_windows, dtype=np.float64)
    s_trust_no_motion = np.zeros(n_windows, dtype=np.float64)

    for i in range(n_windows):
        # Rolling HR window for gap, flatline, and physiological rate of change
        hr_win = hr_ppg[max(0, i - 14) : i + 1]
        res = scorer.evaluate_window(hr_win)

        # Motion attenuation evaluated against 10s ENMO dynamic energy
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

        g = res.sub_scores["gap"]
        st = res.sub_scores["stale"]
        ph = res.sub_scores["phys"]

        s_gap[i] = g
        s_stale[i] = st
        s_phys[i] = ph
        s_motion[i] = mot_score

        # Composite scores
        if g == 0.0 or st == 0.0 or ph == 0.0:
            tr = 0.0
            tr_no_mot = 0.0
        else:
            tr = float(np.clip(g * st * ph * mot_score, 0.0, 1.0))
            tr_no_mot = float(np.clip(g * st * ph, 0.0, 1.0))

        s_trust[i] = tr
        s_trust_no_motion[i] = tr_no_mot

    timestamps_sec = np.arange(n_windows, dtype=np.float64) * estimator.step_sec

    return {
        "subject_id": sid,
        "n_windows": n_windows,
        "timestamps_sec": timestamps_sec,
        "hr_ppg": hr_ppg,
        "spectral_sqi": spectral_sqi,
        "dominant_freq_hz": dominant_freq_hz,
        "is_valid": is_valid,
        "enmo_step": enmo_step,
        "enmo_10s": enmo_10s,
        "s_gap": s_gap,
        "s_stale": s_stale,
        "s_phys": s_phys,
        "s_motion": s_motion,
        "s_trust": s_trust,
        "s_trust_no_motion": s_trust_no_motion,
    }


def build_cache(verify_reproducibility: bool = True) -> Dict[str, Any]:
    """
    Builds the PPG and trust cache for all 15 subjects.
    Optionally re-runs a subset or full cohort to assert bitwise identical output.
    """
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    estimator = WristPPGHREstimator(fs_ppg=64.0, window_sec=8.0, step_sec=2.0)
    scorer = RuleBasedTrustScorer(abstention_threshold=0.70)

    print("=" * 80)
    print("VITASENSE AI - BUILDING WRIST-PPG & TRUST CACHE (ALL 15 SUBJECTS)")
    print(f"Output directory: {DATA_PROCESSED_DIR}")
    print("=" * 80)

    manifest_entries = {}
    first_run_checksums = {}

    for i in range(1, 16):
        sid = f"S{i}"
        print(f"Processing {sid}...", end=" ", flush=True)

        cached_data = compute_subject_cache(sid, estimator, scorer)
        out_path = DATA_PROCESSED_DIR / f"{sid}_ppg_cache.npz"

        # Save deterministically using np.savez_compressed
        np.savez_compressed(out_path, **cached_data)

        chk = compute_file_sha256(out_path)
        first_run_checksums[sid] = chk

        n_win = cached_data["n_windows"]
        valid_cnt = int(np.sum(cached_data["is_valid"]))
        pct_valid = valid_cnt / n_win * 100.0

        manifest_entries[sid] = {
            "n_windows": n_win,
            "valid_windows": valid_cnt,
            "pct_valid": pct_valid,
            "sha256": chk,
            "file": out_path.name,
            "shape": list(cached_data["hr_ppg"].shape),
        }
        print(f"done ({n_win} windows, {pct_valid:.1f}% valid). SHA256: {chk[:12]}...")

    # Compute cohort summary checksum
    combined_hash = hashlib.sha256("".join(first_run_checksums[f"S{i}"] for i in range(1, 16)).encode()).hexdigest()

    manifest = {
        "cohort_checksum_sha256": combined_hash,
        "n_subjects": 15,
        "step_sec": 2.0,
        "window_sec": 8.0,
        "subjects": manifest_entries,
    }

    manifest_path = DATA_PROCESSED_DIR / "cache_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "=" * 80)
    print(f"[+] All 15 subjects cached successfully.")
    print(f"Cohort Combined SHA-256: {combined_hash}")
    print(f"Manifest saved to: {manifest_path}")
    print("=" * 80)

    # 4. Verification Check: Re-run S1 and S2 to verify bitwise deterministic reproducibility
    if verify_reproducibility:
        print("\nVerifying reproducibility: Re-computing S1 and S2 to assert identical output...")
        for sid in ["S1", "S2"]:
            second_data = compute_subject_cache(sid, estimator, scorer)
            verify_path = DATA_PROCESSED_DIR / f"{sid}_verify_temp.npz"
            np.savez_compressed(verify_path, **second_data)
            second_chk = compute_file_sha256(verify_path)
            verify_path.unlink()

            first_chk = first_run_checksums[sid]
            assert first_chk == second_chk, (
                f"Determinism check failed for {sid}! First SHA256: {first_chk}, Second SHA256: {second_chk}"
            )
            print(f"  [+] {sid} re-run checksum matches bitwise: {first_chk[:12]} == {second_chk[:12]}")
        print("[+] Reproducibility verification PASSED: Identical output guaranteed across runs.\n")

    return manifest


if __name__ == "__main__":
    build_cache(verify_reproducibility=True)
