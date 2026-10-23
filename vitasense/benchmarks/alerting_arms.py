"""
VitaSense AI - Alerting Benchmark Arms 1 and 2 Implementation
Protocol Section 4 (Frozen Protocol v1.0.0) & Section 4/6 (Amendment 3)

Implements:
1. Arm 1: Fixed Threshold (Clinical Guideline Baseline)
   - Population threshold tau_pop in {100, 110, 120} bpm.
   - Alert triggers when HR_eval(t) > tau_pop.
   - Strictly zero personalization, zero signal quality checking, zero motion gating.

2. Arm 2: Personal Baseline with Shrinkage
   - Personalized threshold tau_i(t) = max(tau_floor, mu_hat(t) + k * sigma_hat(t)).
   - Candidate grids: k in {2.0, 2.5, 3.0}, kappa in {0.5, 1.0, 2.0} hours.
   - Empirical Bayes shrinkage:
       mu_hat(t) = w(t) * bar_x_i(t) + (1 - w(t)) * mu_pop
       sigma_hat(t) = w(t) * s_i(t) + (1 - w(t)) * sigma_pop
       w(t) = t_calib_hours(t) / (t_calib_hours(t) + kappa)
   - Deployment-only online calibration: strictly causal history of low-motion
     windows (ENMO_10s <= theta_rest and valid HR) observed up to window t.
   - Population prior (mu_pop, sigma_pop) is calibrated strictly inside training folds.

3. Strict Input Quarantine:
   - Evaluated alerting arms NEVER receive ground-truth activity labels, injector
     resting masks, ECG-derived tau_i, or injected episode times.
   - Built-in validation raises TypeError if any prohibited input is supplied.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Set
import numpy as np

from vitasense.benchmarks.alert_emitter import StandardAlertEmitter


PROHIBITED_INPUT_KEYS: Set[str] = {
    "activity",
    "activity_labels",
    "act_aligned",
    "is_resting",
    "resting_mask",
    "tau_i",
    "injected_episodes",
    "episodes",
    "episode_times",
    "synthetic_mask",
    "event_type",
    "label",
    "ecg_hr",
    "ecg_labels",
}


def validate_arm_inputs(**kwargs: Any) -> None:
    """
    Asserts that no prohibited ground-truth or placement variables are passed into an arm.
    Raises TypeError if any prohibited variable is detected per Amendment 3 Section 4.
    """
    for key in kwargs:
        if key.lower() in PROHIBITED_INPUT_KEYS:
            raise TypeError(
                f"Prohibited input detected: '{key}'. Protocol Amendment 3 Section 4 strictly "
                f"forbids alerting arms from receiving ground-truth activity labels, resting masks, "
                f"ECG-derived tau_i, or injected episode times."
            )


@dataclass(frozen=True)
class ArmOutput:
    """Standardized output of an alerting arm."""
    alert_mask: np.ndarray
    raw_alert_mask: Optional[np.ndarray] = None
    threshold_series: Optional[np.ndarray] = None
    abstain_mask: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class Arm1FixedThreshold:
    """
    Arm 1: Fixed Population Threshold Alerting (Clinical Guideline Baseline).
    Protocol Section 4.1, Amendment 3 Section 6.5 & Amendment 4 Section 3.
    Grid: tau_pop in {100.0, 110.0, 120.0, 125.0, 130.0} bpm.
    """

    def __init__(self, tau_pop: float = 100.0, **kwargs: Any):
        validate_arm_inputs(**kwargs)
        self.tau_pop = float(tau_pop)

    def predict(
        self,
        hr_series: np.ndarray,
        emitter: Optional[StandardAlertEmitter] = None,
        **kwargs: Any,
    ) -> ArmOutput:
        """
        Emits alert when hr_series > tau_pop, filtered through standardized emitter.

        Parameters
        ----------
        hr_series : np.ndarray
            Evaluated wrist-PPG heart rate time series (bpm).
        emitter : StandardAlertEmitter, optional
            Shared alert emitter enforcing persistence P and refractory R.
        """
        validate_arm_inputs(**kwargs)
        hr_arr = np.asarray(hr_series, dtype=float)
        raw_mask = (hr_arr > self.tau_pop) & np.isfinite(hr_arr)
        alert_mask = emitter.emit(raw_mask) if emitter is not None else raw_mask
        thresh = np.full(len(hr_arr), self.tau_pop, dtype=float)
        return ArmOutput(
            alert_mask=alert_mask,
            raw_alert_mask=raw_mask,
            threshold_series=thresh,
            abstain_mask=None,
            metadata={"arm": "Arm1_FixedThreshold", "tau_pop": self.tau_pop},
        )


def compute_causal_baseline_threshold_and_stats(
    hr_arr: np.ndarray,
    enmo_arr: np.ndarray,
    k: float,
    kappa_hours: float,
    mu_pop: float,
    sigma_pop: float,
    theta_rest: float = 0.05,
    tau_floor: float = 100.0,
    step_sec: float = 2.0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Computes personal threshold tau_i(t) alongside causal predictive mean mu_hat(t)
    and predictive standard deviation std_hat(t).
    """
    n = len(hr_arr)
    if len(enmo_arr) != n:
        raise ValueError(f"Length mismatch: hr_series ({n}) vs enmo_10s ({len(enmo_arr)})")

    is_calib = (enmo_arr <= theta_rest) & np.isfinite(hr_arr)
    c = is_calib.astype(int)
    x = np.where(is_calib, hr_arr, 0.0)
    x2 = np.where(is_calib, hr_arr ** 2, 0.0)

    # Strictly causal cumulative sums (strictly before window t)
    prior_c = np.concatenate(([0], np.cumsum(c)[:-1]))
    prior_x = np.concatenate(([0.0], np.cumsum(x)[:-1]))
    prior_x2 = np.concatenate(([0.0], np.cumsum(x2)[:-1]))

    # Personal sample mean and variance
    safe_c = np.maximum(1, prior_c)
    bar_x = np.where(prior_c > 0, prior_x / safe_c, mu_pop)

    safe_c_minus_1 = np.maximum(1, prior_c - 1)
    var_x = np.where(
        prior_c > 1,
        np.maximum(0.0, (prior_x2 - (prior_x ** 2) / safe_c) / safe_c_minus_1),
        sigma_pop ** 2,
    )
    std_x = np.sqrt(var_x)

    # Empirical Bayes shrinkage weights
    t_hours = prior_c * step_sec / 3600.0
    w = t_hours / (t_hours + kappa_hours)

    mu_hat = w * bar_x + (1.0 - w) * mu_pop
    std_hat = w * std_x + (1.0 - w) * sigma_pop

    # Dynamic personal threshold
    tau_series = np.maximum(tau_floor, mu_hat + k * std_hat)
    return tau_series, mu_hat, std_hat


