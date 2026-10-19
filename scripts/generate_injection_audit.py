"""
VitaSense AI - Synthetic Tachycardia Injection Parameter Audit & Placement Analysis
Protocol Section 8 (Amendment 2 Option (a)) - Frozen Protocol v2.0.0

Generates:
1. results/synthetic_injection_audit.csv and docs/synthetic_injection_audit.csv
   Columns: subject, episode_id, start_window, start_time_sec, start_time_str, duration_sec,
            requested_plateau_sec, actual_plateau_sec, ramp_rate_bpm_s, peak_hr,
            resting_mean, jump_size_bpm, clamped_flag, clamped_reason
2. Detailed audit report:
   - Summary of clamped/adjusted parameters and mathematical rationale
   - Available resting blocks per subject and episode placement
   - Fraction of episodes in the first 10 minutes (t < 600s)
   - Plain-language description of temporal clustering
"""

import sys
import csv
import pickle
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vitasense.quality.event_prevalence import (
    compute_enmo,
    align_activity_to_windows,
    RESTING_ACTIVITY_CODES,
)
from vitasense.benchmarks.synthetic_alert_injection import SyntheticTachycardiaInjector


DATA_DIR = ROOT / "data" / "raw" / "ppg_dalia" / "extracted" / "PPG_FieldStudy"
RESULTS_DIR = ROOT / "results"
DOCS_DIR = ROOT / "docs"


