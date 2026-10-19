import pickle
import numpy as np
import scipy.signal as signal

with open('data/raw/ppg_dalia/extracted/PPG_FieldStudy/S5/S5.pkl', 'rb') as f:
    data = pickle.load(f, encoding='latin1')

wrist = data['signal']['wrist']
bvp = wrist['BVP'].flatten()
acc = wrist['ACC']
labels = data['label'].flatten()
activity = data['activity'].flatten()

# Check BVP amplitude and SNR
bvp_std = np.std(bvp)
bvp_min = np.min(bvp)
bvp_max = np.max(bvp)
print(f'S5 BVP stats: std={bvp_std:.2f}, min={bvp_min:.2f}, max={bvp_max:.2f}')

# Let's inspect where the 30 Amendment 1 events occurred in S5:
# In our previous event prevalence computation, which activities did they belong to?
# Let's check:
import sys
sys.path.append('.')
from src.evaluation.eval_pipeline import run_baseline_on_subject
results = run_baseline_on_subject('S5', 'data/raw/ppg_dalia/extracted/PPG_FieldStudy')
hr_pred = results['hr_pred']
hr_true = results['hr_true']
acts = results['activity']
enmo = results['enmo']

print(f'S5 Pred HR: mean={np.nanmean(hr_pred):.2f}, min={np.nanmin(hr_pred):.2f}, max={np.nanmax(hr_pred):.2f}')
print(f'S5 True HR: mean={np.nanmean(hr_true):.2f}, min={np.nanmin(hr_true):.2f}, max={np.nanmax(hr_true):.2f}')

# What was the predicted HR during resting activities?
resting_acts = [1, 2, 4, 7] # 1: Baseline, 2: Sitting/working, 4: Lunch, 7: Driving
for act_code, name in [(1, 'BASELINE'), (2, 'WORKING'), (4, 'LUNCH'), (7, 'DRIVING')]:
    mask = (acts == act_code)
    if np.sum(mask) > 0:
        mae = np.mean(np.abs(hr_pred[mask] - hr_true[mask]))
        corr = np.corrcoef(hr_pred[mask], hr_true[mask])[0, 1]
        print(f'Act {name}: N={np.sum(mask)}, True HR mean={np.mean(hr_true[mask]):.1f}, Pred HR mean={np.mean(hr_pred[mask]):.1f}, MAE={mae:.2f}, Corr={corr:.4f}')

# Check frequency spectrum of BVP during BASELINE for S5
# 8s window = 512 samples
bvp_baseline = bvp[:int(300*2*64)] # first 10 min
freqs, psd = signal.welch(bvp_baseline, fs=64.0, nperseg=512)
peak_idx = np.argmax(psd[(freqs >= 0.7) & (freqs <= 3.5)])
peak_freq = freqs[(freqs >= 0.7) & (freqs <= 3.5)][peak_idx]
print(f'S5 Baseline BVP dominant spectral peak: {peak_freq:.3f} Hz ({peak_freq*60:.1f} bpm), whereas True HR is {np.mean(hr_true[acts==1]):.1f} bpm')