def compute_causal_baseline_threshold(
    hr_arr: np.ndarray,
    enmo_arr: np.ndarray,
    k: float,
    kappa_hours: float,
    mu_pop: float,
    sigma_pop: float,
    theta_rest: float = 0.05,
    tau_floor: float = 100.0,
    step_sec: float = 2.0,
) -> np.ndarray:
    """
    Computes personal threshold tau_i(t) strictly causally from deployment-available
    low-motion windows (ENMO_10s <= theta_rest and valid HR) observed strictly before window t.
    Protocol Section 4.2 & Amendment 3 Section 6.3.
    """
    tau_series, _, _ = compute_causal_baseline_threshold_and_stats(
        hr_arr=hr_arr,
        enmo_arr=enmo_arr,
        k=k,
        kappa_hours=kappa_hours,
        mu_pop=mu_pop,
        sigma_pop=sigma_pop,
        theta_rest=theta_rest,
        tau_floor=tau_floor,
        step_sec=step_sec,
    )
    return tau_series


class Arm2PersonalBaselineShrinkage:
    """
    Arm 2: Personal Baseline with Cold-Start Shrinkage.
    Protocol Section 4.2 & Amendment 3 Section 6.3/6.5.

    Parameters
    ----------
    k : float
        Outlier multiplier in {2.0, 2.5, 3.0, 3.5, 4.0}.
    kappa_hours : float
        Shrinkage strength in {0.5, 1.0, 2.0} hours.
    mu_pop : float
        Population resting HR mean derived from training folds.
    sigma_pop : float
        Population resting HR std derived from training folds.
    theta_rest : float
        Kinematic stillness ENMO threshold (nominal 0.05g).
    tau_floor : float
        Minimum tachycardia threshold floor in bpm (nominal 100.0 bpm).
    step_sec : float
        Window step size in seconds (nominal 2.0s).
    """

    def __init__(
        self,
        k: float = 2.5,
        kappa_hours: float = 1.0,
        mu_pop: float = 75.0,
        sigma_pop: float = 15.0,
        theta_rest: float = 0.05,
        tau_floor: float = 100.0,
        step_sec: float = 2.0,
        **kwargs: Any,
    ):
        validate_arm_inputs(**kwargs)
        self.k = float(k)
        self.kappa_hours = float(kappa_hours)
        self.mu_pop = float(mu_pop)
        self.sigma_pop = float(sigma_pop)
        self.theta_rest = float(theta_rest)
        self.tau_floor = float(tau_floor)
        self.step_sec = float(step_sec)

    def predict(
        self,
        hr_series: np.ndarray,
        enmo_10s: np.ndarray,
        emitter: Optional[StandardAlertEmitter] = None,
        **kwargs: Any,
    ) -> ArmOutput:
        """
        Emits alert when hr_series > tau_i(t), filtered through standardized emitter.
        """
        validate_arm_inputs(**kwargs)
        hr_arr = np.asarray(hr_series, dtype=float)
        enmo_arr = np.asarray(enmo_10s, dtype=float)

        tau_series = compute_causal_baseline_threshold(
            hr_arr=hr_arr,
            enmo_arr=enmo_arr,
            k=self.k,
            kappa_hours=self.kappa_hours,
            mu_pop=self.mu_pop,
            sigma_pop=self.sigma_pop,
            theta_rest=self.theta_rest,
            tau_floor=self.tau_floor,
            step_sec=self.step_sec,
        )

        raw_mask = (hr_arr > tau_series) & np.isfinite(hr_arr)
        alert_mask = emitter.emit(raw_mask) if emitter is not None else raw_mask

        return ArmOutput(
            alert_mask=alert_mask,
            raw_alert_mask=raw_mask,
            threshold_series=tau_series,
            abstain_mask=None,
            metadata={
                "arm": "Arm2_PersonalBaselineShrinkage",
                "k": self.k,
                "kappa_hours": self.kappa_hours,
                "mu_pop": self.mu_pop,
                "sigma_pop": self.sigma_pop,
            },
        )