def audit_subject(sid: str, injector: SyntheticTachycardiaInjector):
    pkl_path = DATA_DIR / sid / f"{sid}.pkl"
    with open(pkl_path, "rb") as f:
        data = pickle.load(f, encoding="latin1")

    labels = np.asarray(data["label"]).flatten()
    activity = np.asarray(data["activity"]).flatten()
    acc = data["signal"]["wrist"]["ACC"]
    n_windows = len(labels)

    # 1. ENMO dynamic energy & activity alignment
    _, enmo_10s = compute_enmo(acc, n_windows=n_windows)
    act_aligned = align_activity_to_windows(activity, n_windows=n_windows)

    # 2. Personal baseline resting threshold
    baseline_mask = (act_aligned == 1)
    if np.sum(baseline_mask) >= 10:
        mu_rest = float(np.mean(labels[baseline_mask]))
        std_rest = float(np.std(labels[baseline_mask], ddof=1))
    else:
        mu_rest = 70.0
        std_rest = 5.0
    tau_i = max(100.0, mu_rest + 2.5 * std_rest)

    # 3. Resting context
    is_resting = np.isin(act_aligned, list(RESTING_ACTIVITY_CODES)) & (enmo_10s <= 0.05)
    is_tachy = (labels > tau_i)
    clean_rest = is_resting & (~is_tachy)

    # 4. Extract all clean resting blocks
    diff = np.diff(np.concatenate(([0], clean_rest.astype(int), [0])))
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0]
    all_blocks = []
    for s, e in zip(starts, ends):
        dur_s = float((e - s) * injector.step_sec)
        all_blocks.append({
            "start_win": int(s),
            "end_win": int(e - 1),
            "start_s": float(s * injector.step_sec),
            "end_s": float((e - 1) * injector.step_sec),
            "duration_s": dur_s,
            "duration_m": dur_s / 60.0,
            "eligible": dur_s >= (injector.t_ramp + injector.plateau_min + injector.t_decay + 2.0 * injector.edge_buffer_sec),
        })

    # 5. Inject episodes
    res = injector.inject(labels, is_resting, tau_i, subject_id=sid)

    # 6. Audit each injected episode
    episode_records = []
    for ep in res.episodes:
        # Find which block contains this episode
        host_block = None
        for b in all_blocks:
            if b["start_win"] <= ep.start_window and ep.end_window <= b["end_win"]:
                host_block = b
                break

        # Check parameter adjustments / clamping
        flags = []
        reasons = []

        # Peak HR clamping
        if np.isclose(ep.peak_hr, 135.0, atol=0.01):
            flags.append("PEAK_CLAMPED_135")
            reasons.append("Peak HR reached upper bound ceiling (135.0 bpm) due to baseline HR fluctuation during plateau")
        elif np.isclose(ep.peak_hr, 105.0, atol=0.01):
            flags.append("PEAK_CLAMPED_105")
            reasons.append("Peak HR clamped at lower bound floor (105.0 bpm) due to low local resting baseline")

        # Ramp rate bounding
        hr_base = ep.base_hr
        r_lo = max(2.0, (105.0 - hr_base) / 15.0)
        r_hi = min(4.0, (135.0 - hr_base) / 15.0)
        if r_lo > 2.0:
            flags.append("RAMP_MIN_ADJUSTED")
            reasons.append(f"Min ramp rate adjusted from 2.0 to {r_lo:.2f} bpm/s to guarantee peak >= 105 bpm from base {hr_base:.1f} bpm")
        if r_hi < 4.0:
            flags.append("RAMP_MAX_ADJUSTED")
            reasons.append(f"Max ramp rate adjusted from 4.0 to {r_hi:.2f} bpm/s to guarantee peak <= 135 bpm from base {hr_base:.1f} bpm")

        # Plateau duration constraints
        # Check if block constrained plateau upper bound below 120s
        if host_block:
            avail_dur = host_block["duration_s"] - 2.0 * injector.edge_buffer_sec
            max_plat_block = min(120.0, max(45.0, avail_dur - injector.t_ramp - injector.t_decay))
            if max_plat_block < 120.0:
                flags.append("PLAT_SAMPLING_CONSTRAINED")
                reasons.append(f"Block duration ({host_block['duration_s']:.0f}s) constrained max plateau to {max_plat_block:.1f}s (below nominal 120s)")

        clamped_flag = len(flags) > 0
        clamped_str = "; ".join(flags) if flags else "NONE"
        reason_str = "; ".join(reasons) if reasons else "Nominal sampling within ratified bounds"

        # Unconstrained draws from ratified Amendment 2 ranges:
        # Plateau in [45, 120]s, Ramp in [2.0, 4.0] bpm/s, Peak in [105.0, 135.0] bpm
        # Using a shadow unconstrained generator with the same episode seed offset
        ep_seed = (injector._get_subject_seed(sid) + ep.episode_id * 10007) % (2**31 - 1)
        ep_rng = np.random.default_rng(ep_seed)
        req_plat = float(ep_rng.uniform(45.0, 120.0))
        req_ramp = float(ep_rng.uniform(2.0, 4.0))
        req_peak = float(ep_rng.uniform(105.0, 135.0))

        # Check differences
        ramp_diff = not np.isclose(ep.ramp_rate_bpm_s, req_ramp, atol=0.05)
        peak_diff = not np.isclose(ep.peak_hr, req_peak, atol=0.5)
        plat_diff = not np.isclose(ep.plateau_duration_sec, req_plat, atol=1.0)

        jump_size = ep.peak_hr - mu_rest
        mm = int(ep.start_time_sec // 60)
        ss = int(ep.start_time_sec % 60)
        time_str = f"{mm:02d}:{ss:02d}"

        episode_records.append({
            "subject": sid,
            "episode_id": ep.episode_id,
            "start_window": ep.start_window,
            "start_time_sec": ep.start_time_sec,
            "start_time_str": time_str,
            "duration_sec": ep.duration_sec,
            "requested_plateau_sec": req_plat,
            "actual_plateau_sec": ep.plateau_duration_sec,
            "requested_ramp_rate_bpm_s": req_ramp,
            "actual_ramp_rate_bpm_s": ep.ramp_rate_bpm_s,
            "requested_peak_hr": req_peak,
            "actual_peak_hr": ep.peak_hr,
            "resting_mean": mu_rest,
            "jump_size_bpm": jump_size,
            "ramp_differed": "YES" if ramp_diff else "NO",
            "peak_differed": "YES" if peak_diff else "NO",
            "plateau_differed": "YES" if plat_diff else "NO",
            "clamped_flag": clamped_str,
            "clamped_reason": reason_str,
            "host_block": host_block,
        })

    del data
    return {
        "subject": sid,
        "mu_rest": mu_rest,
        "tau_i": tau_i,
        "blocks": all_blocks,
        "records": episode_records,
    }


def main():
    print("=" * 80)
    print("VITASENSE AI - SYNTHETIC INJECTION PARAMETER & PLACEMENT AUDIT")
    print("Protocol Section 8 (Amendment 2 Option (a))")
    print("=" * 80)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    csv_path_results = RESULTS_DIR / "synthetic_injection_audit.csv"
    csv_path_docs = DOCS_DIR / "synthetic_injection_audit.csv"

    injector = SyntheticTachycardiaInjector(seed=42)

    all_records = []
    subject_summaries = []

    for i in range(1, 16):
        sid = f"S{i}"
        s_data = audit_subject(sid, injector)
        subject_summaries.append(s_data)
        all_records.extend(s_data["records"])

    # Write CSV
    fieldnames = [
        "subject",
        "episode_id",
        "start_window",
        "start_time_sec",
        "start_time_str",
        "duration_sec",
        "requested_plateau_sec",
        "actual_plateau_sec",
        "requested_ramp_rate_bpm_s",
        "actual_ramp_rate_bpm_s",
        "requested_peak_hr",
        "actual_peak_hr",
        "resting_mean",
        "jump_size_bpm",
        "ramp_differed",
        "peak_differed",
        "plateau_differed",
        "clamped_flag",
        "clamped_reason",
    ]

    for p in [csv_path_results, csv_path_docs]:
        with open(p, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for r in all_records:
                writer.writerow({
                    "subject": r["subject"],
                    "episode_id": r["episode_id"],
                    "start_window": r["start_window"],
                    "start_time_sec": f"{r['start_time_sec']:.1f}",
                    "start_time_str": r["start_time_str"],
                    "duration_sec": f"{r['duration_sec']:.1f}",
                    "requested_plateau_sec": f"{r['requested_plateau_sec']:.1f}",
                    "actual_plateau_sec": f"{r['actual_plateau_sec']:.1f}",
                    "requested_ramp_rate_bpm_s": f"{r['requested_ramp_rate_bpm_s']:.2f}",
                    "actual_ramp_rate_bpm_s": f"{r['actual_ramp_rate_bpm_s']:.2f}",
                    "requested_peak_hr": f"{r['requested_peak_hr']:.1f}",
                    "actual_peak_hr": f"{r['actual_peak_hr']:.1f}",
                    "resting_mean": f"{r['resting_mean']:.1f}",
                    "jump_size_bpm": f"{r['jump_size_bpm']:.1f}",
                    "ramp_differed": r["ramp_differed"],
                    "peak_differed": r["peak_differed"],
                    "plateau_differed": r["plateau_differed"],
                    "clamped_flag": r["clamped_flag"],
                    "clamped_reason": r["clamped_reason"],
                })

    print(f"\n[+] Successfully saved {len(all_records)} episode records to:")
    print(f"    - {csv_path_results}")
    print(f"    - {csv_path_docs}")

    # Section 1: Parameter Clamping & Adjustment Analysis
    total_eps = len(all_records)
    peak_135 = sum(1 for r in all_records if "PEAK_CLAMPED_135" in r["clamped_flag"])
    peak_105 = sum(1 for r in all_records if "PEAK_CLAMPED_105" in r["clamped_flag"])
    ramp_lo = sum(1 for r in all_records if "RAMP_MIN_ADJUSTED" in r["clamped_flag"])
    ramp_hi = sum(1 for r in all_records if "RAMP_MAX_ADJUSTED" in r["clamped_flag"])
    plat_block = sum(1 for r in all_records if "PLAT_SAMPLING_CONSTRAINED" in r["clamped_flag"])

    print("\n" + "=" * 80)
    print("1. PARAMETER CLAMPING & ADJUSTMENT AUDIT")
    print("=" * 80)
    print(f"Total Injected Episodes: {total_eps}")
    print(f"- Peak HR clamped at 135.0 bpm ceiling: {peak_135} / {total_eps} ({peak_135/total_eps*100:.1f}%)")
    print(f"- Peak HR clamped at 105.0 bpm floor:   {peak_105} / {total_eps} ({peak_105/total_eps*100:.1f}%)")
    print(f"- Ramp rate min adjusted (> 2.0 bpm/s): {ramp_lo} / {total_eps} ({ramp_lo/total_eps*100:.1f}%) [to guarantee peak >= 105 bpm]")
    print(f"- Ramp rate max adjusted (< 4.0 bpm/s): {ramp_hi} / {total_eps} ({ramp_hi/total_eps*100:.1f}%) [to guarantee peak <= 135 bpm]")
    print(f"- Plateau max restricted by block:      {plat_block} / {total_eps} ({plat_block/total_eps*100:.1f}%) [due to block length < 155s]")

    # Section 2: Resting Block Availability & Temporal Placement Analysis
    print("\n" + "=" * 80)
    print("2. RESTING BLOCK AVAILABILITY & TEMPORAL PLACEMENT")
    print("=" * 80)

    total_first_10 = 0
    print(f"{'Subject':<8} | {'Resting Blocks (Durations)':<35} | {'Episodes':<9} | {'In 1st 10m':<10} | {'Pct 1st 10m':<11}")
    print("-" * 80)

    for s in subject_summaries:
        sid = s["subject"]
        n_eps = len(s["records"])
        n_first_10 = sum(1 for r in s["records"] if r["start_time_sec"] < 600.0)
        total_first_10 += n_first_10
        pct_first_10 = (n_first_10 / n_eps) * 100.0 if n_eps > 0 else 0.0

        # Summarize eligible blocks
        elig_blocks = [b for b in s["blocks"] if b["eligible"]]
        b_durs = [f"{b['duration_s']:.0f}s" for b in elig_blocks]
        b_str = f"{len(elig_blocks)} blocks: " + ", ".join(b_durs[:3])
        if len(b_durs) > 3:
            b_str += f", +{len(b_durs)-3} more"

        print(f"{sid:<8} | {b_str:<35} | {n_eps:<9} | {n_first_10:<10} | {pct_first_10:5.1f}%")

    print("-" * 80)
    print(f"{'TOTAL':<8} | {'Across all 15 subjects':<35} | {total_eps:<9} | {total_first_10:<10} | {total_first_10/total_eps*100:5.1f}%")
    print("=" * 80)


if __name__ == "__main__":
    main()
