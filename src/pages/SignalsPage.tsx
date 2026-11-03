import { apiEndpoint } from '../api';
import React, { useState, useEffect, useRef } from 'react';
import { Icon } from '../components/Icons';

interface ReplayPoint {
  idx: number;
  timestamp_sec: number;
  hr_ppg: number | null;
  hr_ecg: number | null;
  trust_score: number;
  enmo: number;
  is_alert: boolean;
  alert_suppressed: boolean;
  fault_active: boolean;
}

interface ReplayResponse {
  notice: string;
  subject: string;
  fault_type: string;
  is_synthetic: boolean;
  tag: string;
  offset: number;
  limit: number;
  total_windows: number;
  step_sec: number;
  data: ReplayPoint[];
}

interface SubjectInfo {
  id: string;
  label: string;
  duration_min: number;
  n_windows: number;
}

const FAULT_OPTIONS = [
  { id: 'NONE', label: 'Clean (No Fault)', synthetic: false },
  { id: 'F1_GAPS', label: 'F1: Missing Gaps (SYNTHETIC)', synthetic: true },
  { id: 'F2_STALE', label: 'F2: Stale Sensor Freeze (SYNTHETIC)', synthetic: true },
  { id: 'F3_DUPL', label: 'F3: Duplicate Packets (SYNTHETIC)', synthetic: true },
  { id: 'F4_SPIKE', label: 'F4: Impulsive Spikes (SYNTHETIC)', synthetic: true },
  { id: 'F5_DRIFT', label: 'F5: Baseline Drift (SYNTHETIC)', synthetic: true },
  { id: 'F6_UNIT', label: 'F6: Unit Scale Shift (SYNTHETIC)', synthetic: true },
  { id: 'F7_NOISE', label: 'F7: Optical BVP Noise +5dB (SYNTHETIC)', synthetic: true },
];

