"""
VitaSense AI - Synthetic Fault-Injection Benchmark Module
Protocol Table 2 Reference: Frozen Fault Taxonomy (F1 - F7)

Strict Compliance Guarantees:
1. Seeded and 100% reproducible.
2. Every output is strictly tagged 'SYNTHETIC' in data structures and metadata.
3. Implements all 7 fault categories with configurable severity:
   - F1_GAPS:  Contiguous missing gaps (NaN injection)
   - F2_STALE: Frozen / stale sensor lockup (zero variance)
   - F3_DUPL:  Duplicate packet / timestamp injection
   - F4_SPIKE: Transient impulsive spikes (+35 to +75 bpm)
   - F5_DRIFT: Linear baseline ramp drift
   - F6_UNIT:  Multiplicative unit/scale error
   - F7_NOISE: Additive noise with specified SNR
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, Tuple, Union
import numpy as np


class FaultType(str, Enum):
    F1_GAPS = "F1_GAPS"
    F2_STALE = "F2_STALE"
    F3_DUPL = "F3_DUPL"
    F4_SPIKE = "F4_SPIKE"
    F5_DRIFT = "F5_DRIFT"
    F6_UNIT = "F6_UNIT"
    F7_NOISE = "F7_NOISE"


class FaultSeverity(str, Enum):
    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"


@dataclass(frozen=True)
class SyntheticFaultResult:
    """
    Immutable container representing the result of a synthetic fault injection.
    Every single output is explicitly tagged 'SYNTHETIC'.
    """
    signal: np.ndarray
    synthetic_mask: np.ndarray  # True where synthetic fault was injected
    fault_type: FaultType
    severity: FaultSeverity
    tag: str = "SYNTHETIC"      # Non-negotiable scientific requirement
    timestamps: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_synthetic(self) -> bool:
        return self.tag == "SYNTHETIC"


class FaultInjector:
    """
    Deterministic, seeded fault injection engine for wearable physiological signals.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    def reset_seed(self, seed: Optional[int] = None) -> None:
        """Reset the random number generator for reproducible sweeps."""
        if seed is not None:
            self.seed = seed
        self._rng = np.random.default_rng(self.seed)

    def inject_gaps(
        self,
        signal: np.ndarray,
        fs: float,
        severity: FaultSeverity = FaultSeverity.MED,
        timestamps: Optional[np.ndarray] = None,
    ) -> SyntheticFaultResult:
        """
        F1_GAPS: Injects contiguous packet loss (NaN) into the signal.
        - Low:  5% drop rate, block duration = 10s
        - Med:  15% drop rate, block duration = 30s
        - High: 30% drop rate, block duration = 120s
        """
        cfg = {
            FaultSeverity.LOW: {"drop_ratio": 0.05, "gap_sec": 10.0},
            FaultSeverity.MED: {"drop_ratio": 0.15, "gap_sec": 30.0},
            FaultSeverity.HIGH: {"drop_ratio": 0.30, "gap_sec": 120.0},
        }[severity]

        out = signal.copy().astype(float)
        n = len(out)
        synthetic_mask = np.zeros(n, dtype=bool)

        gap_len = max(1, int(round(cfg["gap_sec"] * fs)))
        target_dropped = int(round(n * cfg["drop_ratio"]))

        current_dropped = 0
        max_attempts = 500
        attempts = 0

        while current_dropped < target_dropped and attempts < max_attempts:
            attempts += 1
            start_idx = self._rng.integers(0, max(1, n - gap_len))
            end_idx = min(n, start_idx + gap_len)

            # Avoid completely overlapping duplicate injections
            new_samples = np.sum(~synthetic_mask[start_idx:end_idx])
            if new_samples > 0:
                out[start_idx:end_idx] = np.nan
                synthetic_mask[start_idx:end_idx] = True
                current_dropped += new_samples

        meta = {
            "drop_ratio_requested": cfg["drop_ratio"],
            "actual_gap_fraction": float(np.mean(synthetic_mask)),
            "gap_duration_sec": cfg["gap_sec"],
            "seed": self.seed,
        }

        return SyntheticFaultResult(
            signal=out,
            synthetic_mask=synthetic_mask,
            fault_type=FaultType.F1_GAPS,
            severity=severity,
            timestamps=timestamps.copy() if timestamps is not None else None,
            metadata=meta,
        )

    def inject_stale(
        self,
        signal: np.ndarray,
        fs: float,
        severity: FaultSeverity = FaultSeverity.MED,
        timestamps: Optional[np.ndarray] = None,
    ) -> SyntheticFaultResult:
        """
        F2_STALE: Simulates sensor/buffer lockup by repeating the last valid value.
        - Low:  15s freeze
        - Med:  30s freeze
        - High: 60s freeze
        """
        freeze_sec = {
            FaultSeverity.LOW: 15.0,
            FaultSeverity.MED: 30.0,
            FaultSeverity.HIGH: 60.0,
        }[severity]

        out = signal.copy()
        n = len(out)
        synthetic_mask = np.zeros(n, dtype=bool)
        freeze_len = min(n - 1, max(2, int(round(freeze_sec * fs))))

        start_idx = self._rng.integers(0, max(1, n - freeze_len))
        end_idx = start_idx + freeze_len

        frozen_val = out[start_idx]
        out[start_idx:end_idx] = frozen_val
        synthetic_mask[start_idx:end_idx] = True

        meta = {
            "freeze_duration_sec": freeze_sec,
            "freeze_samples": freeze_len,
            "frozen_value": float(np.nanmean(frozen_val)),
            "frozen_variance": float(np.nanvar(out[start_idx:end_idx])),
            "seed": self.seed,
        }

        return SyntheticFaultResult(
            signal=out,
            synthetic_mask=synthetic_mask,
            fault_type=FaultType.F2_STALE,
            severity=severity,
            timestamps=timestamps.copy() if timestamps is not None else None,
            metadata=meta,
        )

    def inject_duplicates(
        self,
        signal: np.ndarray,
        severity: FaultSeverity = FaultSeverity.MED,
        timestamps: Optional[np.ndarray] = None,
    ) -> SyntheticFaultResult:
        """
        F3_DUPL: Injects packet/row duplicates with identical timestamps.
        - Low:  2% packets duplicated
        - Med:  5% packets duplicated
        - High: 15% packets duplicated
        """
        dup_ratio = {
            FaultSeverity.LOW: 0.02,
            FaultSeverity.MED: 0.05,
            FaultSeverity.HIGH: 0.15,
        }[severity]

        n = len(signal)
        n_dups = max(1, int(round(n * dup_ratio)))

        dup_indices = np.sort(self._rng.choice(n, size=n_dups, replace=False))

        # Insert duplicates into signal and timestamps
        out_signal = np.insert(signal, dup_indices, signal[dup_indices], axis=0)

        # Mark duplicates as synthetic
        synthetic_mask = np.zeros(len(out_signal), dtype=bool)
        # Positions of inserted elements in expanded array
        inserted_pos = dup_indices + np.arange(len(dup_indices))
        synthetic_mask[inserted_pos] = True

        out_timestamps = None
        if timestamps is not None:
            # Replicated timestamp (Delta t = 0)
            out_timestamps = np.insert(timestamps, dup_indices, timestamps[dup_indices])

        meta = {
            "dup_ratio_requested": dup_ratio,
            "num_duplicates_inserted": n_dups,
            "original_length": n,
            "expanded_length": len(out_signal),
            "seed": self.seed,
        }

        return SyntheticFaultResult(
            signal=out_signal,
            synthetic_mask=synthetic_mask,
            fault_type=FaultType.F3_DUPL,
            severity=severity,
            timestamps=out_timestamps,
            metadata=meta,
        )

    def inject_spikes(
        self,
        signal: np.ndarray,
        fs: float,
        severity: FaultSeverity = FaultSeverity.MED,
        timestamps: Optional[np.ndarray] = None,
    ) -> SyntheticFaultResult:
        """
        F4_SPIKE: Injects instantaneous motion impact / optical artifact spikes.
        - Low:  1 spike / 15 min (+35 bpm / units)
        - Med:  1 spike / 5 min  (+50 bpm / units)
        - High: 1 spike / 2 min  (+75 bpm / units)
        """
        cfg = {
            FaultSeverity.LOW: {"interval_sec": 900.0, "amplitude": 35.0},
            FaultSeverity.MED: {"interval_sec": 300.0, "amplitude": 50.0},
            FaultSeverity.HIGH: {"interval_sec": 120.0, "amplitude": 75.0},
        }[severity]

        out = signal.copy().astype(float)
        n = len(out)
        synthetic_mask = np.zeros(n, dtype=bool)

        duration_sec = n / fs
        num_spikes = max(1, int(round(duration_sec / cfg["interval_sec"])))

        spike_indices = self._rng.choice(n, size=min(num_spikes, n), replace=False)

        # Randomly choose positive or negative spike with prescribed amplitude
        signs = self._rng.choice([-1.0, 1.0], size=len(spike_indices))
        amplitudes = signs * cfg["amplitude"]

        out[spike_indices] += amplitudes
        synthetic_mask[spike_indices] = True

        meta = {
            "num_spikes": len(spike_indices),
            "spike_amplitude": cfg["amplitude"],
            "seed": self.seed,
        }

        return SyntheticFaultResult(
            signal=out,
            synthetic_mask=synthetic_mask,
            fault_type=FaultType.F4_SPIKE,
            severity=severity,
            timestamps=timestamps.copy() if timestamps is not None else None,
            metadata=meta,
        )

    def inject_drift(
        self,
        signal: np.ndarray,
        fs: float,
        severity: FaultSeverity = FaultSeverity.MED,
        duration_sec: float = 60.0,
        timestamps: Optional[np.ndarray] = None,
    ) -> SyntheticFaultResult:
        """
        F5_DRIFT: Injects linear baseline ramp drift x(t) = x_0(t) + alpha * t.
        - Low:  +0.05 units/s over 60s
        - Med:  +0.15 units/s over 60s
        - High: +0.30 units/s over 60s
        """
        slope = {
            FaultSeverity.LOW: 0.05,
            FaultSeverity.MED: 0.15,
            FaultSeverity.HIGH: 0.30,
        }[severity]

        out = signal.copy().astype(float)
        n = len(out)
        synthetic_mask = np.zeros(n, dtype=bool)

        drift_len = min(n, max(2, int(round(duration_sec * fs))))
        start_idx = self._rng.integers(0, max(1, n - drift_len))
        end_idx = start_idx + drift_len

        t_ramp = np.arange(drift_len) / fs
        ramp = slope * t_ramp

        out[start_idx:end_idx] += ramp
        synthetic_mask[start_idx:end_idx] = True

        meta = {
            "slope_units_per_sec": slope,
            "drift_duration_sec": duration_sec,
            "max_drift_offset": float(ramp[-1]),
            "seed": self.seed,
        }

        return SyntheticFaultResult(
            signal=out,
            synthetic_mask=synthetic_mask,
            fault_type=FaultType.F5_DRIFT,
            severity=severity,
            timestamps=timestamps.copy() if timestamps is not None else None,
            metadata=meta,
        )

    def inject_unit_error(
        self,
        signal: np.ndarray,
        severity: FaultSeverity = FaultSeverity.MED,
        duration_sec: Optional[float] = None,
        fs: float = 1.0,
        timestamps: Optional[np.ndarray] = None,
    ) -> SyntheticFaultResult:
        """
        F6_UNIT: Applies multiplicative scaling factor (e.g. firmware conversion error).
        - Low:  x 1.2
        - Med:  x 1.5
        - High: x 60.0 (Hz vs bpm or conversion error)
        """
        scale_factor = {
            FaultSeverity.LOW: 1.2,
            FaultSeverity.MED: 1.5,
            FaultSeverity.HIGH: 60.0,
        }[severity]

        out = signal.copy().astype(float)
        n = len(out)
        synthetic_mask = np.zeros(n, dtype=bool)

        if duration_sec is None:
            # Apply to entire signal
            out *= scale_factor
            synthetic_mask[:] = True
        else:
            block_len = min(n, max(1, int(round(duration_sec * fs))))
            start_idx = self._rng.integers(0, max(1, n - block_len))
            end_idx = start_idx + block_len
            out[start_idx:end_idx] *= scale_factor
            synthetic_mask[start_idx:end_idx] = True

        meta = {
            "scale_factor": scale_factor,
            "seed": self.seed,
        }

        return SyntheticFaultResult(
            signal=out,
            synthetic_mask=synthetic_mask,
            fault_type=FaultType.F6_UNIT,
            severity=severity,
            timestamps=timestamps.copy() if timestamps is not None else None,
            metadata=meta,
        )

    def inject_noise(
        self,
        signal: np.ndarray,
        severity: FaultSeverity = FaultSeverity.MED,
        motion_acc: Optional[np.ndarray] = None,
        timestamps: Optional[np.ndarray] = None,
    ) -> SyntheticFaultResult:
        """
        F7_NOISE: Injects high-motion noise at prescribed Signal-to-Noise Ratio (SNR).
        - Low:  SNR = +15 dB
        - Med:  SNR = +5 dB
        - High: SNR = -5 dB
        """
        snr_db = {
            FaultSeverity.LOW: 15.0,
            FaultSeverity.MED: 5.0,
            FaultSeverity.HIGH: -5.0,
        }[severity]

        out = signal.copy().astype(float)
        n = len(out)
        synthetic_mask = np.ones(n, dtype=bool)

        # Estimate clean signal variance (ignoring NaNs)
        clean_var = np.nanvar(signal)
        if clean_var <= 1e-12:
            clean_var = 1.0

        # SNR = 10 * log10(P_signal / P_noise) => P_noise = P_signal / 10^(SNR/10)
        noise_var = clean_var / (10.0 ** (snr_db / 10.0))
        noise_std = np.sqrt(noise_var)

        base_noise = self._rng.normal(0.0, noise_std, size=out.shape)

        if motion_acc is not None:
            # Modulate noise by accelerometer magnitude
            if motion_acc.ndim > 1:
                motion_energy = np.linalg.norm(motion_acc, axis=1)
            else:
                motion_energy = np.abs(motion_acc)
            # Normalize motion energy to mean 1.0
            norm_energy = motion_energy / (np.mean(motion_energy) + 1e-6)
            if len(norm_energy) == n:
                if out.ndim > 1:
                    norm_energy = norm_energy[:, None]
                base_noise = base_noise * norm_energy

        out += base_noise

        meta = {
            "snr_db_target": snr_db,
            "noise_std": float(noise_std),
            "motion_modulated": motion_acc is not None,
            "seed": self.seed,
        }

        return SyntheticFaultResult(
            signal=out,
            synthetic_mask=synthetic_mask,
            fault_type=FaultType.F7_NOISE,
            severity=severity,
            timestamps=timestamps.copy() if timestamps is not None else None,
            metadata=meta,
        )