class Arm3aKinematicGate:
    """
    Arm 3a: Motion / Rest Gate Only (Kinematic Context Baseline).
    Protocol Section 4.3 & Amendment 3 Section 1.2 / 6.5.
    Combines Arm 2 personal baseline with dynamic accelerometer gating:
    raw alert triggers if and only if: (HR > tau_i) AND (ENMO_10s <= theta_rest).

    Grid: theta_rest in {0.03, 0.05, 0.08}g.
    """

    def __init__(
        self,
        k: float = 2.5,
        kappa_hours: float = 1.0,
        theta_rest: float = 0.05,
        mu_pop: float = 75.0,
        sigma_pop: float = 15.0,
        tau_floor: float = 100.0,
        step_sec: float = 2.0,
        **kwargs: Any,
    ):
        validate_arm_inputs(**kwargs)
        self.k = float(k)
        self.kappa_hours = float(kappa_hours)
        self.theta_rest = float(theta_rest)
        self.mu_pop = float(mu_pop)
        self.sigma_pop = float(sigma_pop)
        self.tau_floor = float(tau_floor)
        self.step_sec = float(step_sec)

    def predict(
        self,
        hr_series: np.ndarray,
        enmo_10s: np.ndarray,
        emitter: Optional[StandardAlertEmitter] = None,
        **kwargs: Any,
    ) -> ArmOutput:
        """
        Emits alert when (hr_series > tau_i(t)) AND (enmo_10s <= theta_rest).
        """
        validate_arm_inputs(**kwargs)
        hr_arr = np.asarray(hr_series, dtype=float)
        enmo_arr = np.asarray(enmo_10s, dtype=float)

        tau_series = compute_causal_baseline_threshold(
            hr_arr=hr_arr,
            enmo_arr=enmo_arr,
            k=self.k,
            kappa_hours=self.kappa_hours,
            mu_pop=self.mu_pop,
            sigma_pop=self.sigma_pop,
            theta_rest=0.05,  # Fixed nominal calibration stillness
            tau_floor=self.tau_floor,
            step_sec=self.step_sec,
        )

        raw_mask = (hr_arr > tau_series) & np.isfinite(hr_arr) & (enmo_arr <= self.theta_rest)
        alert_mask = emitter.emit(raw_mask) if emitter is not None else raw_mask

        return ArmOutput(
            alert_mask=alert_mask,
            raw_alert_mask=raw_mask,
            threshold_series=tau_series,
            abstain_mask=None,
            metadata={
                "arm": "Arm3a_KinematicGate",
                "k": self.k,
                "kappa_hours": self.kappa_hours,
                "theta_rest": self.theta_rest,
                "mu_pop": self.mu_pop,
                "sigma_pop": self.sigma_pop,
            },
        )


