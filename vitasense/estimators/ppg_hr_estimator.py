"""
VitaSense AI - Documented Wrist-PPG Heart Rate Estimator
Baseline for Component C (Trust Score vs Reference Error Calibration)

Algorithm Specification:
1. Input:
   - Raw Wrist Photoplethysmogram (BVP) sampled at fs = 64 Hz.
   - Concurrent 3D Wrist Accelerometer (ACC) sampled at fs = 32 Hz.
2. Preprocessing:
   - 4th-order zero-phase Butterworth bandpass filter: [0.7 Hz, 3.5 Hz] (42 to 210 bpm).
3. Sliding Window Segmentation:
   - Window duration = 8.0 seconds (512 samples @ 64 Hz).
   - Window step = 2.0 seconds (128 samples @ 64 Hz), aligned with PPG-DaLiA benchmark.
4. Periodogram & Spectral Peak Tracking:
   - Zero-padded FFT (N_fft = 4096) for frequency resolution Delta f ~ 0.9375 bpm.
   - Cardiac dominant frequency f_peak identification in [0.7, 3.5] Hz.
   - Estimated HR_ppg = f_peak * 60 (bpm).
5. Signal Quality Index (Spectral Purity):
   - Power ratio Q = Power(f_peak +/- 0.15 Hz) / Total_Power(0.7 - 3.5 Hz).
   - If Q < 0.20 or signal is missing/flatline, returns None / NaN (coverage tracking).
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import signal as sp_signal


@dataclass(frozen=True)
class PPGHRWindowEstimate:
    """Estimated heart rate and spectral confidence for an analysis window."""
    timestamp_sec: float
    hr_bpm: Optional[float]
    spectral_sqi: float         # Ratio of power in peak to cardiac band [0.0, 1.0]
    dominant_freq_hz: float
    is_valid: bool
    rejection_reason: Optional[str] = None


class WristPPGHREstimator:
    """
    Standard spectral wrist-PPG heart rate estimator.
    Evaluates 8.0s windows every 2.0s to compute continuous HR estimates.
    """

    def __init__(
        self,
        fs_ppg: float = 64.0,
        fs_acc: float = 32.0,
        window_sec: float = 8.0,
        step_sec: float = 2.0,
        lowcut_hz: float = 0.70,   # 42 bpm
        highcut_hz: float = 3.50,  # 210 bpm
        n_fft: int = 4096,
        min_sqi_threshold: float = 0.15,
    ):
        self.fs_ppg = fs_ppg
        self.fs_acc = fs_acc
        self.window_sec = window_sec
        self.step_sec = step_sec
        self.lowcut_hz = lowcut_hz
        self.highcut_hz = highcut_hz
        self.n_fft = n_fft
        self.min_sqi_threshold = min_sqi_threshold

        # Design Butterworth bandpass filter
        nyq = 0.5 * fs_ppg
        low = lowcut_hz / nyq
        high = highcut_hz / nyq
        self.b_bandpass, self.a_bandpass = sp_signal.butter(4, [low, high], btype="bandpass")

    def filter_signal(self, bvp_signal: np.ndarray) -> np.ndarray:
        """Applies 4th-order zero-phase Butterworth filter."""
        # Handle 1D or (N, 1) inputs
        sig = bvp_signal.flatten().astype(float)
        # If signal contains NaNs or is too short, return as-is
        if len(sig) < 30 or np.isnan(sig).any():
            return sig
        return sp_signal.filtfilt(self.b_bandpass, self.a_bandpass, sig)

    def estimate_window(self, bvp_window: np.ndarray, timestamp_sec: float) -> PPGHRWindowEstimate:
        """
        Estimates heart rate from an 8.0s window of raw BVP signal.
        """
        win = bvp_window.flatten().astype(float)

        # 1. Missingness / flatline checks
        if np.isnan(win).any():
            return PPGHRWindowEstimate(
                timestamp_sec=timestamp_sec,
                hr_bpm=None,
                spectral_sqi=0.0,
                dominant_freq_hz=0.0,
                is_valid=False,
                rejection_reason="contains_nan",
            )

        var = np.var(win)
        if var < 1e-6:
            return PPGHRWindowEstimate(
                timestamp_sec=timestamp_sec,
                hr_bpm=None,
                spectral_sqi=0.0,
                dominant_freq_hz=0.0,
                is_valid=False,
                rejection_reason="flatline_zero_variance",
            )

        # 2. Zero-mean and windowing (Hanning)
        win_detrend = win - np.mean(win)
        hanning = np.hanning(len(win_detrend))
        windowed = win_detrend * hanning

        # 3. Zero-padded FFT
        fft_vals = np.fft.rfft(windowed, n=self.n_fft)
        freqs = np.fft.rfftfreq(self.n_fft, d=1.0 / self.fs_ppg)
        power = np.abs(fft_vals) ** 2

        # 4. Restrict to physiological cardiac band [0.7, 3.5] Hz
        band_mask = (freqs >= self.lowcut_hz) & (freqs <= self.highcut_hz)
        band_freqs = freqs[band_mask]
        band_power = power[band_mask]

        if len(band_power) == 0 or np.sum(band_power) < 1e-12:
            return PPGHRWindowEstimate(
                timestamp_sec=timestamp_sec,
                hr_bpm=None,
                spectral_sqi=0.0,
                dominant_freq_hz=0.0,
                is_valid=False,
                rejection_reason="zero_band_power",
            )

        # 5. Dominant cardiac peak
        peak_idx = np.argmax(band_power)
        f_peak = band_freqs[peak_idx]
        hr_bpm = f_peak * 60.0

        # 6. Spectral purity / SQI
        peak_window_mask = (freqs >= f_peak - 0.15) & (freqs <= f_peak + 0.15)
        peak_power = np.sum(power[peak_window_mask])
        total_band_power = np.sum(band_power)

        spectral_sqi = float(np.clip(peak_power / (total_band_power + 1e-12), 0.0, 1.0))
        is_valid = spectral_sqi >= self.min_sqi_threshold

        return PPGHRWindowEstimate(
            timestamp_sec=timestamp_sec,
            hr_bpm=float(hr_bpm) if is_valid else None,
            spectral_sqi=spectral_sqi,
            dominant_freq_hz=float(f_peak),
            is_valid=is_valid,
            rejection_reason=None if is_valid else f"low_spectral_purity_{spectral_sqi:.2f}",
        )

    def estimate_stream(
        self,
        bvp_signal: np.ndarray,
        total_windows: Optional[int] = None,
    ) -> List[PPGHRWindowEstimate]:
        """
        Processes continuous BVP signal with 8.0s window shifted by 2.0s.
        Filtered first with 4th-order zero-phase Butterworth filter.
        """
        filtered_bvp = self.filter_signal(bvp_signal)
        win_len = int(round(self.window_sec * self.fs_ppg))
        step_len = int(round(self.step_sec * self.fs_ppg))
        n_samples = len(filtered_bvp)

        estimates: List[PPGHRWindowEstimate] = []
        i = 0
        start = 0

        while start + win_len <= n_samples:
            if total_windows is not None and i >= total_windows:
                break
            win = filtered_bvp[start : start + win_len]
            t_sec = i * self.step_sec
            est = self.estimate_window(win, timestamp_sec=t_sec)
            estimates.append(est)
            start += step_len
            i += 1

        return estimates
