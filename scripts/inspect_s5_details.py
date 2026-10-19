import sys
import pickle
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vitasense.estimators.ppg_hr_estimator import WristPPGHREstimator

path = ROOT / "data" / "raw" / "ppg_dalia" / "extracted" / "PPG_FieldStudy" / "S5" / "S5.pkl"
with open(path, 'rb') as f:
    data = pickle.load(f, encoding='latin1')

wrist = data['signal']['wrist']
bvp = wrist['BVP'].flatten()
acc = wrist['ACC']
labels = data['label'].flatten()
activity = data['activity'].flatten()

estimator = WristPPGHREstimator(fs_ppg=64.0, window_sec=8.0, step_sec=2.0)
n_windows = len(labels)
estimates = estimator.estimate_stream(bvp, total_windows=n_windows)

records = []
ACTIVITY_MAP = {
    0: "NO_ACTIVITY (Transitions)",
    1: "BASELINE (Resting)",
    2: "STAIRS (Climbing)",
    3: "SOCCER (Table soccer)",
    4: "CYCLING (Outdoor)",
    5: "DRIVING (Car)",
    6: "LUNCH (Sitting/eating)",
    7: "WALKING (Walking)",
    8: "WORKING (Desk work)",
}

for i in range(min(len(estimates), n_windows)):
    est = estimates[i]
    ecg_ref = labels[i]
    t_sec = i * 2.0
    act_idx = min(len(activity) - 1, int(round((t_sec + 4.0) * 4.0)))
    act_code = int(round(activity[act_idx]))
    act_name = ACTIVITY_MAP.get(act_code, f"UNKNOWN_{act_code}")
    
    # compute 8s ENMO from acc
    # acc is 32 Hz
    a_start = int(i * 2.0 * 32.0)
    a_end = a_start + int(8.0 * 32.0)
    if a_end <= len(acc):
        acc_win = acc[a_start:a_end]
        norm = np.sqrt(np.sum(acc_win**2, axis=1)) / 64.0
        enmo = np.mean(np.maximum(0.0, norm - 1.0))
    else:
        enmo = np.nan

    records.append({
        "window_idx": i,
        "timestamp_sec": t_sec,
        "activity_code": act_code,
        "activity_name": act_name,
        "ecg_ref_hr": ecg_ref,
        "ppg_est_hr": est.hr_bpm,
        "is_valid": est.is_valid,
        "spectral_sqi": est.spectral_sqi,
        "enmo": enmo,
    })

import pandas as pd
df = pd.DataFrame(records)

print('S5 Overall Results:')
print(f"Total Windows: {len(df)}")
valid = df.dropna(subset=['ppg_est_hr', 'ecg_ref_hr'])
mae = np.mean(np.abs(valid['ppg_est_hr'] - valid['ecg_ref_hr']))
corr = np.corrcoef(valid['ppg_est_hr'], valid['ecg_ref_hr'])[0, 1]
print(f"MAE: {mae:.2f} bpm | Median Error: {np.median(np.abs(valid['ppg_est_hr'] - valid['ecg_ref_hr'])):.2f} bpm | Corr: {corr:.4f}")

print('\nPer Activity for S5:')
for act_id, act_name in ACTIVITY_MAP.items():
    sub = valid[valid['activity_code'] == act_id]
    if len(sub) > 0:
        a_mae = np.mean(np.abs(sub['ppg_est_hr'] - sub['ecg_ref_hr']))
        a_med = np.median(np.abs(sub['ppg_est_hr'] - sub['ecg_ref_hr']))
        a_corr = np.corrcoef(sub['ppg_est_hr'], sub['ecg_ref_hr'])[0, 1] if len(sub) > 1 and np.std(sub['ppg_est_hr']) > 0 and np.std(sub['ecg_ref_hr']) > 0 else np.nan
        print(f"{act_name:25s} | N={len(sub):4d} | Ref HR: {sub['ecg_ref_hr'].mean():.1f}±{sub['ecg_ref_hr'].std():.1f} | Pred HR: {sub['ppg_est_hr'].mean():.1f}±{sub['ppg_est_hr'].std():.1f} | MAE: {a_mae:5.2f} | Med: {a_med:5.2f} | Corr: {a_corr:.4f}")

# Check resting windows (ENMO <= 0.05 and resting activities)
rest_mask = valid['activity_code'].isin([1, 5, 6, 8]) & (valid['enmo'] <= 0.05)
print(f"\nS5 Total Resting Windows: {np.sum(rest_mask)} ({np.sum(rest_mask)*2/60:.1f} min)")
print(f"S5 Resting Ref HR: mean={valid.loc[rest_mask, 'ecg_ref_hr'].mean():.1f}, median={valid.loc[rest_mask, 'ecg_ref_hr'].median():.1f}, min={valid.loc[rest_mask, 'ecg_ref_hr'].min():.1f}, max={valid.loc[rest_mask, 'ecg_ref_hr'].max():.1f}")
print(f"S5 Resting Pred HR: mean={valid.loc[rest_mask, 'ppg_est_hr'].mean():.1f}, median={valid.loc[rest_mask, 'ppg_est_hr'].median():.1f}")
print(f"S5 Resting MAE: {np.mean(np.abs(valid.loc[rest_mask, 'ppg_est_hr'] - valid.loc[rest_mask, 'ecg_ref_hr'])):.2f} bpm")
print(f"Fraction of S5 Resting time where Ref HR > 100 bpm: {np.mean(valid.loc[rest_mask, 'ecg_ref_hr'] > 100.0)*100:.1f}%")
print(f"Fraction of S5 Resting time where Ref HR > tau_i (105.01 bpm): {np.mean(valid.loc[rest_mask, 'ecg_ref_hr'] > 105.01)*100:.1f}%")

# Let's inspect what happens during BASELINE (Resting):
base_sub = valid[valid['activity_code'] == 1]
print(f"\nS5 BASELINE: Ref HR={base_sub['ecg_ref_hr'].mean():.1f}±{base_sub['ecg_ref_hr'].std():.1f}, Pred HR={base_sub['ppg_est_hr'].mean():.1f}±{base_sub['ppg_est_hr'].std():.1f}")
print(f"S5 BASELINE errors: first 10 windows:")
for idx, r in base_sub.head(10).iterrows():
    print(f"  t={r['timestamp_sec']:5.1f}s: Ref HR = {r['ecg_ref_hr']:5.1f} | Pred HR = {r['ppg_est_hr']:5.1f} | Diff = {r['ppg_est_hr'] - r['ecg_ref_hr']:5.1f} | SQI = {r['spectral_sqi']:.3f}")