export function SignalsPage() {
  const [subjects, setSubjects] = useState<SubjectInfo[]>([]);
  const [selectedSubject, setSelectedSubject] = useState<string>('S1');
  const [selectedFault, setSelectedFault] = useState<string>('NONE');
  const [streamData, setStreamData] = useState<ReplayPoint[]>([]);
  const [currentIdx, setCurrentIdx] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [speed, setSpeed] = useState<number>(1);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [totalWindows, setTotalWindows] = useState<number>(4603);

  const timerRef = useRef<number | null>(null);

  // Fetch subjects list on mount
  useEffect(() => {
    fetch(apiEndpoint('/api/replay/subjects'))
      .then((r) => r.json())
      .then((data: SubjectInfo[]) => {
        if (Array.isArray(data) && data.length > 0) {
          setSubjects(data);
        }
      })
      .catch((err) => console.error('Failed to fetch subjects:', err));
  }, []);

  // Fetch replay stream data when subject or fault changes
  useEffect(() => {
    setIsLoading(true);
    const url = `/api/replay/stream?subject=${selectedSubject}&fault=${selectedFault}&offset=0&limit=400`;
    fetch(url)
      .then((r) => r.json())
      .then((res: ReplayResponse) => {
        if (res && res.data) {
          setStreamData(res.data);
          setTotalWindows(res.total_windows || res.data.length);
          setCurrentIdx(0);
        }
        setIsLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load replay stream:', err);
        setIsLoading(false);
      });
  }, [selectedSubject, selectedFault]);

  // Animation / playback loop
  useEffect(() => {
    if (isPlaying && streamData.length > 0) {
      const intervalMs = Math.max(100, Math.floor(1000 / speed));
      timerRef.current = setInterval(() => {
        setCurrentIdx((prev) => (prev + 1) % streamData.length);
      }, intervalMs);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isPlaying, speed, streamData]);

  const currentPoint: ReplayPoint = streamData[currentIdx] || {
    idx: 0,
    timestamp_sec: 0,
    hr_ppg: 72.0,
    hr_ecg: 72.0,
    trust_score: 0.95,
    enmo: 0.015,
    is_alert: false,
    alert_suppressed: false,
    fault_active: false,
  };

  const isFaultSelected = selectedFault !== 'NONE';
  const hrError =
    currentPoint.hr_ppg !== null && currentPoint.hr_ecg !== null
      ? Math.abs(currentPoint.hr_ppg - currentPoint.hr_ecg)
      : null;

  // Mini history window (last 30 samples)
  const windowSlice = streamData.slice(Math.max(0, currentIdx - 29), currentIdx + 1);

  return (
    <div className="feature-page signal-lab-page">
      {/* Prominent Replay Banner Required by Protocol */}
      <div className="replay-banner">
        <div className="replay-badge">
          <Icon name="activity" />
          <span>REPLAY: public dataset, not live</span>
        </div>
        <p>
          Telemetry streamed strictly from verified <code>data/processed</code> caches (PPG-DaLiA cohort).
          No model training at runtime.
        </p>
      </div>

      <div className="page-title">
        <div>
          <span className="app-kicker">SIGNAL LAB / REPLAY SIMULATOR</span>
          <h1>
            Physiological Signal <em>Validation & Replay</em>
          </h1>
          <p>
            Evaluate wrist-PPG heart rate tracking against gold-standard ECG reference,
            assess real-time rule-based trust scoring, and simulate synthetic telemetry faults.
          </p>
        </div>

        {/* Live Status Indicators */}
        <div className="replay-status-group">
          {currentPoint.is_alert && (
            <span className="status-pill status-alert">
              <Icon name="bell" /> TACHYCARDIA ALERT
            </span>
          )}
          {currentPoint.alert_suppressed && (
            <span className="status-pill status-suppressed">
              <Icon name="shield" /> ALERT SUPPRESSED (Low Trust)
            </span>
          )}
          {!currentPoint.is_alert && !currentPoint.alert_suppressed && (
            <span className="status-pill status-normal">
              <Icon name="check" /> Telemetry Nominal
            </span>
          )}
        </div>
      </div>

      {/* Control Console */}
      <section className="replay-controls-card">
        <div className="control-row">
          <div className="control-field">
            <label htmlFor="subject-select">
              <Icon name="user" /> Subject Selection
            </label>
            <select
              id="subject-select"
              value={selectedSubject}
              onChange={(e) => setSelectedSubject(e.target.value)}
              className="select-input"
            >
              {subjects.length > 0 ? (
                subjects.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label} ({s.duration_min} min, {s.n_windows} windows)
                  </option>
                ))
              ) : (
                Array.from({ length: 15 }, (_, i) => `S${i + 1}`).map((sid) => (
                  <option key={sid} value={sid}>
                    Subject {sid}
                  </option>
                ))
              )}
            </select>
          </div>

          <div className="control-field">
            <label htmlFor="fault-select">
              <Icon name="shield" /> Fault Injection Module
            </label>
            <select
              id="fault-select"
              value={selectedFault}
              onChange={(e) => setSelectedFault(e.target.value)}
              className={`select-input ${isFaultSelected ? 'fault-active-border' : ''}`}
            >
              {FAULT_OPTIONS.map((opt) => (
                <option key={opt.id} value={opt.id}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Playback Controls */}
          <div className="playback-buttons">
            <button
              type="button"
              className="button button-soft"
              onClick={() => setIsPlaying(!isPlaying)}
              aria-label={isPlaying ? 'Pause' : 'Play'}
            >
              <Icon name={isPlaying ? 'moon' : 'pulse'} />
              <span>{isPlaying ? 'Pause' : 'Play'}</span>
            </button>

            <button
              type="button"
              className={`speed-pill ${speed === 1 ? 'active' : ''}`}
              onClick={() => setSpeed(1)}
            >
              1×
            </button>
            <button
              type="button"
              className={`speed-pill ${speed === 2 ? 'active' : ''}`}
              onClick={() => setSpeed(2)}
            >
              2×
            </button>
            <button
              type="button"
              className={`speed-pill ${speed === 5 ? 'active' : ''}`}
              onClick={() => setSpeed(5)}
            >
              5×
            </button>
          </div>
        </div>

        {/* Timeline Scrubber */}
        <div className="timeline-scrubber">
          <div className="scrubber-labels">
            <span>Window #{currentPoint.idx} ({Math.floor(currentPoint.timestamp_sec / 60)}m {(currentPoint.timestamp_sec % 60).toFixed(0)}s)</span>
            <span>Total: {totalWindows} windows</span>
          </div>
          <input
            type="range"
            min={0}
            max={Math.max(0, streamData.length - 1)}
            value={currentIdx}
            onChange={(e) => {
              setCurrentIdx(Number(e.target.value));
              setIsPlaying(false);
            }}
            className="slider-bar"
          />
        </div>
      </section>

      {/* Telemetry Metric Displays */}
      <div className="telemetry-grid">
        {/* Metric 1: Wrist-PPG HR */}
        <article className="telemetry-card">
          <span className="app-kicker">ESTIMATED TELEMETRY</span>
          <div className="metric-header">
            <h3>Wrist-PPG Heart Rate</h3>
            <span className="telemetry-source">Step 3a Estimator</span>
          </div>
          <div className="metric-val">
            <strong>
              {currentPoint.hr_ppg !== null ? currentPoint.hr_ppg.toFixed(1) : 'NaN'}
            </strong>
            <span>BPM</span>
          </div>
          {isFaultSelected && (
            <span className="synthetic-tag">
              <Icon name="shield" /> SYNTHETIC FAULT APPLIED
            </span>
          )}
        </article>

        {/* Metric 2: ECG Reference HR */}
        <article className="telemetry-card">
          <span className="app-kicker">GROUND TRUTH</span>
          <div className="metric-header">
            <h3>ECG Reference HR</h3>
            <span className="telemetry-source">RespiBAN Chest ECG</span>
          </div>
          <div className="metric-val">
            <strong className="text-mint">
              {currentPoint.hr_ecg !== null ? currentPoint.hr_ecg.toFixed(1) : 'NaN'}
            </strong>
            <span>BPM</span>
          </div>
          <small className="metric-sub">
            {hrError !== null ? `Error: ${hrError.toFixed(1)} BPM` : 'Sensor Gap'}
          </small>
        </article>

        {/* Metric 3: Trust Score */}
        <article className="telemetry-card">
          <span className="app-kicker">DATA QUALITY</span>
          <div className="metric-header">
            <h3>Rule-Based Trust Score</h3>
            <span className="telemetry-source">S_gap × S_stale × S_phys × S_mot</span>
          </div>
          <div className="metric-val">
            <strong
              style={{
                color:
                  currentPoint.trust_score >= 0.70
                    ? 'var(--mint)'
                    : currentPoint.trust_score >= 0.50
                    ? '#f59e0b'
                    : '#ef4444',
              }}
            >
              {(currentPoint.trust_score * 100).toFixed(0)}
            </strong>
            <span>%</span>
          </div>
          <div className="trust-meter">
            <div
              className="trust-meter-fill"
              style={{
                width: `${Math.max(0, Math.min(100, currentPoint.trust_score * 100))}%`,
                backgroundColor:
                  currentPoint.trust_score >= 0.70
                    ? 'var(--mint)'
                    : currentPoint.trust_score >= 0.50
                    ? '#f59e0b'
                    : '#ef4444',
              }}
            />
          </div>
          <small className="metric-sub">
            {currentPoint.trust_score >= 0.70
              ? 'High Confidence · Alerts Allowed'
              : 'Compromised Signal · Alerts Gated'}
          </small>
        </article>

        {/* Metric 4: Kinematic ENMO */}
        <article className="telemetry-card">
          <span className="app-kicker">KINEMATICS</span>
          <div className="metric-header">
            <h3>Motion Energy (ENMO 10s)</h3>
            <span className="telemetry-source">Wrist Accelerometer</span>
          </div>
          <div className="metric-val">
            <strong>{currentPoint.enmo.toFixed(3)}</strong>
            <span>g</span>
          </div>
          <small className="metric-sub">
            {currentPoint.enmo <= 0.05
              ? 'Resting Epoch (Gating Clear)'
              : currentPoint.enmo <= 0.15
              ? 'Moderate Movement'
              : 'High Motion (Kinematic Gate Active)'}
          </small>
        </article>
      </div>

      {/* Synchronized Real-Time Waveform & Trend Visualizer */}
      <section className="replay-visualizer-card">
        <div className="visualizer-header">
          <div>
            <span className="app-kicker">SYNCHRONIZED TRACE</span>
            <h2>Real-Time Tracking: Wrist PPG vs. ECG Reference</h2>
          </div>
          <div className="legend-pills">
            <span className="legend-pill legend-ppg">Wrist-PPG HR</span>
            <span className="legend-pill legend-ecg">ECG Reference</span>
            <span className="legend-pill legend-trust">Trust Score</span>
          </div>
        </div>

        {/* SVG Live Strip Chart */}
        <div className="chart-canvas-container">
          <svg className="live-strip-chart" viewBox="0 0 600 200" preserveAspectRatio="none">
            {/* Grid Lines */}
            <line x1="0" y1="50" x2="600" y2="50" stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
            <line x1="0" y1="100" x2="600" y2="100" stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
            <line x1="0" y1="150" x2="600" y2="150" stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />

            {/* Threshold Line at 100 BPM */}
            <line x1="0" y1="75" x2="600" y2="75" stroke="#ef4444" strokeDasharray="3 3" opacity="0.6" />
            <text x="10" y="70" fill="#ef4444" fontSize="10">Alert Threshold: 100 BPM</text>

            {/* ECG Reference Polyline (Mint) */}
            {windowSlice.length > 1 && (
              <polyline
                fill="none"
                stroke="#10b981"
                strokeWidth="2.5"
                points={windowSlice
                  .map((p, i) => {
                    const x = (i / (windowSlice.length - 1)) * 600;
                    const val = p.hr_ecg !== null ? p.hr_ecg : 70;
                    // Map 50-150 bpm to 180-20 svg y
                    const y = 180 - ((val - 50) / 100) * 160;
                    return `${x},${Math.max(10, Math.min(190, y))}`;
                  })
                  .join(' ')}
              />
            )}

            {/* Wrist PPG HR Polyline (Cyan/Amber) */}
            {windowSlice.length > 1 && (
              <polyline
                fill="none"
                stroke={isFaultSelected ? '#f59e0b' : '#38bdf8'}
                strokeWidth="2.5"
                strokeDasharray={isFaultSelected ? '4 2' : 'none'}
                points={windowSlice
                  .map((p, i) => {
                    const x = (i / (windowSlice.length - 1)) * 600;
                    const val = p.hr_ppg !== null ? p.hr_ppg : 70;
                    const y = 180 - ((val - 50) / 100) * 160;
                    return `${x},${Math.max(10, Math.min(190, y))}`;
                  })
                  .join(' ')}
              />
            )}
          </svg>
        </div>

        <div className="visualizer-footer">
          <small>
            Mode: <strong>REPLAY: public dataset, not live</strong> · Showing 30-window rolling observation buffer (60s history)
          </small>
          {isFaultSelected && (
            <span className="synthetic-badge-pill">
              SYNTHETIC FAULT: {selectedFault}
            </span>
          )}
        </div>
      </section>
    </div>
  );
}