class Arm3bTrustScoreGate:
    """
    Arm 3b: Multi-Attribute Trust Score Gate.
    Protocol Section 4.4 & Amendment 3 Section 1.2 / 6.5.
    Combines Arm 2 personal baseline with multi-attribute trust score gating:
    raw alert triggers if and only if: (HR > tau_i) AND (S_trust >= theta_trust).

    Grid: theta_trust in {0.60, 0.70, 0.80}.
    """

    def __init__(
        self,
        k: float = 2.5,
        kappa_hours: float = 1.0,
        theta_trust: float = 0.70,
        mu_pop: float = 75.0,
        sigma_pop: float = 15.0,
        tau_floor: float = 100.0,
        step_sec: float = 2.0,
        **kwargs: Any,
    ):
        validate_arm_inputs(**kwargs)
        self.k = float(k)
        self.kappa_hours = float(kappa_hours)
        self.theta_trust = float(theta_trust)
        self.mu_pop = float(mu_pop)
        self.sigma_pop = float(sigma_pop)
        self.tau_floor = float(tau_floor)
        self.step_sec = float(step_sec)

    def predict(
        self,
        hr_series: np.ndarray,
        enmo_10s: np.ndarray,
        trust_series: np.ndarray,
        emitter: Optional[StandardAlertEmitter] = None,
        **kwargs: Any,
    ) -> ArmOutput:
        """
        Emits alert when (hr_series > tau_i(t)) AND (trust_series >= theta_trust).
        """
        validate_arm_inputs(**kwargs)
        hr_arr = np.asarray(hr_series, dtype=float)
        enmo_arr = np.asarray(enmo_10s, dtype=float)
        trust_arr = np.asarray(trust_series, dtype=float)

        tau_series = compute_causal_baseline_threshold(
            hr_arr=hr_arr,
            enmo_arr=enmo_arr,
            k=self.k,
            kappa_hours=self.kappa_hours,
            mu_pop=self.mu_pop,
            sigma_pop=self.sigma_pop,
            theta_rest=0.05,
            tau_floor=self.tau_floor,
            step_sec=self.step_sec,
        )

        raw_mask = (hr_arr > tau_series) & np.isfinite(hr_arr) & (trust_arr >= self.theta_trust)
        alert_mask = emitter.emit(raw_mask) if emitter is not None else raw_mask

        return ArmOutput(
            alert_mask=alert_mask,
            raw_alert_mask=raw_mask,
            threshold_series=tau_series,
            abstain_mask=None,
            metadata={
                "arm": "Arm3b_TrustScoreGate",
                "k": self.k,
                "kappa_hours": self.kappa_hours,
                "theta_trust": self.theta_trust,
                "mu_pop": self.mu_pop,
                "sigma_pop": self.sigma_pop,
            },
        )


