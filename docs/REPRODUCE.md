# VitaSense AI - Reproducibility Guide

**Document Version:** 1.0.0  
**Date:** 2026-10-19  
**Status:** Protocol-Compliant Replication Specification  

This document provides exact, deterministic commands to verify datasets, rebuild intermediate feature caches, regenerate ground-truth alert injection schedules, reproduce every reported evaluation table, and execute the automated test suite.

---

## 1. Environment and Prerequisites

- **Python Version:** 3.10+ (tested on Python 3.13)
- **Core Dependencies:**
  - `numpy >= 1.24.0`
  - `scipy >= 1.10.0`
  - `pandas >= 2.0.0`
  - `pytest >= 8.0.0`
- **Working Directory:** Repository root (`d:\projects\health tracker`)

---

## 2. Dataset Versions and Checksums

All raw datasets are stored under `data/raw/` and are strictly excluded from git tracking.

### 2.1 Primary Wearable Benchmark Dataset: PPG-DaLiA
- **Repository:** UCI Machine Learning Repository
- **UCI Dataset ID:** 495
- **Version:** 2019
- **Citation URL:** https://archive.ics.uci.edu/dataset/495/ppg+dalia
- **Licence:** Creative Commons Attribution 4.0 International (CC BY 4.0)
- **Archive File:** `data/raw/ppg_dalia/ppg+dalia_full.zip`
- **Archive Size:** 2,865,111,320 bytes (2.67 GB)
- **Archive SHA-256:**
  ```
  5772387956e34e2e2dc4c2ddbeb98cb70569d5112fa4c13ee98a17680b84a1f3
  ```
- **Extracted Structure:**
  `data/raw/ppg_dalia/extracted/PPG_FieldStudy/S{1..15}/S{1..15}.pkl`
- **Subjects:** 15 subjects ($S_1$ to $S_{15}$), each containing synchronized Chest RespiBAN (700 Hz ECG gold standard, 3D ACC, Respiration) and Wrist Empatica E4 (64 Hz BVP, 32 Hz 3D ACC, 4 Hz EDA, 4 Hz TEMP).

### 2.2 Secondary Datasets
1. **UCI Heart Disease (Cleveland Clinic):**
   - **UCI Dataset ID:** 45
   - **Path:** `data/raw/uci_heart_disease/uci_heart_disease.csv`
   - **SHA-256:** `548eaf3b9d47152c9e0d25c167dc629740e8a4a13366a9be8fbd789ac3d2ebae`
2. **PhysioNet Wearable Stress and Exercise:**
   - **Version:** 1.0.1
   - **URL:** https://physionet.org/content/wearable-device-dataset/1.0.1/
   - **Path:** `data/raw/physionet_wearable/`
   - **Verification:** 707/708 data files verified against official PhysioNet `SHA256SUMS.txt`.

---

## 3. Deterministic Seeds

To guarantee bit-exact reproducibility across all platforms:
- **Master Pseudo-Random Seed:** `42`
- All seeded components:
  - `SyntheticTachycardiaInjector(seed=42)`
  - `FaultInjector(seed=42)`
  - `FaultScheduleGenerator(seed=42)`
  - Subject-level bootstrap resampling for 95% confidence intervals (`seed=42`, $B = 2000$ iterations)

---

## 4. Step-by-Step Reproduction Commands

Execute the following commands sequentially from the repository root:

### Step 1: Run Automated Test Suite
Asserts that all 60 protocol unit tests pass (including quarantine tests, leakage tests, estimator tests, scoring tests, and emitter tests):
```powershell
python -m pytest
```
*Expected Output:* `60 passed, 1 deselected` (1 integration test deselected unless explicitly invoked).

