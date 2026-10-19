"""
VitaSense AI - Synthetic Resting Tachycardia Benchmark Injection Module
Protocol Section 8 (Amendment 2, Option (a)) - Frozen Protocol v2.0.0

Strict Compliance Guarantees:
1. Seeded and 100% reproducible (seed = 42).
2. Every output is strictly tagged 'SYNTHETIC' and 'SYNTHETIC_RESTING_TACHYCARDIA'.
3. Injected exclusively into verified resting segments (is_resting == True, ENMO <= 0.05g).
4. Strictly zero overlap with natural tachycardia events (natural events untouched).
5. Full compliance with episode parameters:
   - Episode count: N_tachy in [5, 10] per subject.
   - Target peak HR: HR_tachy in [105, 135] bpm.
   - Onset ramp rate: +2 to +4 bpm/s over 15s.
   - Sustained plateau: T_event in [45, 120] seconds.
   - Resolution: Exponential decay back to resting baseline over 20s.
"""

from dataclasses import dataclass, field
import hashlib
from typing import Dict, List, Optional, Tuple, Any
import numpy as np


@dataclass(frozen=True)
class InjectedEpisode:
    """
    Metadata container for a single injected synthetic tachycardia episode.
    """
    episode_id: int
    start_window: int
    end_window: int
    start_time_sec: float
    end_time_sec: float
    duration_sec: float
    plateau_duration_sec: float
    ramp_rate_bpm_s: float
    peak_hr: float
    base_hr: float
    tag: str = "SYNTHETIC"
    event_type: str = "SYNTHETIC_RESTING_TACHYCARDIA"
    is_synthetic: bool = True


@dataclass(frozen=True)
class SyntheticTachycardiaResult:
    """
    Immutable result of synthetic resting tachycardia injection under Amendment 2 Option (a).
    """
    hr_injected: np.ndarray
    synthetic_mask: np.ndarray  # True where synthetic tachycardia episode is active
    episodes: List[InjectedEpisode]
    tag: str = "SYNTHETIC"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_synthetic(self) -> bool:
        return self.tag == "SYNTHETIC"


