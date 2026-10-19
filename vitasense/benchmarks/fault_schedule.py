"""
VitaSense AI - Deterministic Fault Injection Schedule Module
Protocol Amendment 3 Section 5: Fault Taxonomy (F1 - F7) & Dual-Duty Regimes

Implements:
1. Condition 0: No-Fault / Clean Background.
2. Regime A: Low Fault-Duty (~10% total faulted non-event time).
   - F1 (Missing Gaps): 30s NaN blocks, 3% duty
   - F2 (Frozen / Stale): 30s flatline blocks, 2% duty
   - F3 (Duplicates): 1-window repeated packets, 2% duty
   - F4 (Transient Spikes): +50 bpm spike (1 window), rate = 1 per 15 min (~0.22% duty)
   - F5 (Baseline Drift): +0.15 bpm/s ramp over 60s (+9 bpm max), 1.5% duty
   - F6 (Unit / Scale): x1.5 scale over 60s blocks, 1.5% duty
   - Total faulted non-event time: ~10.0%.

3. Regime B: Nominal / Standard Fault-Duty (~25-30% total faulted non-event time).
   - F1 (Missing Gaps): 30s NaN blocks, 10% duty
   - F2 (Frozen / Stale): 30s flatline blocks, 5% duty
   - F3 (Duplicates): 1-window repeated packets, 5% duty
   - F4 (Transient Spikes): +50 bpm spike (1 window), rate = 1 per 5 min (~0.67% duty)
   - F5 (Baseline Drift): +0.15 bpm/s ramp over 60s (+9 bpm max), 5% duty
   - F6 (Unit / Scale): x1.5 scale over 60s blocks, 5% duty
   - Total faulted non-event time: ~25-30%.

Strict Guarantees:
1. Seeded determinism: seed=42 yields identical faults across runs.
2. Zero overlap with active injected episodes: active episodes are 100% untouched.
3. Every window receives an explicit fault label:
   'F0_CLEAN', 'F1_GAPS', 'F2_STALE', 'F3_DUPL', 'F4_SPIKE', 'F5_DRIFT', 'F6_UNIT'.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Sequence, Tuple, Any
import numpy as np


class FaultRegime(str, Enum):
    NO_FAULT = "NO_FAULT"
    REGIME_A = "REGIME_A"  # Low duty (~10%)
    REGIME_B = "REGIME_B"  # Nominal duty (~25-30%)


@dataclass(frozen=True)
class FaultScheduleResult:
    """Outcome of applying a fault regime to a subject's evaluation stream."""
    hr_faulted: np.ndarray
    fault_types: np.ndarray          # String array of length N with fault labels
    fault_mask: np.ndarray           # Boolean array: True where any fault F1..F6 is active
    regime: FaultRegime
    seed: int
    non_event_windows: int
    faulted_non_event_windows: int
    fault_duty_fraction: float       # Fraction of non-event windows that are faulted
    fault_disaggregated_windows: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