### Step 2: Build Clean PPG Feature Cache
Processes raw wrist BVP and 3D accelerometer signals for all 15 subjects through the Step 3a front-end spectral peak estimator ([WristPPGHREstimator](file:///d:/projects/health%20tracker/vitasense/estimators/ppg_hr_estimator.py)), computes 10-second rolling ENMO, spectral SQI, and pre-computed trust score inputs:
```powershell
python scripts/build_ppg_cache.py
```
- **Generated Outputs:**
  `data/processed/S1_ppg_cache.npz` through `data/processed/S15_ppg_cache.npz`.
- **Properties:** Verified identical checksums on successive runs.

### Step 3: Build F7 High-Motion Optical Noise Cache
Injects motion-modulated Gaussian noise at target $\text{SNR} = +5.0\text{ dB}$ directly into the raw 64 Hz optical BVP waveform, re-runs [WristPPGHREstimator](file:///d:/projects/health%20tracker/vitasense/estimators/ppg_hr_estimator.py) across the corrupted optical signal, and caches the resulting estimates separately:
```powershell
python scripts/build_f7_cache.py
```
- **Generated Outputs:**
  `data/processed/S1_f7_ppg_cache.npz` through `data/processed/S15_f7_ppg_cache.npz`.
- **Note:** Clean caches are strictly untouched and preserved.

### Step 4: Generate Synthetic Tachycardia Injection Audit
Injects 112 synthetic acute tachycardia episodes across clean resting periods ($S_1$ to $S_{15}$) conforming to Protocol Amendments 2, 3, and 4 (minimum inter-episode gap $\ge 60\text{s}$, adaptive plateau adjustment):
```powershell
python scripts/generate_injection_audit.py
```
- **Generated Outputs:**
  - `results/synthetic_injection_audit.csv`
  - `docs/synthetic_injection_audit.csv`
- **Audit Verification:** Confirms 112 valid episodes with minimum inter-episode gap $\ge 60.0\text{s}$.

### Step 5: Execute Complete Benchmark Suite
Runs the complete Leave-One-Subject-Out (LOSO) cross-validation harness across all 4 experimental conditions:
1. **Condition 0:** Clean background (no faults).
2. **Regime A:** Low fault-duty cycle ($\sim 10\%$ total faulted time, seeded pseudo-random schedule outside injected episodes).
3. **Regime B:** Nominal fault-duty cycle ($\sim 25\text{--}30\%$ total faulted time).
4. **F7:** Standalone high-motion optical BVP noise ($\text{SNR} = +5\text{ dB}$).

Command:
```powershell
python scripts/run_fault_regimes_benchmark.py
```

- **Output Sections Generated:**
  1. **Combined Benchmark Metric Table:** Event Recall %, Clean FA/hr, True Alert count, Clean False Alert count, Alert Precision, and $F_1$ score for Arms 1, 2, 3a, 3b, and 3b-noMotion across all 4 conditions.
  2. **Strata Tables:** Pooled All-15, Without-S5 (14 subjects), and Ambulatory High-Motion Stratum (S5, S6, S11).
  3. **Disaggregated Fault-Type Tables:** Exposure hours, alert counts, and FA/hr for F0_CLEAN and F1–F6 under Regimes A and B, with explicit `[Insufficient data]` flags for cells with $<10$ alerts or $<1.0\text{ h}$ exposure.
  4. **Pre-Specified Paired Comparisons (Arm 3b vs Arm 3a):** Per-subject recall and FA/hr differences, two-sided Wilcoxon signed-rank tests ($\alpha = 0.05$), Hodges-Lehmann median difference estimators, and 95% bootstrap confidence intervals across all 4 conditions.
  5. **Edge-of-Grid Boundary Analysis Table:** Exact fraction of 15 LOSO training folds selecting candidate grid boundary values for each arm and condition.

---

## 5. Summary of Key Files

| File Path | Description |
| :--- | :--- |
| `scripts/build_ppg_cache.py` | Clean feature cache builder (PPG estimator + ENMO + SQI) |
| `scripts/build_f7_cache.py` | F7 optical noise cache builder (raw BVP noise + estimator rerun) |
| `scripts/generate_injection_audit.py` | Generates 112-episode synthetic tachycardia audit CSVs |
| `scripts/run_fault_regimes_benchmark.py` | Comprehensive benchmark runner and table generator |
| `vitasense/benchmarks/fault_injection.py` | FaultInjector class (F1–F7 implementation) |
| `vitasense/benchmarks/fault_schedule.py` | Deterministic fault schedule generator (Regimes A & B) |
| `vitasense/benchmarks/alert_emitter.py` | StandardAlertEmitter with persistence $P$ and refractory $R = 60\text{s}$ |
| `vitasense/benchmarks/scoring.py` | Event-level scoring and false alert counting |
| `docs/RESULTS_SUMMARY.md` | Complete empirical findings, tables, and scientific limitations |
| `docs/protocol.md` | Frozen experimental protocol (Amendments 1–4) |
