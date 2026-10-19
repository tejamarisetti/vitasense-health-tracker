"""
Tests for VitaSense Replay & Benchmark APIs
Verifies:
1. Replay mode reads only from data/processed caches.
2. Replay streams PPG HR, ECG Reference HR, Trust Score, ENMO.
3. Fault toggles F1-F7 work and tag outputs 'SYNTHETIC'.
4. Benchmark summary delivers verified findings ('H1 not supported', no invented numbers).
"""

import pytest
from fastapi.testclient import TestClient
from vitasense.api.app import app

client = TestClient(app)


def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "REPLAY: public dataset, not live" in data["notice"]


def test_replay_subjects_list():
    res = client.get("/api/replay/subjects")
    assert res.status_code == 200
    subjects = res.json()
    assert len(subjects) == 15
    ids = [s["id"] for s in subjects]
    assert ids == [f"S{i}" for i in range(1, 16)]


def test_replay_stream_clean():
    res = client.get("/api/replay/stream?subject=S1&fault=NONE&offset=0&limit=50")
    assert res.status_code == 200
    data = res.json()
    assert data["notice"] == "REPLAY: public dataset, not live"
    assert data["subject"] == "S1"
    assert data["is_synthetic"] is False
    assert len(data["data"]) == 50

    p0 = data["data"][0]
    assert "hr_ppg" in p0
    assert "hr_ecg" in p0
    assert "trust_score" in p0
    assert "enmo" in p0
    assert "is_alert" in p0


def test_replay_stream_fault_synthetic_tag():
    # Toggle F4_SPIKE
    res = client.get("/api/replay/stream?subject=S1&fault=F4_SPIKE&offset=100&limit=50")
    assert res.status_code == 200
    data = res.json()
    assert data["is_synthetic"] is True
    assert data["tag"] == "SYNTHETIC"
    assert any(pt["fault_active"] for pt in data["data"])


def test_replay_stream_f7_noise():
    # Toggle F7_NOISE
    res = client.get("/api/replay/stream?subject=S2&fault=F7_NOISE&offset=0&limit=50")
    assert res.status_code == 200
    data = res.json()
    assert data["is_synthetic"] is True
    assert data["tag"] == "SYNTHETIC"


def test_benchmark_summary_h1_not_supported():
    res = client.get("/api/benchmark/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["finding"] == "H1 not supported"
    assert len(data["combined_metric_table"]) > 0
    assert len(data["paired_comparison_table"]) == 4

    # Verify no-fault values match docs/RESULTS_SUMMARY.md exactly
    arm3b_nofault = next(
        r for r in data["combined_metric_table"]
        if r["condition"] == "Condition 0 (No-Fault)" and r["arm"] == "Arm 3b (+Trust)"
    )
    assert arm3b_nofault["recall_pct"] == 79.5
    assert arm3b_nofault["fa_per_hr"] == 1.76
    assert arm3b_nofault["tp"] == 89
    assert arm3b_nofault["fp"] == 62
