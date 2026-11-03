# VitaSense AI — Wearable Telemetry & Anomaly Monitoring Platform

[![Live App on Vercel](https://img.shields.io/badge/Frontend-Vercel%20Live-brightgreen)](https://vitasense-health-tracker.vercel.app)
[![API on Render](https://img.shields.io/badge/Backend-Render%20FastAPI-blue)](https://vitasense-backend-druv.onrender.com/docs)
[![Tests Passing](https://img.shields.io/badge/Tests-122%20Passed-success)](#testing--verification)
[![Paper PDF](https://img.shields.io/badge/IEEE%20Paper-PDF-red)](paper/conference_paper.pdf)

> **Paper Title:** *AI-Driven Integrated Healthcare Monitoring and Disease Risk Prediction Using Wearable Sensors and Machine Learning*  
> **Authors:** Department of Computer Science & Engineering, Vel Tech Rangarajan Dr. Sagunthala R&D Institute of Science and Technology, Chennai, India.

---

## 🌟 Overview

**VitaSense AI** is a full-stack, research-grade health monitoring and telemetry analysis platform. It addresses the critical industry challenge of **monitor alarm fatigue** caused by false resting tachycardia notifications in photoplethysmography (PPG) wristbands.

By combining real-time signal processing, kinematic stillness gating, dynamic Bayesian shrinkage baselines, and safety-aligned AI health companionship, VitaSense AI offers both:
1. **An Interactive Clinical Demonstration Suite:** Real-time dashboards, telemetry replay of authentic multi-activity human subjects, custom measurement entry, and localized health intelligence.
2. **A Reproducible Scientific Fault-Injection Benchmark:** 6 causal alerting arms rigorously evaluated across 15 ambulatory subjects (35.94 recording hours) from the public **PPG-DaLiA** benchmark dataset.

---

## 🔬 Core Scientific Findings

In our IEEE conference paper:
- **Kinematic Stillness Gating (Arm 3a):** Accounts for the largest share of false-alert suppression, reducing false alarms by **65.9% to 74.2%** relative to ungated individual baselines.
- **Multi-Attribute Software Trust Scoring (Arm 3b):** Multi-attribute SQIs provided **no statistically significant incremental benefit ($p \ge 0.28$)** over simple stillness gating.
- **Practical Takeaway for Wearables:** Embedded devices can achieve state-of-the-art false-alarm suppression with lightweight accelerometer motion gating without burning battery power on complex on-device heuristic software quality pipelines.

---

## 🤖 What the Gemini API Key Powers

The `GEMINI_API_KEY` configured in the backend powers the **VitaSense AI Companion** (`/api/assistant`), which provides:
- **Context-Aware Physiological Explanations:** Explains why heart rate or SpO₂ fluctuates based on real-time activity and time-series telemetry.
- **Educational Guidance:** Translates complex clinical metrics (HRV SDNN, resting heart rate reserve) into plain, reassuring human language.
- **Safety Boundaries & Emergency Guardrails:** Hard-coded guardrails prevent diagnostic prescribing, automatically detecting severe emergency cues (e.g. chest pain, fainting) and recommending urgent medical care.
- **Deterministic Offline Fallback:** If the Gemini API key is not supplied, the platform automatically switches to rule-based fallback responses, ensuring zero system crashes.

---

## 📂 Repository Architecture & Documentation

This repository contains the complete end-to-end source code, dataset processing pipelines, and research documentation:

```
├── paper/                      # Research Publication & Academic Artifacts
│   ├── conference_paper.tex    # Complete IEEEtran LaTeX source code
│   ├── conference_paper.pdf    # Camera-ready 6-page compiled publication PDF
│   ├── figures/                # Vector PDF figures, forest plots, and ROC curves
│   ├── tables/                 # LaTeX-formatted benchmark data tables
│   ├── verified_sources/       # Raw bibtex sources and citations audit
│   └── NUMBERS_PROVENANCE.csv  # Verified provenance for every number in the paper
│
├── docs/                       # Project Documentation & Protocols
│   ├── protocol.md             # Pre-specified fault-injection benchmark protocol
│   ├── PRD_TRACEABILITY.md     # Product requirement specifications & test traceability
│   ├── RESULTS_SUMMARY.md      # Numerical metrics across all evaluated arms & strata
│   ├── REPRODUCE.md            # Step-by-step reproduction instructions
│   └── ASSISTANT_SPEC.md       # AI companion intent routing & safety architecture
│
├── vitasense/                  # Python Backend Package (FastAPI)
│   ├── api/                    # REST endpoints (auth, measurements, alerts, replay, companion)
│   ├── benchmarks/             # 6-Arm alerting benchmark harness & LOSO CV engine
│   ├── estimators/             # Heart-rate tracking, bandpass filters & ENMO motion gate
│   └── quality/                # Multi-attribute signal quality trust scoring engine
│
├── src/                        # Frontend Application (React + TypeScript + Vite + Tailwind)
│   ├── components/             # Reusable UI widgets, interactive charts, and modals
│   ├── pages/                  # Dashboard, Signals Replay, Companion, Trends, Benchmark
│   └── api.ts                  # Centralized client routing (supports Vercel & Render)
│
├── tests/                      # Automated Test Suite (122 pytest test cases)
├── requirements.txt            # Production dependencies for Render
├── vercel.json                 # Single-page application rewrites for Vercel
└── package.json                # Frontend dependencies and build scripts
```

---

## 🚀 Live Deployments

- **Frontend (Vercel):** [https://vitasense-health-tracker.vercel.app](https://vitasense-health-tracker.vercel.app)
- **Backend API (Render):** [https://vitasense-backend-druv.onrender.com](https://vitasense-backend-druv.onrender.com)
- **Interactive Swagger Docs:** [https://vitasense-backend-druv.onrender.com/docs](https://vitasense-backend-druv.onrender.com/docs)

---

## 💻 Local Development Setup

### 1. Prerequisites
- **Python:** 3.11+ (or 3.12 / 3.13)
- **Node.js:** v18+ and npm

### 2. Backend Installation
```bash
# Clone the repository
git clone https://github.com/tejamarisetti/vitasense-health-tracker.git
cd vitasense-health-tracker

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Configure Environment
cp .env.example .env
# Edit .env with your optional GEMINI_API_KEY

# Start Backend Server
python -m uvicorn vitasense.api.app:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Frontend Installation
```bash
# In the project root:
npm install

# Start Vite Development Server
npm run dev
# Open http://localhost:5173
```

---

## 🧪 Testing & Verification

Run the full automated test suite (122 unit and integration tests covering signal quality, data leakage quarantine, authentication, and alerting arms):

```bash
# Run pytest
python -m pytest

# Run frontend build
npm run build
```

---

## ⚖️ Regulatory Notice & Clinical Disclaimer

VitaSense AI is strictly an **academic research software artifact** developed for educational demonstration, signal quality benchmarking, and physiological data exploration. It is **not** an FDA-cleared or CE-marked medical device. It must not be used for emergency medical diagnosis, clinical treatment decision-making, or life-critical patient monitoring.
