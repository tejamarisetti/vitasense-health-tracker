import pickle
import numpy as np
import scipy.stats as stats

subjects = ['S1', 'S5', 'S13']
FS_ECG = 700.0
FS_BVP = 64.0
FS_ACC = 32.0

for s in subjects:
    path = f'data/raw/ppg_dalia/extracted/PPG_FieldStudy/{s}/{s}.pkl'
    with open(path, 'rb') as f:
        data = pickle.load(f, encoding='latin1')
    
    rpeaks = data['rpeaks'].flatten()
    labels = data['label'].flatten()
    activity = data['activity'].flatten()
    wrist = data['signal']['wrist']
    bvp = wrist['BVP'].flatten()
    acc = wrist['ACC'] # (N, 3)
    
    # 1. RR interval distribution
    # rpeaks is sample indices at 700 Hz
    rr_samples = np.diff(rpeaks)
    rr_seconds = rr_samples / FS_ECG
    rr_bpm = 60.0 / rr_seconds
    
    frac_hr_lt_35 = np.mean(rr_bpm < 35.0)
    frac_hr_gt_200 = np.mean(rr_bpm > 200.0)
    
    # 2. Agreement between rpeaks-derived HR and label array
    # PPG-DaLiA label array is computed with 8s window, 2s step (shift = 2s, window = 8s).
    # Let's compute average HR in each 8s window centered/starting at each step.
    # In PPG-DaLiA: window length is 8s, step is 2s.
    # Let's align rpeaks count in each [t, t+8] window:
    hr_rpeaks = []
    for i in range(len(labels)):
        t_start = i * 2.0 * FS_ECG
        t_end = t_start + 8.0 * FS_ECG
        # count rpeaks in this window
        peaks_in_win = rpeaks[(rpeaks >= t_start) & (rpeaks < t_end)]
        if len(peaks_in_win) > 1:
            # HR = 60 * (len(peaks_in_win) - 1) / ((peaks_in_win[-1] - peaks_in_win[0]) / FS_ECG)
            # or 60 * len(peaks_in_win) / 8.0
            hr_win = (len(peaks_in_win) - 1) * 60.0 / ((peaks_in_win[-1] - peaks_in_win[0]) / FS_ECG)
        elif len(peaks_in_win) == 1:
            hr_win = 60.0
        else:
            hr_win = np.nan
        hr_rpeaks.append(hr_win)
    
    hr_rpeaks = np.array(hr_rpeaks)
    valid_mask = ~np.isnan(hr_rpeaks) & ~np.isnan(labels)
    rpeak_label_mae = np.mean(np.abs(hr_rpeaks[valid_mask] - labels[valid_mask]))
    rpeak_label_corr = stats.pearsonr(hr_rpeaks[valid_mask], labels[valid_mask])[0]
    
    # 3. Resting HR distribution (activity == 1 is BASELINE)
    # activity is sampled at 4 Hz, length matches labels?
    # Let's check activity length vs labels
    if len(activity) != len(labels):
        # resample activity to labels length
        indices = np.linspace(0, len(activity)-1, len(labels)).astype(int)
        act_at_labels = activity[indices]
    else:
        act_at_labels = activity
        
    baseline_mask = (act_at_labels == 1)
    hr_baseline = labels[baseline_mask]
    
    mu_rest = np.mean(hr_baseline)
    std_rest = np.std(hr_baseline, ddof=1)
    tau_i = max(100.0, mu_rest + 2.5 * std_rest)
    
    # Percentiles
    p_min = np.min(hr_baseline)
    p25 = np.percentile(hr_baseline, 25)
    p50 = np.median(hr_baseline)
    p75 = np.percentile(hr_baseline, 75)
    p95 = np.percentile(hr_baseline, 95)
    p99 = np.percentile(hr_baseline, 99)
    p_max = np.max(hr_baseline)
    
    # Check overall HR distribution across the entire session
    hr_all_p50 = np.median(labels)
    hr_all_mean = np.mean(labels)
    hr_all_max = np.max(labels)
    hr_all_min = np.min(labels)
    
    print(f'==============================')
    print(f'SUBJECT: {s}')
    print(f'==============================')
    print(f'Questionnaire: {data["questionnaire"]}')
    print(f'Total Windows (Labels): {len(labels)} ({len(labels)*2/60:.1f} min)')
    print(f'Total R-peaks: {len(rpeaks)}')
    print(f'RR Interval (s):')
    print(f'  Mean: {np.mean(rr_seconds):.4f}s | SD: {np.std(rr_seconds):.4f}s')
    print(f'  Min: {np.min(rr_seconds):.4f}s | 25%: {np.percentile(rr_seconds, 25):.4f}s | Median: {np.median(rr_seconds):.4f}s | 75%: {np.percentile(rr_seconds, 75):.4f}s | Max: {np.max(rr_seconds):.4f}s')
    print(f'Implied HR from RR (bpm):')
    print(f'  Min HR: {np.min(rr_bpm):.1f} | Median HR: {np.median(rr_bpm):.1f} | Max HR: {np.max(rr_bpm):.1f}')
    print(f'  Fraction HR < 35 bpm: {frac_hr_lt_35 * 100:.3f}%')
    print(f'  Fraction HR > 200 bpm: {frac_hr_gt_200 * 100:.3f}%')
    print(f'Agreement between R-peak-derived HR and Label array:')
    print(f'  MAE: {rpeak_label_mae:.3f} bpm')
    print(f'  Pearson r: {rpeak_label_corr:.4f}')
    print(f'Resting HR (BASELINE, activity=1, N={len(hr_baseline)} windows, {len(hr_baseline)*2/60:.1f} min):')
    print(f'  Mean: {mu_rest:.2f} bpm | SD: {std_rest:.2f} bpm')
    print(f'  Min: {p_min:.2f} | 25%: {p25:.2f} | 50%: {p50:.2f} | 75%: {p75:.2f} | 95%: {p95:.2f} | 99%: {p99:.2f} | Max: {p_max:.2f} bpm')
    print(f'  Threshold tau_i = max(100, mu + 2.5*sigma) = max(100, {mu_rest:.2f} + 2.5*{std_rest:.2f}) = {tau_i:.2f} bpm')
    print(f'Full Session Reference HR:')
    print(f'  Min: {hr_all_min:.2f} | Mean: {hr_all_mean:.2f} | Median: {hr_all_p50:.2f} | Max: {hr_all_max:.2f} bpm')
    print(f'  Fraction of full session with reference HR > 100 bpm: {np.mean(labels > 100.0) * 100:.2f}%')
    print(f'  Fraction of full session with reference HR > tau_i: {np.mean(labels > tau_i) * 100:.2f}%')