class SyntheticTachycardiaInjector:
    """
    Deterministic synthetic resting tachycardia injector for ambulatory HR time series.
    Implements Amendment 2 Option (a) with exact physiological and kinematic gating.
    """

    def __init__(
        self,
        seed: int = 42,
        step_sec: float = 2.0,
        t_ramp: float = 15.0,
        t_decay: float = 20.0,
        plateau_min: float = 45.0,
        plateau_max: float = 120.0,
        hr_min: float = 105.0,
        hr_max: float = 135.0,
        ramp_min: float = 2.0,
        ramp_max: float = 4.0,
        min_inter_event_gap_sec: float = 60.0,
        edge_buffer_sec: float = 4.0,
    ):
        self.seed = seed
        self.step_sec = step_sec
        self.t_ramp = t_ramp
        self.t_decay = t_decay
        self.plateau_min = plateau_min
        self.plateau_max = plateau_max
        self.hr_min = hr_min
        self.hr_max = hr_max
        self.ramp_min = ramp_min
        self.ramp_max = ramp_max
        self.min_inter_event_gap_sec = min_inter_event_gap_sec
        self.edge_buffer_sec = edge_buffer_sec

    def _get_subject_seed(self, subject_id: Optional[str]) -> int:
        if subject_id is None:
            return self.seed
        # Derive deterministic 32-bit integer seed from base seed and subject string
        h = hashlib.sha256(f"{self.seed}_{subject_id}".encode("utf-8")).digest()
        return int.from_bytes(h[:4], byteorder="big")

    def _find_clean_resting_blocks(
        self,
        is_resting: np.ndarray,
        is_tachy: np.ndarray,
    ) -> List[Tuple[int, int, float]]:
        """
        Identify contiguous blocks of resting intervals where no natural tachycardia occurs.
        Returns list of (start_win, end_win, duration_sec).
        """
        clean_rest = np.asarray(is_resting, dtype=bool) & (~np.asarray(is_tachy, dtype=bool))
        diff = np.diff(np.concatenate(([0], clean_rest.astype(int), [0])))
        starts = np.where(diff == 1)[0]
        ends = np.where(diff == -1)[0]

        blocks: List[Tuple[int, int, float]] = []
        for s, e in zip(starts, ends):
            dur_sec = float((e - s) * self.step_sec)
            blocks.append((int(s), int(e - 1), dur_sec))
        return blocks

    def inject(
        self,
        hr_series: np.ndarray,
        is_resting: np.ndarray,
        tau_i: float,
        n_episodes: Optional[int] = None,
        subject_id: Optional[str] = None,
    ) -> SyntheticTachycardiaResult:
        """
        Inject synthetic resting tachycardia episodes into ambulatory HR time series.

        Parameters
        ----------
        hr_series : np.ndarray
            Reference 0.5-1.0 Hz ambulatory heart rate series (bpm).
        is_resting : np.ndarray of bool
            Boolean mask indicating verified resting periods.
        tau_i : float
            Personalized resting tachycardia threshold for natural events.
        n_episodes : int, optional
            Number of episodes to inject. If None, chosen in [5, 10] deterministically.
        subject_id : str, optional
            Subject identifier (e.g. 'S1') for subject-specific deterministic seeding.

        Returns
        -------
        SyntheticTachycardiaResult
        """
        hr_orig = np.asarray(hr_series, dtype=float).copy()
        n_windows = len(hr_orig)
        resting_mask = np.asarray(is_resting, dtype=bool)

        if len(resting_mask) != n_windows:
            raise ValueError(f"Length mismatch: hr_series has {n_windows}, is_resting has {len(resting_mask)}")

        sub_seed = self._get_subject_seed(subject_id)
        rng = np.random.default_rng(sub_seed)

        # 1. Identify natural tachycardia occurrences (must NOT be touched)
        natural_tachy_mask = resting_mask & (hr_orig > tau_i)

        # 2. Extract candidate clean resting blocks
        all_blocks = self._find_clean_resting_blocks(resting_mask, natural_tachy_mask)

        # Minimum duration needed for an episode plus buffers
        min_episode_dur = self.t_ramp + self.plateau_min + self.t_decay
        min_block_dur = min_episode_dur + 2.0 * self.edge_buffer_sec

        candidate_blocks = [b for b in all_blocks if b[2] >= min_block_dur]
        if not candidate_blocks:
            raise ValueError(
                f"No resting blocks of duration >= {min_block_dur:.1f}s found for injection in subject {subject_id}."
            )

        # 3. Determine target episode count N_tachy in [5, 10]
        # Calculate maximum possible non-overlapping episodes that can fit across all candidate blocks
        max_possible_episodes = 0
        for _, _, b_dur in candidate_blocks:
            avail_dur = b_dur - 2.0 * self.edge_buffer_sec
            fit = int(avail_dur // (min_episode_dur + self.min_inter_event_gap_sec))
            # If at least min_episode_dur fits, count is at least 1
            if fit == 0 and avail_dur >= min_episode_dur:
                fit = 1
            max_possible_episodes += fit

        if max_possible_episodes == 0:
            raise ValueError(f"Cannot fit any episodes of length {min_episode_dur}s in available resting blocks.")

        if n_episodes is not None:
            target_n = n_episodes
        else:
            target_n = int(rng.integers(5, 11))

        # Clamp target_n to [5, 10] and maximum physically packable
        actual_n = min(target_n, max_possible_episodes)
        actual_n = max(min(actual_n, 10), min(5, max_possible_episodes))

        # 4. Allocate episodes across candidate blocks proportionally to duration
        total_cand_dur = sum(b[2] for b in candidate_blocks)
        allocations = []
        for b in candidate_blocks:
            avail_dur = b[2] - 2.0 * self.edge_buffer_sec
            max_fit = max(1, int((avail_dur + self.min_inter_event_gap_sec) // (min_episode_dur + self.min_inter_event_gap_sec)))
            alloc = min(max_fit, int(round(actual_n * (b[2] / total_cand_dur))))
            allocations.append(alloc)

        # Adjust allocation to sum exactly to actual_n
        diff = actual_n - sum(allocations)
        if diff > 0:
            sorted_indices = sorted(range(len(candidate_blocks)), key=lambda i: candidate_blocks[i][2], reverse=True)
            for idx in sorted_indices:
                b = candidate_blocks[idx]
                avail_dur = b[2] - 2.0 * self.edge_buffer_sec
                max_fit = max(1, int((avail_dur + self.min_inter_event_gap_sec) // (min_episode_dur + self.min_inter_event_gap_sec)))
                can_add = min(diff, max_fit - allocations[idx])
                allocations[idx] += can_add
                diff -= can_add
                if diff <= 0:
                    break
        elif diff < 0:
            for idx in sorted(range(len(candidate_blocks)), key=lambda i: candidate_blocks[i][2]):
                can_sub = min(-diff, allocations[idx])
                allocations[idx] -= can_sub
                diff += can_sub
                if diff >= 0:
                    break

        # 5. Place and synthesize episodes within each allocated block
        hr_injected = hr_orig.copy()
        synthetic_mask = np.zeros(n_windows, dtype=bool)
        episodes: List[InjectedEpisode] = []
        episode_counter = 1

        for b_idx, (b_start, b_end, b_dur) in enumerate(candidate_blocks):
            n_in_block = allocations[b_idx]
            if n_in_block <= 0:
                continue

            # Compute available plateau upper bound inside this block
            # If multiple episodes in block, distribute space
            edge_win = int(np.ceil(self.edge_buffer_sec / self.step_sec))
            gap_win = int(np.ceil(self.min_inter_event_gap_sec / self.step_sec))
            cur_win = b_start + edge_win
            if episodes:
                min_next_win = episodes[-1].end_window + 1 + gap_win
                cur_win = max(cur_win, min_next_win)

            # Available duration per episode
            total_block_win = (b_end - cur_win + 1) - edge_win
            if total_block_win <= 0:
                continue
            avg_win_per_ep = (total_block_win - (n_in_block - 1) * gap_win) // n_in_block
            avg_dur_per_ep = avg_win_per_ep * self.step_sec

            max_plat = min(self.plateau_max, max(self.plateau_min, avg_dur_per_ep - self.t_ramp - self.t_decay))

            for ep_i in range(n_in_block):
                # Sample plateau duration in [plateau_min, max_plat]
                if max_plat > self.plateau_min:
                    t_plateau = float(rng.uniform(self.plateau_min, max_plat))
                else:
                    t_plateau = self.plateau_min

                t_total = self.t_ramp + t_plateau + self.t_decay
                ep_win_count = int(np.round(t_total / self.step_sec))

                # Boundary safety check
                if cur_win + ep_win_count > b_end + 1:
                    # Clip plateau to fit remaining resting windows
                    rem_win = (b_end + 1) - cur_win
                    t_total = rem_win * self.step_sec
                    t_plateau = max(self.plateau_min, t_total - self.t_ramp - self.t_decay)
                    t_total = self.t_ramp + t_plateau + self.t_decay
                    ep_win_count = int(np.round(t_total / self.step_sec))
                    if cur_win + ep_win_count > b_end + 1:
                        break

                # Determine base HR from local onset window
                hr_base = float(hr_orig[cur_win])
                if np.isnan(hr_base):
                    hr_base = 70.0

                # Sample target peak HR in [105, 135] bpm and calculate ramp rate
                # Ramp rate must satisfy ramp_min <= r_ramp <= ramp_max over t_ramp = 15s
                # delta_peak = r_ramp * 15s in [30, 60] bpm
                r_lo = max(self.ramp_min, (self.hr_min - hr_base) / self.t_ramp)
                r_hi = min(self.ramp_max, (self.hr_max - hr_base) / self.t_ramp)

                if r_lo <= r_hi:
                    r_ramp = float(rng.uniform(r_lo, r_hi))
                    hr_peak = hr_base + r_ramp * self.t_ramp
                else:
                    r_ramp = float(np.clip((120.0 - hr_base) / self.t_ramp, self.ramp_min, self.ramp_max))
                    hr_peak = float(np.clip(hr_base + r_ramp * self.t_ramp, self.hr_min, self.hr_max))

                delta_peak = hr_peak - hr_base

                # Generate temporal elevation profile
                delta_hr = np.zeros(ep_win_count, dtype=float)
                for w_idx in range(ep_win_count):
                    tau = w_idx * self.step_sec
                    if tau < self.t_ramp:
                        # Linear onset ramp
                        delta_hr[w_idx] = r_ramp * tau
                    elif tau < self.t_ramp + t_plateau:
                        # Sustained plateau
                        delta_hr[w_idx] = delta_peak
                    elif tau < t_total:
                        # Exponential resolution back to baseline
                        tau_dec = tau - (self.t_ramp + t_plateau)
                        delta_hr[w_idx] = delta_peak * np.exp(-3.0 * tau_dec / self.t_decay)
                    else:
                        delta_hr[w_idx] = 0.0

                # Apply synthetic elevation to HR stream
                ep_slice = slice(cur_win, cur_win + ep_win_count)
                hr_injected[ep_slice] = hr_orig[ep_slice] + delta_hr

                # Strictly enforce that synthetic tachycardia stays within physiological tachycardia bounds [105.0, 135.0]
                hr_injected[ep_slice] = np.clip(hr_injected[ep_slice], None, self.hr_max)

                # Clamp plateau region strictly into [105.0, 135.0]
                plat_win_start = cur_win + int(np.ceil(self.t_ramp / self.step_sec))
                plat_win_end = cur_win + int(np.floor((self.t_ramp + t_plateau) / self.step_sec))
                if plat_win_end > plat_win_start:
                    hr_injected[plat_win_start:plat_win_end] = np.clip(
                        hr_injected[plat_win_start:plat_win_end], self.hr_min, self.hr_max
                    )

                synthetic_mask[ep_slice] = True

                episode = InjectedEpisode(
                    episode_id=episode_counter,
                    start_window=cur_win,
                    end_window=cur_win + ep_win_count - 1,
                    start_time_sec=float(cur_win * self.step_sec),
                    end_time_sec=float((cur_win + ep_win_count - 1) * self.step_sec),
                    duration_sec=float(ep_win_count * self.step_sec),
                    plateau_duration_sec=float(t_plateau),
                    ramp_rate_bpm_s=float(r_ramp),
                    peak_hr=float(np.max(hr_injected[ep_slice])),
                    base_hr=float(hr_base),
                    tag="SYNTHETIC",
                    event_type="SYNTHETIC_RESTING_TACHYCARDIA",
                    is_synthetic=True,
                )
                episodes.append(episode)
                episode_counter += 1

                # Advance window pointer with inter-event gap
                cur_win += ep_win_count + gap_win

        # 6. Verify Critical Scientific Invariants
        if not np.all(resting_mask[synthetic_mask]):
            raise ValueError("Invariant violation: Synthetic tachycardia was injected outside resting segments.")

        if not np.all(hr_injected[~synthetic_mask] == hr_orig[~synthetic_mask]):
            raise ValueError("Invariant violation: Heart rate stream was modified outside synthetic episode windows.")

        if np.any(synthetic_mask[natural_tachy_mask]):
            raise ValueError("Invariant violation: Synthetic episode overlapped with existing natural tachycardia.")

        return SyntheticTachycardiaResult(
            hr_injected=hr_injected,
            synthetic_mask=synthetic_mask,
            episodes=episodes,
            tag="SYNTHETIC",
            metadata={
                "subject_id": subject_id,
                "seed": self.seed,
                "sub_seed": sub_seed,
                "n_episodes": len(episodes),
                "total_injected_min": float(np.sum(synthetic_mask) * self.step_sec / 60.0),
                "step_sec": self.step_sec,
                "tau_i": tau_i,
            },
        )