def apply_fault_schedule(
    hr_eval: np.ndarray,
    injected_episodes: Sequence[Any],
    regime: FaultRegime = FaultRegime.REGIME_A,
    seed: int = 42,
    step_sec: float = 2.0,
) -> FaultScheduleResult:
    """
    Applies the specified fault regime deterministically to the heart rate stream.
    Faults are applied exclusively to non-event background time (zero overlap with episodes).

    Parameters
    ----------
    hr_eval : np.ndarray
        Evaluated heart rate series (bpm).
    injected_episodes : Sequence of episode objects or dicts
        Must provide start_sec and end_sec (or start_time_sec, end_time_sec).
    regime : FaultRegime
        NO_FAULT, REGIME_A, or REGIME_B.
    seed : int
        RNG seed for reproducibility (nominal 42).
    step_sec : float
        Window step size in seconds (nominal 2.0s).
    """
    hr_arr = np.array(hr_eval, dtype=float, copy=True)
    n_windows = len(hr_arr)
    timestamps = np.arange(n_windows, dtype=np.float64) * step_sec

    # 1. Identify active injected episode windows (strictly protected from faults)
    is_injected = np.zeros(n_windows, dtype=bool)
    for ep in injected_episodes:
        if hasattr(ep, "start_time_sec") and hasattr(ep, "end_time_sec"):
            s, e = float(ep.start_time_sec), float(ep.end_time_sec)
        elif isinstance(ep, dict):
            s = float(ep.get("start_time_sec", ep.get("start_sec", 0.0)))
            e = float(ep.get("end_time_sec", ep.get("end_sec", 0.0)))
        elif isinstance(ep, (tuple, list)) and len(ep) >= 2:
            s, e = float(ep[0]), float(ep[1])
        else:
            continue
        is_injected |= (timestamps >= s) & (timestamps <= e)

    non_event_mask = ~is_injected
    n_bg = int(np.sum(non_event_mask))

    fault_types = np.full(n_windows, "F0_CLEAN", dtype="<U12")
    fault_mask = np.zeros(n_windows, dtype=bool)

    if regime == FaultRegime.NO_FAULT or n_bg == 0:
        return FaultScheduleResult(
            hr_faulted=hr_arr,
            fault_types=fault_types,
            fault_mask=fault_mask,
            regime=regime,
            seed=seed,
            non_event_windows=n_bg,
            faulted_non_event_windows=0,
            fault_duty_fraction=0.0,
            fault_disaggregated_windows={"F0_CLEAN": n_bg},
        )

    rng = np.random.default_rng(seed)

    # 2. Configure regime parameters per Amendment 3 Section 5
    if regime == FaultRegime.REGIME_A:
        # Target duty: ~10%
        cfg = {
            "F1_GAPS": {"len_sec": 30.0, "duty": 0.030},   # 3%
            "F2_STALE": {"len_sec": 30.0, "duty": 0.020},  # 2%
            "F3_DUPL": {"len_sec": 2.0, "duty": 0.020},    # 2%
            "F4_SPIKE": {"rate_per_min": 1.0 / 15.0},      # 1 per 15 min
            "F5_DRIFT": {"len_sec": 60.0, "duty": 0.015},  # 1.5%
            "F6_UNIT": {"len_sec": 60.0, "duty": 0.015},   # 1.5%
        }
    else:  # REGIME_B
        # Target duty: ~25-30%
        cfg = {
            "F1_GAPS": {"len_sec": 30.0, "duty": 0.100},   # 10%
            "F2_STALE": {"len_sec": 30.0, "duty": 0.050},  # 5%
            "F3_DUPL": {"len_sec": 2.0, "duty": 0.050},    # 5%
            "F4_SPIKE": {"rate_per_min": 1.0 / 5.0},       # 1 per 5 min
            "F5_DRIFT": {"len_sec": 60.0, "duty": 0.050},  # 5%
            "F6_UNIT": {"len_sec": 60.0, "duty": 0.050},   # 5%
        }

    # Available slots in background non-event time (must not overlap active episodes or other faults)
    available_mask = non_event_mask.copy()

    def place_blocks(block_len_windows: int, n_blocks: int, f_type: str) -> List[Tuple[int, int]]:
        placed = []
        if block_len_windows <= 0 or n_blocks <= 0:
            return placed

        # Find contiguous free slices in available_mask
        free_starts = []
        for i in range(n_windows - block_len_windows + 1):
            if np.all(available_mask[i : i + block_len_windows]):
                free_starts.append(i)

        if not free_starts:
            return placed

        rng.shuffle(free_starts)
        for start_idx in free_starts:
            end_idx = start_idx + block_len_windows
            if np.all(available_mask[start_idx:end_idx]):
                available_mask[start_idx:end_idx] = False
                fault_types[start_idx:end_idx] = f_type
                fault_mask[start_idx:end_idx] = True
                placed.append((start_idx, end_idx))
                if len(placed) >= n_blocks:
                    break
        return placed

    # --- Place F1_GAPS (30s NaN blocks) ---
    len_f1 = max(1, int(round(cfg["F1_GAPS"]["len_sec"] / step_sec)))
    n_blocks_f1 = max(1, int(round((n_bg * cfg["F1_GAPS"]["duty"]) / len_f1)))
    blocks_f1 = place_blocks(len_f1, n_blocks_f1, "F1_GAPS")
    for s_idx, e_idx in blocks_f1:
        hr_arr[s_idx:e_idx] = np.nan

    # --- Place F2_STALE (30s frozen blocks) ---
    len_f2 = max(1, int(round(cfg["F2_STALE"]["len_sec"] / step_sec)))
    n_blocks_f2 = max(1, int(round((n_bg * cfg["F2_STALE"]["duty"]) / len_f2)))
    blocks_f2 = place_blocks(len_f2, n_blocks_f2, "F2_STALE")
    for s_idx, e_idx in blocks_f2:
        val = hr_arr[s_idx - 1] if s_idx > 0 and np.isfinite(hr_arr[s_idx - 1]) else 75.0
        hr_arr[s_idx:e_idx] = val

    # --- Place F5_DRIFT (60s linear ramp +0.15 bpm/s) ---
    len_f5 = max(2, int(round(cfg["F5_DRIFT"]["len_sec"] / step_sec)))
    n_blocks_f5 = max(1, int(round((n_bg * cfg["F5_DRIFT"]["duty"]) / len_f5)))
    blocks_f5 = place_blocks(len_f5, n_blocks_f5, "F5_DRIFT")
    ramp_profile = 0.15 * (np.arange(len_f5) * step_sec)
    for s_idx, e_idx in blocks_f5:
        hr_arr[s_idx:e_idx] += ramp_profile

    # --- Place F6_UNIT (60s x1.5 scale factor) ---
    len_f6 = max(1, int(round(cfg["F6_UNIT"]["len_sec"] / step_sec)))
    n_blocks_f6 = max(1, int(round((n_bg * cfg["F6_UNIT"]["duty"]) / len_f6)))
    blocks_f6 = place_blocks(len_f6, n_blocks_f6, "F6_UNIT")
    for s_idx, e_idx in blocks_f6:
        hr_arr[s_idx:e_idx] *= 1.5

    # --- Place F3_DUPL (repeated packet / duplicate) ---
    len_f3 = 1
    n_blocks_f3 = max(1, int(round(n_bg * cfg["F3_DUPL"]["duty"])))
    blocks_f3 = place_blocks(len_f3, n_blocks_f3, "F3_DUPL")
    for s_idx, e_idx in blocks_f3:
        if s_idx > 0 and np.isfinite(hr_arr[s_idx - 1]):
            hr_arr[s_idx] = hr_arr[s_idx - 1]

    # --- Place F4_SPIKE (+50 bpm impulsive spike, 1 window) ---
    rate_per_min = cfg["F4_SPIKE"]["rate_per_min"]
    dur_min = (n_bg * step_sec) / 60.0
    n_spikes = max(1, int(round(dur_min * rate_per_min)))
    spikes = place_blocks(1, n_spikes, "F4_SPIKE")
    for s_idx, e_idx in spikes:
        hr_arr[s_idx] += 50.0

    faulted_bg_windows = int(np.sum(fault_mask & non_event_mask))
    duty_frac = float(faulted_bg_windows / n_bg) if n_bg > 0 else 0.0

    disagg = {}
    for ft in ["F0_CLEAN", "F1_GAPS", "F2_STALE", "F3_DUPL", "F4_SPIKE", "F5_DRIFT", "F6_UNIT"]:
        disagg[ft] = int(np.sum((fault_types == ft) & non_event_mask))

    return FaultScheduleResult(
        hr_faulted=hr_arr,
        fault_types=fault_types,
        fault_mask=fault_mask,
        regime=regime,
        seed=seed,
        non_event_windows=n_bg,
        faulted_non_event_windows=faulted_bg_windows,
        fault_duty_fraction=duty_frac,
        fault_disaggregated_windows=disagg,
        metadata={"total_windows": n_windows},
    )
