"""
VitaSense AI - Rule-Based Data-Quality and Trust-Score Module
Component B & C Core Module: Protocol Section 4 (Arms 3 & 4) and Section 6

Strict Requirements:
1. Exact determinism: identical inputs produce identical outputs every single time.
2. Multi-attribute quality evaluation:
   - S_gap:    Missingness / contiguous gap penalty
   - S_stale:  Zero-variance / flatline detector
   - S_phys:   Physiological bounds and rate-of-change limits
   - S_motion: Accelerometer dynamic motion energy attenuation
3. Hard-gate zeroing: flatlined, excessive missing, or out-of-bounds signals yield S_trust = 0.0.
4. Generates structured TrustScoreResult with actionable abstention recommendations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union
import numpy as np


@dataclass(frozen=True)
class TrustScoreResult:
    """
    Structured outcome of the rule-based trust score evaluation.
    """
    trust_score: float             # In range [0.0, 1.0]
    sub_scores: Dict[str, float]   # {'gap': ..., 'stale': ..., 'phys': ..., 'motion': ...}
    abstain: bool                  # True if trust score is below abstention threshold
    reasons: Tuple[str, ...] = ()  # Explanations for penalties or abstention
    metadata: Dict[str, float] = field(default_factory=dict)


class RuleBasedTrustScorer:
    """
    Deterministic rule-based signal quality index and trust score evaluator.
    """

    def __init__(
        self,
        hr_min_bpm: float = 35.0,
        hr_max_bpm: float = 220.0,
        max_hr_jump_bpm_s: float = 40.0,
        flatline_variance_eps: float = 1e-6,
        abstention_threshold: float = 0.70,
        rest_motion_threshold_g: float = 0.05,
        severe_motion_threshold_g: float = 0.30,
    ):
        self.hr_min_bpm = hr_min_bpm
        self.hr_max_bpm = hr_max_bpm
        self.max_hr_jump_bpm_s = max_hr_jump_bpm_s
        self.flatline_variance_eps = flatline_variance_eps
        self.abstention_threshold = abstention_threshold
        self.rest_motion_threshold_g = rest_motion_threshold_g
        self.severe_motion_threshold_g = severe_motion_threshold_g

    def evaluate_window(
        self,
        hr_window: np.ndarray,
        fs_hr: float = 1.0,
        acc_window: Optional[np.ndarray] = None,
        fs_acc: float = 32.0,
    ) -> TrustScoreResult:
        """
        Evaluates a window of heart rate and concurrent wrist accelerometer signal.
        Deterministic: no stochastic operations, pure function of inputs.
        """
        reasons: List[str] = []
        meta: Dict[str, float] = {}

        n_samples = len(hr_window)
        if n_samples == 0:
            return TrustScoreResult(
                trust_score=0.0,
                sub_scores={"gap": 0.0, "stale": 0.0, "phys": 0.0, "motion": 1.0},
                abstain=True,
                reasons=("empty_window",),
            )

        # -------------------------------------------------------------
        # 1. Gap / Missingness Check (S_gap)
        # -------------------------------------------------------------
        nan_count = int(np.sum(np.isnan(hr_window)))
        nan_ratio = nan_count / n_samples
        meta["nan_ratio"] = float(nan_ratio)

        if nan_ratio >= 0.50:
            s_gap = 0.0
            reasons.append(f"excessive_missing_gaps: {nan_ratio:.1%}")
        elif nan_ratio > 0.0:
            s_gap = max(0.0, 1.0 - 2.0 * nan_ratio)
            reasons.append(f"partial_missing_gaps: {nan_ratio:.1%}")
        else:
            s_gap = 1.0

        # Extract valid non-NaN samples for remaining checks
        valid_samples = hr_window[~np.isnan(hr_window)]

        # If all samples are NaN, return hard zero immediately
        if len(valid_samples) < 2:
            return TrustScoreResult(
                trust_score=0.0,
                sub_scores={"gap": 0.0, "stale": 0.0, "phys": 0.0, "motion": 1.0},
                abstain=True,
                reasons=("insufficient_valid_samples",),
                metadata=meta,
            )

        # -------------------------------------------------------------
        # 2. Flatline / Stale Check (S_stale)
        # -------------------------------------------------------------
        sample_var = float(np.var(valid_samples))
        meta["signal_variance"] = sample_var

        if sample_var < self.flatline_variance_eps:
            s_stale = 0.0
            reasons.append(f"sensor_flatline_stale_lockup: var={sample_var:.2e}")
        else:
            s_stale = 1.0

        # -------------------------------------------------------------
        # 3. Physiological Bounds & Rate-of-Change Check (S_phys)
        # -------------------------------------------------------------
        min_val = float(np.min(valid_samples))
        max_val = float(np.max(valid_samples))
        meta["hr_min"] = min_val
        meta["hr_max"] = max_val

        s_phys = 1.0
        if min_val < self.hr_min_bpm or max_val > self.hr_max_bpm:
            # Extreme out of bounds -> hard penalty
            s_phys = 0.0
            reasons.append(f"physiological_range_violation: min={min_val:.1f}, max={max_val:.1f}")
        else:
            # Check maximum instantaneous jump
            diffs = np.abs(np.diff(valid_samples))
            if len(diffs) > 0:
                max_diff = float(np.max(diffs))
                meta["max_instantaneous_jump"] = max_diff
                if max_diff > self.max_hr_jump_bpm_s:
                    s_phys = max(0.0, 1.0 - (max_diff - self.max_hr_jump_bpm_s) / 50.0)
                    reasons.append(f"non_physiological_rate_of_change: jump={max_diff:.1f} bpm")

        # -------------------------------------------------------------
        # 4. Kinematic Motion Artifact Penalty (S_motion)
        # -------------------------------------------------------------
        s_motion = 1.0
        if acc_window is not None and len(acc_window) > 0:
            if acc_window.ndim > 1 and acc_window.shape[1] == 3:
                # 3D Accelerometer magnitude
                acc_mag = np.linalg.norm(acc_window, axis=1)
            else:
                acc_mag = np.abs(acc_window).flatten()

            # Dynamic Acceleration: ENMO = max(0, ||a|| - 1.0g)
            enmo = np.maximum(0.0, acc_mag - 1.0)
            mean_enmo = float(np.mean(enmo))
            meta["mean_enmo_g"] = mean_enmo

            if mean_enmo <= self.rest_motion_threshold_g:
                # Resting / sedentary level motion: no penalty
                s_motion = 1.0
            elif mean_enmo >= self.severe_motion_threshold_g:
                # Severe physical exercise motion: high penalty
                s_motion = 0.20
                reasons.append(f"severe_motion_artifact: ENMO={mean_enmo:.3f}g")
            else:
                # Moderate motion: linear interpolation between 1.0 and 0.4
                norm_motion = (mean_enmo - self.rest_motion_threshold_g) / (
                    self.severe_motion_threshold_g - self.rest_motion_threshold_g
                )
                s_motion = float(1.0 - 0.60 * norm_motion)
                reasons.append(f"moderate_motion_artifact: ENMO={mean_enmo:.3f}g")

        # -------------------------------------------------------------
        # 5. Composite Score & Gating Rule
        # -------------------------------------------------------------
        sub_scores = {
            "gap": float(s_gap),
            "stale": float(s_stale),
            "phys": float(s_phys),
            "motion": float(s_motion),
        }

        # Hard failure in any critical signal attribute zeros the trust score
        if s_gap == 0.0 or s_stale == 0.0 or s_phys == 0.0:
            composite_score = 0.0
        else:
            # Multiplicative gating ensures every sub-score degrades overall confidence
            composite_score = float(s_gap * s_stale * s_phys * s_motion)

        composite_score = float(np.clip(composite_score, 0.0, 1.0))
        abstain = composite_score < self.abstention_threshold

        if abstain and not reasons:
            reasons.append(f"low_trust_score_below_threshold: {composite_score:.2f} < {self.abstention_threshold:.2f}")

        return TrustScoreResult(
            trust_score=composite_score,
            sub_scores=sub_scores,
            abstain=abstain,
            reasons=tuple(reasons),
            metadata=meta,
        )
