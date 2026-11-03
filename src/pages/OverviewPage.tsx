import { apiEndpoint } from '../api';
import React, { useState, useEffect } from 'react';
import { Icon } from '../components/Icons';
import { MetricCard } from '../components/MetricCard';
import { Waveform } from '../components/Waveform';
import { getAuthToken, loadUserProfile, MeasurementRecord } from '../types';

interface OverviewPageProps {
  go: (page: string) => void;
}

export function OverviewPage({ go }: OverviewPageProps) {
  const [activeRange, setActiveRange] = useState('LIVE');
  const [measurements, setMeasurements] = useState<MeasurementRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState<'auto' | 'demo' | 'user'>('auto');
  const [showAddModal, setShowAddModal] = useState(false);
  const [addType, setAddType] = useState<'heart_rate' | 'spo2' | 'respiratory_rate'>('heart_rate');
  const [addValue, setAddValue] = useState<number>(72);
  const [addUnit, setAddUnit] = useState<string>('bpm');
  const [addError, setAddError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const profile = loadUserProfile();

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const fetchMeasurements = async () => {
    const token = getAuthToken();
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch(apiEndpoint('/api/measurements?limit=50'), {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data: MeasurementRecord[] = await res.json();
        setMeasurements(data);
      }
    } catch (err) {
      console.warn('Could not load user measurements for overview', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMeasurements();
  }, []);

  // Separate real user measurements from demo measurements
  const realMeasurements = measurements.filter((m) => m.source !== 'demo');
  const demoMeasurements = measurements.filter((m) => m.source === 'demo');

  // Determine effective data source
  const isDisplayingReal =
    viewMode === 'user'
      ? realMeasurements.length > 0
      : viewMode === 'demo'
      ? false
      : realMeasurements.length > 0;

  const activeRecords = isDisplayingReal ? realMeasurements : demoMeasurements;

  // Extract latest readings
  const latestHr = activeRecords.find((m) => m.type === 'heart_rate');
  const latestSpo2 = activeRecords.find((m) => m.type === 'spo2');
  const latestResp = activeRecords.find((m) => m.type === 'respiratory_rate');

  const hrValue = latestHr ? latestHr.value : 72;
  const spo2Value = latestSpo2 ? latestSpo2.value : 97;
  const respValue = latestResp ? latestResp.value : 16;
  const avgTrustScore =
    activeRecords.length > 0
      ? (activeRecords.reduce((acc, m) => acc + (m.trust_score || 0), 0) / activeRecords.length) * 100
      : 96;

  const lastUpdatedStr = latestHr
    ? new Date(latestHr.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '10:42 AM';

  const sourceLabel = isDisplayingReal
    ? `Live User (${latestHr?.source || 'manual'})`
    : 'DEMO (Simulated Telemetry)';

  const handleAddMeasurementSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddError(null);
    const token = getAuthToken();
    if (!token) {
      setAddError('Authentication token missing. Please log in.');
      return;
    }
    try {
      const res = await fetch(apiEndpoint('/api/measurements'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          type: addType,
          value: Number(addValue),
          unit: addUnit,
          timestamp: new Date().toISOString(),
          source: 'manual',
        }),
      });
      if (res.ok) {
        setShowAddModal(false);
        showToast(`✓ Logged ${addType.replace('_', ' ')} (${addValue} ${addUnit}) successfully.`);
        fetchMeasurements();
        setViewMode('user');
      } else {
        const err = await res.json();
        setAddError(err.detail || 'Validation failed. Please verify input.');
      }
    } catch (err) {
      setAddError('Network error logging measurement.');
    }
  };

  const handleLoadDemoData = async () => {
    const token = getAuthToken();
    if (!token) {
      showToast('⚠️ Please log in to seed demo data.');
      return;
    }
    try {
      const res = await fetch(apiEndpoint('/api/measurements/demo/reset'), {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        showToast('✓ Loaded simulated research demo telemetry.');
        fetchMeasurements();
      }
    } catch (err) {
      showToast('⚠️ Network error resetting demo data.');
    }
  };

  return (
    <div className="overview">
      {/* FR-05 Data Source Banner: Clearly distinguishes DEMO vs REAL */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
          padding: '10px 16px',
          borderRadius: '10px',
          marginBottom: '16px',
          background: isDisplayingReal ? 'rgba(52, 211, 153, 0.08)' : 'rgba(245, 158, 11, 0.1)',
          border: `1px solid ${isDisplayingReal ? 'rgba(52, 211, 153, 0.3)' : 'rgba(245, 158, 11, 0.35)'}`,
          color: isDisplayingReal ? 'var(--mint)' : '#fbbf24',
          fontSize: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              padding: '2px 8px',
              borderRadius: '4px',
              fontSize: '10px',
              fontWeight: 800,
              letterSpacing: '0.05em',
              background: isDisplayingReal ? 'var(--mint)' : '#f59e0b',
              color: '#071510',
            }}
          >
            {isDisplayingReal ? 'REAL USER DATA' : 'DEMO DATA'}
          </span>
          <span>
            {isDisplayingReal
              ? `Connected to your measurements (${realMeasurements.length} records logged).`
              : 'Overview is displaying simulated research demo telemetry.'}
          </span>
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {realMeasurements.length > 0 && (
            <button
              type="button"
              className="button button-quiet"
              style={{ fontSize: '11px', padding: '4px 10px', minHeight: '26px' }}
              onClick={() => setViewMode(isDisplayingReal ? 'demo' : 'user')}
            >
              {isDisplayingReal ? 'Switch to Demo Data (DEMO)' : 'Switch to My Measurements'}
            </button>
          )}
          <button
            type="button"
            className="button button-soft"
            style={{ fontSize: '11px', padding: '4px 12px', minHeight: '26px', fontWeight: 600 }}
            onClick={() => setShowAddModal(true)}
          >
            <Icon name="check" size={12} /> + Add Measurement
          </button>
        </div>
      </div>

      <div className="page-title">
        <div>
          <span className="app-kicker">
            {new Date().toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' }).toUpperCase()}
          </span>
          <h1>
            Your health, <em>at a glance.</em>
          </h1>
          <p>Good morning, {profile.name}. Here’s what your signals are saying today.</p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            className="button button-soft"
            onClick={() => go('trends')}
            type="button"
          >
            <Icon name="history" /> View health history
          </button>
        </div>
      </div>

      {/* Empty State when 0 measurements exist */}
      {measurements.length === 0 && !loading && (
        <div
          style={{
            padding: '28px',
            borderRadius: '12px',
            background: 'var(--panel)',
            border: '1px solid var(--line)',
            textAlign: 'center',
            marginBottom: '20px',
          }}
        >
          <span className="app-kicker">GETTING STARTED</span>
          <h3 style={{ marginTop: '6px', marginBottom: '8px' }}>No physiological readings recorded yet</h3>
          <p style={{ color: 'var(--muted)', fontSize: '13px', maxWidth: '480px', margin: '0 auto 16px' }}>
            Begin tracking your daily heart rate, oxygen saturation, and vitals by logging a real reading,
            or seed demo research telemetry to explore the analytical dashboard.
          </p>
          <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
            <button
              type="button"
              className="button button-primary"
              onClick={() => setShowAddModal(true)}
            >
              <Icon name="check" size={14} /> Log First Measurement
            </button>
            <button
              type="button"
              className="button button-soft"
              onClick={handleLoadDemoData}
            >
              <Icon name="history" size={14} /> Load Demo Telemetry (DEMO)
            </button>
          </div>
        </div>
      )}

      <div className="dashboard-grid">
        {/* Real-time Body Signals */}
        <article className="body-signals">
          <div className="panel-top">
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span className="app-kicker">REAL-TIME OVERVIEW</span>
                <span
                  style={{
                    fontSize: '9px',
                    fontWeight: 700,
                    padding: '1px 6px',
                    borderRadius: '4px',
                    background: isDisplayingReal ? 'rgba(52, 211, 153, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                    color: isDisplayingReal ? 'var(--mint)' : '#fbbf24',
                  }}
                >
                  {isDisplayingReal ? 'LIVE' : 'DEMO'}
                </span>
              </div>
              <h2>Your Body Signals</h2>
            </div>
            <div className="range-tabs">
              {['LIVE', '1H', '6H', '24H'].map((range) => (
                <button
                  key={range}
                  className={activeRange === range ? 'selected' : ''}
                  onClick={() => setActiveRange(range)}
                  type="button"
                >
                  {range}
                </button>
              ))}
            </div>
          </div>

          <div className="signal-stats">
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span>HEART RATE</span>
                {!isDisplayingReal && (
                  <span style={{ fontSize: '9px', color: '#f59e0b', fontWeight: 700 }}>DEMO</span>
                )}
              </div>
              <strong>
                {hrValue.toFixed(0)} <small>BPM</small>
              </strong>
              <b>{isDisplayingReal ? 'From your latest reading' : 'Simulated resting baseline'}</b>
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span>SpO₂ ESTIMATE</span>
                {!isDisplayingReal && (
                  <span style={{ fontSize: '9px', color: '#f59e0b', fontWeight: 700 }}>DEMO</span>
                )}
              </div>
              <strong>
                {spo2Value.toFixed(0)}<small>%</small>
              </strong>
              <b>{isDisplayingReal ? 'From your latest reading' : 'Illustrative measurement'}</b>
            </div>
          </div>

          <div className="live-chart">
            <div className="chart-grid" />
            <Waveform large />
            <span className="chart-note">
              {hrValue.toFixed(0)} BPM <i>{lastUpdatedStr}</i>
            </span>
          </div>

          <div className="signal-meta">
            <span>
              <i className="live-dot" style={{ background: isDisplayingReal ? 'var(--mint)' : '#f59e0b' }} />
              {isDisplayingReal ? 'Live user telemetry stream' : 'Streaming demo data (DEMO)'}
            </span>
            <span>Last updated {lastUpdatedStr}</span>
            <span>Source: {sourceLabel}</span>
          </div>
        </article>

        {/* AI Insight Card */}
        <article className="ai-insight">
          <div className="ai-card-head">
            <span>
              <Icon name="sparkles" />
            </span>
            <div>
              <small>VITASENSE INTELLIGENCE</small>
              <strong>AI Insight</strong>
            </div>
            <button
              type="button"
              aria-label="More options"
              onClick={() => go('companion')}
              title="Open in AI Companion"
            >
              <Icon name="more" />
            </button>
          </div>

          <div className="neural">
            <span />
            <span />
            <span />
            <span />
            <i />
            <i />
            <i />
          </div>

          <p>
            {isDisplayingReal
              ? `Your latest heart rate is ${hrValue.toFixed(0)} BPM with ${spo2Value.toFixed(0)}% SpO₂. Review your historical variance and data quality flags.`
              : 'Your recent measurements show a change from your previous baseline. Review the trend and confirm that the latest readings are reliable.'}
          </p>

          <div className="uncertainty">
            <Icon name="shield" />
            <span>
              <b>Context matters</b>
              This is an observation, not a diagnosis.
            </span>
          </div>

          <div className="insight-actions">
            <button onClick={() => go('assessment')} type="button" style={{ background: 'var(--brand-mint)', color: '#000', fontWeight: 700 }}>
              Assess Symptoms (FR-06) <Icon name="arrow" />
            </button>
            <button onClick={() => go('companion')} type="button">
              Explain this trend <Icon name="arrow" />
            </button>
            <button onClick={() => go('trends')} type="button">
              View supporting data <Icon name="chevron" />
            </button>
            <button onClick={() => go('signals')} type="button">
              Review uncertainty <Icon name="chevron" />
            </button>
          </div>
        </article>

        {/* Metric Row */}
        <div className="metric-row">
          <MetricCard
            icon="drop"
            label={isDisplayingReal ? "SpO₂ ESTIMATE" : "SpO₂ ESTIMATE (DEMO)"}
            value={spo2Value.toFixed(0)}
            unit="%"
            change="1.2%"
          >
            <svg className="mini-spark" viewBox="0 0 180 45">
              <path d="M0 31 22 29 40 30 57 17 72 25 89 23 108 9 125 23 146 20 180 12" />
            </svg>
          </MetricCard>

          <MetricCard
            icon="activity"
            label={isDisplayingReal ? "RESPIRATORY RATE" : "RESPIRATORY RATE (DEMO)"}
            value={respValue.toFixed(0)}
            unit="/ min"
            change="0.8%"
          >
            <svg className="mini-bars" viewBox="0 0 180 45">
              {[16, 25, 20, 35, 28, 42, 31, 38, 24, 34, 29, 40].map((val, idx) => (
                <rect
                  key={idx}
                  x={idx * 15}
                  y={45 - val}
                  width="7"
                  height={val}
                  rx="3"
                />
              ))}
            </svg>
          </MetricCard>

          {/* Quality Card */}
          <article className="quality-card">
            <div className="panel-top">
              <div>
                <small>DATA QUALITY</small>
                <strong>Signal integrity</strong>
              </div>
              <span className="quality-score">{avgTrustScore.toFixed(0)}%</span>
            </div>
            <div className="quality-bar">
              <i style={{ width: `${Math.min(100, avgTrustScore)}%` }} />
            </div>
            <div className="quality-list">
              <span>
                <i className="good" /> Completeness <b>98%</b>
              </span>
              <span>
                <i className="good" /> Freshness <b>Current</b>
              </span>
              <span>
                <i className="warn" /> Source <b>{isDisplayingReal ? 'User Telemetry' : 'DEMO Data'}</b>
              </span>
            </div>
            <button onClick={() => go('signals')} type="button">
              Open validation report <Icon name="arrow" />
            </button>
          </article>
        </div>

        {/* 7-Day Trend Card */}
        <article className="trend-card">
          <div className="panel-top">
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span className="app-kicker">7-DAY TREND</span>
                {!isDisplayingReal && (
                  <span style={{ fontSize: '9px', color: '#f59e0b', fontWeight: 700 }}>DEMO</span>
                )}
              </div>
              <h3>Heart rate history</h3>
            </div>
            <div className="legend">
              <span>
                <i /> Your reading
              </span>
              <span>
                <i /> Baseline
              </span>
              <button onClick={() => go('trends')} type="button">
                View analysis <Icon name="arrow" />
              </button>
            </div>
          </div>

          <div className="trend-chart">
            <div className="y-labels">
              <span>100</span>
              <span>80</span>
              <span>60</span>
              <span>40</span>
            </div>
            <svg viewBox="0 0 800 190" preserveAspectRatio="none">
              <path
                className="baseline"
                d="M0 102 C130 91 210 110 350 99 S590 108 800 93"
              />
              <path
                className="trend-area"
                d="M0 127 C75 125 93 72 159 88 S250 132 310 112 395 61 456 86 531 121 599 81 702 67 800 35 V190H0Z"
              />
              <path
                className="trend-line"
                d="M0 127 C75 125 93 72 159 88 S250 132 310 112 395 61 456 86 531 121 599 81 702 67 800 35"
              />
              <circle cx="456" cy="86" r="5" />
            </svg>
            <div className="x-labels">
              <span>MON</span>
              <span>TUE</span>
              <span>WED</span>
              <span>THU</span>
              <span>FRI</span>
              <span>SAT</span>
              <span>TODAY</span>
            </div>
          </div>
        </article>

        {/* Recent Events / Activity Card */}
        <article className="activity-card">
          <div className="panel-top">
            <div>
              <span className="app-kicker">ACTIVITY</span>
              <h3>Recent events</h3>
            </div>
            <button
              type="button"
              aria-label="More options"
              onClick={() => go('alerts')}
              title="View recent event alerts"
            >
              <Icon name="more" />
            </button>
          </div>

          <div className="timeline">
            <div>
              <span className="event-icon mint">
                <Icon name="pulse" />
              </span>
              <p>
                <b>Reading saved</b>
                <small>Heart rate · {hrValue.toFixed(0)} BPM</small>
              </p>
              <time>{lastUpdatedStr}</time>
            </div>
            <div>
              <span className="event-icon violet">
                <Icon name="ai" />
              </span>
              <p>
                <b>Trend insight updated</b>
                <small>New pattern detected</small>
              </p>
              <time>9:18 AM</time>
            </div>
            <div>
              <span className="event-icon cyan">
                <Icon name="shield" />
              </span>
              <p>
                <b>Validation completed</b>
                <small>{avgTrustScore.toFixed(0)}% trust rating</small>
              </p>
              <time>Yesterday</time>
            </div>
          </div>
        </article>

        {/* Research Demo Notice */}
        <div className="demo-notice">
          <Icon name="shield" />
          <span>
            <b>Research demonstration</b>
            {isDisplayingReal
              ? 'Your actual recorded vitals are displayed above. Always consult a certified physician for medical decisions.'
              : 'All measurements shown above are illustrative DEMO data and are not intended for diagnosis or clinical decision-making.'}
          </span>
          <button
            type="button"
            onClick={() => go('benchmark')}
            title="Inspect verified benchmark results"
          >
            Learn more
          </button>
        </div>
      </div>

      {/* Quick Add Measurement Modal on Overview */}
      {showAddModal && (
        <div className="export-dialog-backdrop" onClick={() => setShowAddModal(false)}>
          <div className="export-dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '440px' }}>
            <div className="export-dialog-header">
              <div>
                <span className="app-kicker">MANUAL MEASUREMENT INGESTION</span>
                <h3>Add Health Reading</h3>
                <p>Record your real vital reading. It will be assessed by the quality engine.</p>
              </div>
              <button
                className="export-dialog-close"
                onClick={() => setShowAddModal(false)}
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            {addError && (
              <div
                style={{
                  padding: '10px 14px',
                  borderRadius: '8px',
                  background: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid #ef4444',
                  color: '#f87171',
                  fontSize: '12px',
                  marginBottom: '16px',
                }}
              >
                ⚠️ {addError}
              </div>
            )}

            <form onSubmit={handleAddMeasurementSubmit}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ fontSize: '11px', color: 'var(--muted)', display: 'block', marginBottom: '6px' }}>
                  Measurement Type
                </label>
                <select
                  value={addType}
                  onChange={(e) => {
                    const t = e.target.value as any;
                    setAddType(t);
                    if (t === 'heart_rate') setAddUnit('bpm');
                    else if (t === 'spo2') setAddUnit('%');
                    else if (t === 'respiratory_rate') setAddUnit('brpm');
                  }}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: '8px',
                    border: '1px solid var(--line-strong)',
                    background: 'var(--panel-2)',
                    color: 'var(--text)',
                  }}
                >
                  <option value="heart_rate">Heart Rate (bpm)</option>
                  <option value="spo2">Oxygen Saturation SpO₂ (%)</option>
                  <option value="respiratory_rate">Respiratory Rate (brpm)</option>
                </select>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '12px', marginBottom: '20px' }}>
                <div>
                  <label style={{ fontSize: '11px', color: 'var(--muted)', display: 'block', marginBottom: '6px' }}>
                    Reading Value
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={addValue}
                    onChange={(e) => setAddValue(Number(e.target.value))}
                    required
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: '1px solid var(--line-strong)',
                      background: 'var(--panel-2)',
                      color: 'var(--text)',
                    }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '11px', color: 'var(--muted)', display: 'block', marginBottom: '6px' }}>
                    Unit
                  </label>
                  <input
                    type="text"
                    disabled
                    value={addUnit}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: '1px solid var(--line)',
                      background: 'var(--panel)',
                      color: 'var(--muted)',
                    }}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button
                  type="button"
                  className="button button-quiet"
                  onClick={() => setShowAddModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="button button-primary">
                  Save Reading
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Floating Success Toast */}
      {toastMessage && (
        <div className="export-toast">
          <Icon name="check" size={16} />
          <span>{toastMessage}</span>
        </div>
      )}
    </div>
  );
}
