"""
VitaSense AI - Standardized Alert Emitter Module
Protocol Amendment 4 (Section 1) - Temporal Persistence and Refractory Hold-off

Enforces:
1. Temporal Persistence (P in {10, 20, 30}s):
   An alert is emitted if and only if the arm's criteria hold continuously for at least
   P consecutive seconds (W_p = P / step_sec contiguous windows).
2. Refractory Hold-off (R = 60s):
   Following any emitted alert, an alarm refractory hold-off of R seconds (W_r = R / step_sec
   windows) is enforced, during which subsequent triggers are suppressed.
3. Shared Uniformity:
   Shared identically across all evaluated arms (Arms 1, 2, 3a, 3b, 3b-noMotion, 4).
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional
import numpy as np


@dataclass(frozen=True)
class AlertEmitterConfig:
    p_persist_sec: float = 10.0
    r_refractory_sec: float = 60.0
    step_sec: float = 2.0


class StandardAlertEmitter:
    """
    Standardized Alert Emitter shared across all ablation arms.
    Protocol Amendment 4 Section 1.
    """

    def __init__(
        self,
        p_persist_sec: float = 10.0,
        r_refractory_sec: float = 60.0,
        step_sec: float = 2.0,
    ):
        self.p_persist_sec = float(p_persist_sec)
        self.r_refractory_sec = float(r_refractory_sec)
        self.step_sec = float(step_sec)

        self.w_persist = max(1, int(round(self.p_persist_sec / self.step_sec)))
        self.w_refractory = max(0, int(round(self.r_refractory_sec / self.step_sec)))

    def emit(self, raw_condition: np.ndarray) -> np.ndarray:
        """
        Filters raw instantaneous binary condition into standardized emitted alerts.

        Parameters
        ----------
        raw_condition : np.ndarray of bool
            Instantaneous boolean condition per window (True where criteria are met).

        Returns
        -------
        emitted_alerts : np.ndarray of bool
            Boolean array of length N where True indicates an active emitted alert.
        """
        cond = np.asarray(raw_condition, dtype=bool)
        n = len(cond)
        emitted = np.zeros(n, dtype=bool)

        run_len = 0
        refractory_counter = 0

        for i in range(n):
            if refractory_counter > 0:
                refractory_counter -= 1

            if cond[i]:
                run_len += 1
                if run_len >= self.w_persist and refractory_counter == 0:
                    emitted[i] = True
                    refractory_counter = self.w_refractory
                    run_len = 0
            else:
                run_len = 0

        return emitted