class Arm3bNoMotionGate:
    """
    Arm 3b-noMotion: Trust Score Gate Without Motion.
    Protocol Amendment 3 Section 1.3 & Section 6.5.
    Evaluates multi-attribute trust score evaluated without the motion term:
    raw alert triggers if and only if: (HR > tau_i) AND (S_trust,noMotion >= theta_trust).

    Grid: theta_trust in {0.60, 0.70, 0.80}.
    """

    def __init__(
        self,
        k: float = 2.5,
        kappa_hours: float = 1.0,
        theta_trust: float = 0.70,
        mu_pop: float = 75.0,
        sigma_pop: float = 15.0,
        tau_floor: float = 100.0,
        step_sec: float = 2.0,
        **kwargs: Any,
    ):
        validate_arm_inputs(**kwargs)
        self.k = float(k)
        self.kappa_hours = float(kappa_hours)
        self.theta_trust = float(theta_trust)
        self.mu_pop = float(mu_pop)
        self.sigma_pop = float(sigma_pop)
        self.tau_floor = float(tau_floor)
        self.step_sec = float(step_sec)

    def predict(
        self,
        hr_series: np.ndarray,
        enmo_10s: np.ndarray,
        trust_no_motion_series: np.ndarray,
        emitter: Optional[StandardAlertEmitter] = None,
        **kwargs: Any,
    ) -> ArmOutput:
        """
        Emits alert when (hr_series > tau_i(t)) AND (trust_no_motion_series >= theta_trust).
        """
        validate_arm_inputs(**kwargs)
        hr_arr = np.asarray(hr_series, dtype=float)
        enmo_arr = np.asarray(enmo_10s, dtype=float)
        trust_nomot_arr = np.asarray(trust_no_motion_series, dtype=float)

        tau_series = compute_causal_baseline_threshold(
            hr_arr=hr_arr,
            enmo_arr=enmo_arr,
            k=self.k,
            kappa_hours=self.kappa_hours,
            mu_pop=self.mu_pop,
            sigma_pop=self.sigma_pop,
            theta_rest=0.05,
            tau_floor=self.tau_floor,
            step_sec=self.step_sec,
        )

        raw_mask = (hr_arr > tau_series) & np.isfinite(hr_arr) & (trust_nomot_arr >= self.theta_trust)
        alert_mask = emitter.emit(raw_mask) if emitter is not None else raw_mask

        return ArmOutput(
            alert_mask=alert_mask,
            raw_alert_mask=raw_mask,
            threshold_series=tau_series,
            abstain_mask=None,
            metadata={
                "arm": "Arm3b_NoMotionGate",
                "k": self.k,
                "kappa_hours": self.kappa_hours,
                "theta_trust": self.theta_trust,
                "mu_pop": self.mu_pop,
                "sigma_pop": self.sigma_pop,
            },
        )


class Arm4ConformalAbstention:
    """
    Arm 4: Conformal Prediction / Multi-attribute Trust Abstention.
    Protocol Amendment 3 Section 6.

    Combines:
    1. Causal personal baseline threshold tau_i(t) = max(tau_floor, mu_hat(t) + k * std_hat(t))
    2. Predictive uncertainty U(t) = std_hat(t) / max(1.0, mu_hat(t))
    3. Augmented uncertainty U_total(t) = U(t) + lambda_trust * (1.0 - S_trust(t))
    4. Conformal nonconformity scores on training calibration set (low-motion windows):
       s(t) = |HR(t) - mu_hat(t)| / max(1.0, std_hat(t))
    5. Conformal quantile q_calib = Quantile_(1-alpha)({s(t)})
    6. Prediction interval [mu_hat(t) - q_calib * std_hat(t), mu_hat(t) + q_calib * std_hat(t)]
    7. Abstention rule:
       Abstain (suppress alert) if:
       a) Prediction interval spans threshold tau_i(t), OR
       b) Augmented uncertainty U_total(t) > theta_unc
    8. Alert fires if:
       (HR(t) > tau_i(t)) AND NOT Abstain
       Filtered through StandardAlertEmitter(P, R=60s).

    Candidate Grids:
    - alpha in {0.05, 0.10}
    - lambda_trust in {0.5, 1.0}
    - theta_unc in {0.20, 0.30}
    """

    def __init__(
        self,
        k: float = 2.5,
        kappa_hours: float = 1.0,
        alpha: float = 0.10,
        lambda_trust: float = 0.5,
        theta_unc: float = 0.30,
        q_calib: float = 1.96,
        mu_pop: float = 75.0,
        sigma_pop: float = 15.0,
        tau_floor: float = 100.0,
        step_sec: float = 2.0,
        **kwargs: Any,
    ):
        validate_arm_inputs(**kwargs)
        self.k = float(k)
        self.kappa_hours = float(kappa_hours)
        self.alpha = float(alpha)
        self.lambda_trust = float(lambda_trust)
        self.theta_unc = float(theta_unc)
        self.q_calib = float(q_calib)
        self.mu_pop = float(mu_pop)
        self.sigma_pop = float(sigma_pop)
        self.tau_floor = float(tau_floor)
        self.step_sec = float(step_sec)

    def predict(
        self,
        hr_series: np.ndarray,
        enmo_10s: np.ndarray,
        trust_series: np.ndarray,
        emitter: Optional[StandardAlertEmitter] = None,
        **kwargs: Any,
    ) -> ArmOutput:
        """
        Emits alert when (hr_series > tau_i(t)) AND NOT abstained by conformal interval / trust defect.
        """
        validate_arm_inputs(**kwargs)
        hr_arr = np.asarray(hr_series, dtype=float)
        enmo_arr = np.asarray(enmo_10s, dtype=float)
        trust_arr = np.asarray(trust_series, dtype=float)

        tau_series, mu_hat, std_hat = compute_causal_baseline_threshold_and_stats(
            hr_arr=hr_arr,
            enmo_arr=enmo_arr,
            k=self.k,
            kappa_hours=self.kappa_hours,
            mu_pop=self.mu_pop,
            sigma_pop=self.sigma_pop,
            theta_rest=0.05,
            tau_floor=self.tau_floor,
            step_sec=self.step_sec,
        )

        safe_mu = np.maximum(1.0, mu_hat)
        safe_std = np.maximum(1.0, std_hat)
        u_t = safe_std / safe_mu
        u_total = u_t + self.lambda_trust * (1.0 - trust_arr)

        band_lo = mu_hat - self.q_calib * safe_std
        band_hi = mu_hat + self.q_calib * safe_std

        # Abstain if prediction band spans threshold or augmented uncertainty exceeds threshold
        spans_tau = (band_lo <= tau_series) & (tau_series <= band_hi)
        excessive_unc = (u_total > self.theta_unc)
        abstain_mask = spans_tau | excessive_unc

        raw_mask = (hr_arr > tau_series) & np.isfinite(hr_arr) & (~abstain_mask)
        alert_mask = emitter.emit(raw_mask) if emitter is not None else raw_mask

        return ArmOutput(
            alert_mask=alert_mask,
            raw_alert_mask=raw_mask,
            threshold_series=tau_series,
            abstain_mask=abstain_mask,
            metadata={
                "arm": "Arm4_ConformalAbstention",
                "k": self.k,
                "kappa_hours": self.kappa_hours,
                "alpha": self.alpha,
                "lambda_trust": self.lambda_trust,
                "theta_unc": self.theta_unc,
                "q_calib": self.q_calib,
                "mu_pop": self.mu_pop,
                "sigma_pop": self.sigma_pop,
            },
        )


