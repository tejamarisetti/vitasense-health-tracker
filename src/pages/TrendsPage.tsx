import React, { useState, useEffect } from 'react';
import { Icon } from '../components/Icons';
import { loadUserProfile, getAuthToken, MeasurementRecord, HistoryItem } from '../types';

export function TrendsPage() {
  const [activeRange, setActiveRange] = useState('7D');
  const [showExportModal, setShowExportModal] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Phase 2 Telemetry & Quality Engine State
  const [measurements, setMeasurements] = useState<MeasurementRecord[]>([]);
  const [loadingMeas, setLoadingMeas] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [addType, setAddType] = useState<'heart_rate' | 'spo2' | 'respiratory_rate' | 'hrv'>('heart_rate');
  const [addValue, setAddValue] = useState<number>(72);
  const [addUnit, setAddUnit] = useState('bpm');
  const [addSource, setAddSource] = useState<'manual' | 'import' | 'demo'>('manual');
  const [addError, setAddError] = useState<string | null>(null);

  // Phase 3 FR-10 History State
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyPage, setHistoryPage] = useState(1);
  const [historyTotalPages, setHistoryTotalPages] = useState(1);
  const [historyTotalItems, setHistoryTotalItems] = useState(0);
  const [historyCategory, setHistoryCategory] = useState<'all' | 'measurements' | 'alerts'>('all');
  const [historyTypeFilter, setHistoryTypeFilter] = useState('');
  const [activeTableTab, setActiveTableTab] = useState<'telemetry' | 'history'>('telemetry');
  const [expandedHistoryId, setExpandedHistoryId] = useState<string | null>(null);

  const profile = loadUserProfile();

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const fetchMeasurements = async () => {
    const token = getAuthToken();
    if (!token) return;
    setLoadingMeas(true);
    try {
      const res = await fetch('/api/measurements?limit=50', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setMeasurements(data);
        // If empty, auto-seed demo data for immediate visual experience
        if (data.length === 0) {
          await fetch('/api/measurements/demo/reset', {
            method: 'POST',
            headers: { Authorization: `Bearer ${token}` },
          });
          const reRes = await fetch('/api/measurements?limit=50', {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (reRes.ok) {
            setMeasurements(await reRes.json());
          }
        }
      }
    } catch (err) {
      console.warn('Could not load telemetry measurements', err);
    } finally {
      setLoadingMeas(false);
    }
  };

  const fetchHistory = async (page = historyPage, category = historyCategory, typeFilter = historyTypeFilter) => {
    const token = getAuthToken();
    if (!token) return;
    setHistoryLoading(true);
    try {
      let url = `/api/history?page=${page}&limit=10&category=${category}`;
      if (typeFilter) {
        url += `&item_type=${encodeURIComponent(typeFilter)}`;
      }
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setHistoryItems(data.items || []);
        setHistoryPage(data.page || 1);
        setHistoryTotalPages(data.total_pages || 1);
        setHistoryTotalItems(data.total_items || 0);
      }
    } catch (err) {
      console.warn('Could not load user history', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    fetchMeasurements();
    fetchHistory(1, historyCategory, historyTypeFilter);
  }, []);

  useEffect(() => {
    if (activeTableTab === 'history') {
      fetchHistory(historyPage, historyCategory, historyTypeFilter);
    }
  }, [activeTableTab, historyCategory, historyTypeFilter, historyPage]);

  const handleResetDemoData = async () => {
    const token = getAuthToken();
    if (!token) {
      showToast('⚠️ Please log in to manage telemetry data.');
      return;
    }
    try {
      const res = await fetch('/api/measurements/demo/reset', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        showToast(`✓ ${data.message}`);
        fetchMeasurements();
      } else {
        const err = await res.json();
        showToast(`⚠️ Error resetting demo data: ${err.detail || 'Failed'}`);
      }
    } catch (err) {
      showToast('⚠️ Network error resetting demo data.');
    }
  };

  const handleAddMeasurementSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddError(null);
    const token = getAuthToken();
    if (!token) {
      setAddError('Authentication token missing. Please log in.');
      return;
    }

    try {
      const res = await fetch('/api/measurements', {
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
          source: addSource,
        }),
      });

      if (res.ok) {
        setShowAddModal(false);
        showToast(`✓ Added ${addType} reading (${addValue} ${addUnit}) successfully.`);
        fetchMeasurements();
      } else {
        const err = await res.json();
        setAddError(err.detail || 'Validation failed. Please verify inputs.');
      }
    } catch (err) {
      setAddError('Network error submitting measurement.');
    }
  };

  // Adjust default unit when measurement type changes
  const handleTypeChange = (t: 'heart_rate' | 'spo2' | 'respiratory_rate' | 'hrv') => {
    setAddType(t);
    if (t === 'heart_rate') setAddUnit('bpm');
    else if (t === 'spo2') setAddUnit('%');
    else if (t === 'respiratory_rate') setAddUnit('brpm');
    else if (t === 'hrv') setAddUnit('ms');
  };

  const generateReportData = () => {
    const now = new Date();
    const dates = ['MON 20', 'TUE 21', 'WED 22', 'THU 23', 'FRI 24', 'SAT 25', 'SUN 26'];
    const hrValues = [68, 72, 70, 86, 74, 71, 73];

    return {
      report_title: 'VitaSense AI Telemetry & Physiological Trend Report',
      generated_at: now.toISOString(),
      report_range: activeRange,
      patient_profile: {
        name: profile.name,
        email: profile.email,
        age: profile.age,
        biological_sex: profile.sex,
        resting_baseline_hr: `${profile.restingHr} BPM`,
        activity_level: profile.activityLevel,
        wellness_target: profile.healthGoal,
      },
      summary_statistics: {
        mean_heart_rate: '74.2 BPM',
        min_heart_rate: '58.0 BPM',
        max_heart_rate: '112.5 BPM',
        resting_hr_baseline: `${profile.restingHr || 64} BPM`,
        hrv_sdnn: '48.3 ms',
        data_trust_index: '96.4%',
        signal_completeness: '98.2%',
        motion_artifact_suppressions: 2,
      },
      time_series_observations: dates.map((day, idx) => ({
        epoch: day,
        mean_hr_bpm: hrValues[idx],
        baseline_hr_bpm: profile.restingHr || 64,
        deviation_bpm: hrValues[idx] - (profile.restingHr || 64),
        trust_confidence: '0.96',
        kinematic_state: hrValues[idx] > 80 ? 'Elevated / Transient' : 'Nominal Resting',
      })),
      research_disclaimer:
        'This telemetry report is generated strictly for educational, research, and self-monitoring demonstration purposes by the VitaSense AI platform. It is not an FDA-cleared diagnostic device and must not replace professional clinical diagnosis.',
    };
  };

  const handleExportJson = () => {
    const data = generateReportData();
    const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(
      JSON.stringify(data, null, 2)
    )}`;
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', jsonString);
    downloadAnchor.setAttribute(
      'download',
      `vitasense-telemetry-report-${activeRange.toLowerCase()}.json`
    );
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();

    setShowExportModal(false);
    showToast(`✓ VitaSense JSON telemetry report (${activeRange}) downloaded successfully.`);
  };

  const handleExportCsv = () => {
    const data = generateReportData();
    const headers = [
      'Epoch',
      'Mean_HR_BPM',
      'Baseline_HR_BPM',
      'Deviation_BPM',
      'Trust_Confidence',
      'Kinematic_State',
    ];
    const rows = data.time_series_observations.map((row) => [
      row.epoch,
      row.mean_hr_bpm,
      row.baseline_hr_bpm,
      row.deviation_bpm,
      row.trust_confidence,
      `"${row.kinematic_state}"`,
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');

    const encodedUri = encodeURI(csvContent);
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', encodedUri);
    downloadAnchor.setAttribute(
      'download',
      `vitasense-telemetry-log-${activeRange.toLowerCase()}.csv`
    );
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();

    setShowExportModal(false);
    showToast(`✓ VitaSense CSV data log (${activeRange}) downloaded successfully.`);
  };

  const handlePrint = () => {
    setShowExportModal(false);
    setTimeout(() => {
      window.print();
    }, 200);
  };

  return (
    <div className="feature-page">
      <div className="page-title">
        <div>
          <span className="app-kicker">HEALTH TRENDS</span>
          <h1>
            Patterns, <em>made visible.</em>
          </h1>
          <p>
            Compare signals with your historical baseline and inspect every deviation.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            className="button button-soft"
            type="button"
            onClick={() => setShowExportModal(true)}
            id="export-report-btn"
            aria-label="Export health report"
          >
            Export report <Icon name="arrow" />
          </button>
        </div>
      </div>

      <article className="analysis-card">
        <div className="analysis-controls">
          <div className="range-tabs">
            {['24H', '7D', '30D', '3M'].map((range) => (
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

          <div>
            <span>
              <i className="mint-line" /> Heart rate
            </span>
            <span>
              <i className="violet-line" /> Baseline
            </span>
          </div>
        </div>

        <div className="large-analysis">
          <div className="analysis-tooltip">
            <small>THURSDAY · 2:40 PM</small>
            <b>86 BPM</b>
            <span>8 BPM above baseline</span>
          </div>

          <svg viewBox="0 0 1000 360" preserveAspectRatio="none">
            <defs>
              <linearGradient id="trendfill" x1="0" y1="0" x2="0" y2="1">
                <stop stopColor="#35e6d3" stopOpacity=".25" />
                <stop stopColor="#35e6d3" stopOpacity="0" offset="1" />
              </linearGradient>
            </defs>

            <path
              className="cursor-line"
              d="M 520,30 L 520,330"
              stroke="#adcde233"
              strokeWidth="1"
            />
            <path
              className="baseline"
              d="M 40,240 Q 250,230 500,245 T 960,235"
              fill="none"
              stroke="#a78bfa"
              strokeWidth="2"
            />
            <path
              className="trend-area"
              d="M 40,270 Q 150,250 260,220 T 520,130 T 740,240 T 960,210 L 960,340 L 40,340 Z"
            />
            <path
              className="trend-line"
              d="M 40,270 Q 150,250 260,220 T 520,130 T 740,240 T 960,210"
              fill="none"
              stroke="#35e6d3"
              strokeWidth="3"
            />
            <circle cx="520" cy="130" r="6" />
          </svg>

          <div className="y-labels">
            <span>120</span>
            <span>100</span>
            <span>80</span>
            <span>60</span>
            <span>40</span>
          </div>
        </div>

        <div className="x-labels">
          <span>MON</span>
          <span>TUE</span>
          <span>WED</span>
          <span>THU</span>
          <span>FRI</span>
          <span>SAT</span>
          <span>SUN</span>
        </div>
      </article>

      {/* ====================================================================
          Phase 2: Physiological Telemetry & Quality Engine (FR-02 & FR-03)
          ==================================================================== */}
      <section className="telemetry-section">
        <div className="telemetry-header">
          <div>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
              <button
                type="button"
                onClick={() => setActiveTableTab('telemetry')}
                style={{
                  background: activeTableTab === 'telemetry' ? 'var(--mint)' : 'var(--panel-2)',
                  color: activeTableTab === 'telemetry' ? '#071510' : 'var(--muted)',
                  border: '1px solid var(--line)',
                  borderRadius: '6px',
                  padding: '6px 14px',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Telemetry Stream (FR-03)
              </button>
              <button
                type="button"
                onClick={() => setActiveTableTab('history')}
                style={{
                  background: activeTableTab === 'history' ? 'var(--mint)' : 'var(--panel-2)',
                  color: activeTableTab === 'history' ? '#071510' : 'var(--muted)',
                  border: '1px solid var(--line)',
                  borderRadius: '6px',
                  padding: '6px 14px',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                User History & Audit (FR-10)
              </button>
            </div>
            <h2>
              {activeTableTab === 'telemetry'
                ? 'Physiological Telemetry & Quality Engine'
                : 'User History, Assessments & Alert Timeline'}
            </h2>
            <p>
              {activeTableTab === 'telemetry'
                ? 'Per-user isolated time-series with deterministic quality flags (missing, stale, duplicate, implausible, sudden change) and component checks.'
                : 'Chronological timeline of your measurements, alerts, and evaluations with category filters and pagination.'}
            </p>
          </div>

          <div className="telemetry-actions">
            {activeTableTab === 'telemetry' ? (
              <>
                <button
                  className="button button-soft"
                  onClick={() => setShowAddModal(true)}
                  type="button"
                >
                  <Icon name="check" size={14} /> Add Measurement
                </button>
                <button
                  className="button button-quiet"
                  onClick={handleResetDemoData}
                  title="Resets DEMO data only. Real user measurements are never deleted."
                  type="button"
                >
                  <Icon name="history" size={14} /> Reset Demo Data (DEMO)
                </button>
              </>
            ) : (
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <select
                  value={historyCategory}
                  onChange={(e) => {
                    setHistoryCategory(e.target.value as any);
                    setHistoryPage(1);
                  }}
                  style={{
                    background: 'var(--panel-2)',
                    color: 'var(--text)',
                    border: '1px solid var(--line-strong)',
                    borderRadius: '8px',
                    padding: '6px 10px',
                    fontSize: '11px',
                  }}
                >
                  <option value="all">All Categories</option>
                  <option value="measurements">Measurements Only</option>
                  <option value="alerts">Alerts Only</option>
                </select>

                <select
                  value={historyTypeFilter}
                  onChange={(e) => {
                    setHistoryTypeFilter(e.target.value);
                    setHistoryPage(1);
                  }}
                  style={{
                    background: 'var(--panel-2)',
                    color: 'var(--text)',
                    border: '1px solid var(--line-strong)',
                    borderRadius: '8px',
                    padding: '6px 10px',
                    fontSize: '11px',
                  }}
                >
                  <option value="">All Metric Types</option>
                  <option value="heart_rate">Heart Rate</option>
                  <option value="spo2">SpO₂</option>
                  <option value="respiratory_rate">Respiratory Rate</option>
                  <option value="hrv">HRV</option>
                  <option value="observation">Observation</option>
                  <option value="quality">Data Quality</option>
                </select>

                <button
                  type="button"
                  className="button button-soft"
                  onClick={() => fetchHistory(historyPage, historyCategory, historyTypeFilter)}
                  style={{ minHeight: '32px', fontSize: '11px', padding: '0 10px' }}
                >
                  <Icon name="activity" size={12} />
                  <span>Refresh</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {activeTableTab === 'telemetry' ? (
        <div className="telemetry-table-wrap">
          {loadingMeas ? (
            <div style={{ padding: '24px', textAlign: 'center', color: 'var(--muted)' }}>
              Loading telemetry observations...
            </div>
          ) : measurements.length === 0 ? (
            <div style={{ padding: '24px', textAlign: 'center', color: 'var(--muted)' }}>
              No telemetry records found. Click <strong>Add Measurement</strong> or <strong>Reset Demo Data</strong> to populate.
            </div>
          ) : (
            <table className="telemetry-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Metric Type</th>
                  <th>Value</th>
                  <th>Source</th>
                  <th>Trust Score</th>
                  <th>Quality Flags</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {measurements.map((m) => {
                  const isExpanded = expandedId === m.id;
                  const flags = m.quality_flags || [];
                  const dateStr = new Date(m.timestamp).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                  });

                  return (
                    <React.Fragment key={m.id}>
                      <tr
                        className="telemetry-row"
                        onClick={() => setExpandedId(isExpanded ? null : m.id)}
                      >
                        <td>
                          <strong>{dateStr}</strong>
                          <div style={{ fontSize: '9px', color: 'var(--faint)' }}>
                            {new Date(m.timestamp).toLocaleDateString()}
                          </div>
                        </td>
                        <td style={{ textTransform: 'capitalize' }}>
                          {m.type.replace('_', ' ')}
                        </td>
                        <td>
                          <strong>
                            {m.value.toFixed(1)} <small>{m.unit}</small>
                          </strong>
                        </td>
                        <td>
                          <span className={`badge-source ${m.source}`}>
                            {m.source}
                          </span>
                        </td>
                        <td>
                          <strong
                            style={{
                              color:
                                m.trust_score >= 0.8
                                  ? 'var(--mint)'
                                  : m.trust_score > 0.4
                                  ? '#f59e0b'
                                  : '#f87171',
                            }}
                          >
                            {(m.trust_score * 100).toFixed(0)}%
                          </strong>
                        </td>
                        <td>
                          {flags.length === 0 ? (
                            <span className="quality-flag-tag nominal">Nominal</span>
                          ) : (
                            flags.map((f) => (
                              <span key={f} className={`quality-flag-tag ${f}`}>
                                {f.replace('_', ' ')}
                              </span>
                            ))
                          )}
                        </td>
                        <td>
                          <span style={{ color: 'var(--aqua)', fontSize: '10px' }}>
                            {isExpanded ? 'Hide Checks ▲' : 'Inspect Checks ▼'}
                          </span>
                        </td>
                      </tr>

                      {/* Expandable Component Checks Drawer */}
                      {isExpanded && (
                        <tr>
                          <td colSpan={7} style={{ padding: 0 }}>
                            <div className="component-checks-drawer">
                              <span className="app-kicker">
                                vitasense.quality · RULE-BASED COMPONENT CHECKS (RECORD #{m.id})
                              </span>
                              <div className="component-checks-grid">
                                {Object.entries(m.component_checks || {}).map(
                                  ([chkKey, chkVal]) => (
                                    <div key={chkKey} className="component-check-item">
                                      <div className="check-head">
                                        <span className="check-title">
                                          {chkKey.replace('_', ' ')}
                                        </span>
                                        <span className={`check-status ${chkVal.status}`}>
                                          {chkVal.status.toUpperCase()} ({(chkVal.score * 100).toFixed(0)}%)
                                        </span>
                                      </div>
                                      <p className="check-details">{chkVal.details}</p>
                                    </div>
                                  )
                                )}
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
        ) : (
          /* ====================================================================
             FR-10 History Table & Pagination View
             ==================================================================== */
          <div className="telemetry-table-wrap">
            {historyLoading ? (
              <div style={{ padding: '32px', textAlign: 'center', color: 'var(--muted)' }}>
                Loading chronological history...
              </div>
            ) : historyItems.length === 0 ? (
              <div style={{ padding: '32px', textAlign: 'center', color: 'var(--muted)' }}>
                No records found matching category: <strong>{historyCategory}</strong>
              </div>
            ) : (
              <>
                <table className="telemetry-table">
                  <thead>
                    <tr>
                      <th>Timestamp</th>
                      <th>Category</th>
                      <th>Item Type</th>
                      <th>Summary / Value</th>
                      <th>Status / Source</th>
                      <th>Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {historyItems.map((item) => {
                      const isExpanded = expandedHistoryId === item.id;
                      const formattedTime = new Date(item.timestamp).toLocaleString([], {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      });

                      return (
                        <React.Fragment key={item.id}>
                          <tr
                            className="telemetry-row"
                            onClick={() => setExpandedHistoryId(isExpanded ? null : item.id)}
                          >
                            <td>
                              <strong>{formattedTime}</strong>
                            </td>
                            <td>
                              <span
                                style={{
                                  fontSize: '10px',
                                  padding: '3px 7px',
                                  borderRadius: '6px',
                                  background:
                                    item.category === 'measurement'
                                      ? 'rgba(5, 150, 105, 0.15)'
                                      : 'rgba(125, 211, 252, 0.15)',
                                  color:
                                    item.category === 'measurement'
                                      ? 'var(--mint)'
                                      : 'var(--cyan)',
                                  textTransform: 'uppercase',
                                  fontWeight: 700,
                                }}
                              >
                                {item.category}
                              </span>
                            </td>
                            <td style={{ textTransform: 'capitalize' }}>
                              {item.type.replace('_', ' ')}
                            </td>
                            <td>
                              {item.category === 'measurement' ? (
                                <strong>
                                  {item.details?.value} <small>{item.details?.unit}</small>
                                </strong>
                              ) : (
                                <span>{item.details?.title || item.details?.message}</span>
                              )}
                            </td>
                            <td>
                              <span className={`badge-source ${item.source || item.status || 'system'}`}>
                                {item.source || item.status || 'nominal'}
                              </span>
                            </td>
                            <td>
                              <span style={{ color: 'var(--aqua)', fontSize: '10px' }}>
                                {isExpanded ? 'Hide Payload ▲' : 'Inspect Payload ▼'}
                              </span>
                            </td>
                          </tr>

                          {isExpanded && (
                            <tr>
                              <td colSpan={6} style={{ padding: 0 }}>
                                <div className="component-checks-drawer" style={{ padding: '16px' }}>
                                  <span className="app-kicker">
                                    RECORD PAYLOAD DETAILS · OWNER ISOLATED ({item.id})
                                  </span>
                                  <pre
                                    style={{
                                      background: 'var(--panel-2)',
                                      padding: '12px',
                                      borderRadius: '8px',
                                      fontSize: '11px',
                                      color: 'var(--text)',
                                      overflowX: 'auto',
                                      margin: '10px 0 0',
                                    }}
                                  >
                                    {JSON.stringify(item, null, 2)}
                                  </pre>
                                </div>
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      );
                    })}
                  </tbody>
                </table>

                {/* Pagination Controls */}
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '14px 20px',
                    borderTop: '1px solid var(--line)',
                  }}
                >
                  <span style={{ fontSize: '11px', color: 'var(--muted)' }}>
                    Page <strong>{historyPage}</strong> of <strong>{historyTotalPages}</strong> ({historyTotalItems} total records)
                  </span>

                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      type="button"
                      className="button button-quiet"
                      disabled={historyPage <= 1}
                      onClick={() => setHistoryPage((p) => Math.max(1, p - 1))}
                      style={{ minHeight: '32px', fontSize: '11px', padding: '0 12px' }}
                    >
                      ← Previous
                    </button>
                    <button
                      type="button"
                      className="button button-quiet"
                      disabled={historyPage >= historyTotalPages}
                      onClick={() => setHistoryPage((p) => p + 1)}
                      style={{ minHeight: '32px', fontSize: '11px', padding: '0 12px' }}
                    >
                      Next →
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </section>

      {/* Add Measurement Modal */}
      {showAddModal && (
        <div className="add-meas-modal-backdrop" onClick={() => setShowAddModal(false)}>
          <div className="add-meas-modal" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '18px' }}>
              <div>
                <span className="app-kicker">SERVER-SIDE VALIDATION</span>
                <h3 style={{ margin: '4px 0 0', fontSize: '18px' }}>Add Physiological Measurement</h3>
              </div>
              <button
                className="export-dialog-close"
                onClick={() => setShowAddModal(false)}
                type="button"
              >
                ✕
              </button>
            </div>

            {addError && (
              <div
                style={{
                  background: 'rgba(239,68,68,0.12)',
                  border: '1px solid rgba(239,68,68,0.3)',
                  color: '#f87171',
                  borderRadius: '8px',
                  padding: '10px 12px',
                  fontSize: '11px',
                  marginBottom: '16px',
                }}
              >
                {addError}
              </div>
            )}

            <form onSubmit={handleAddMeasurementSubmit}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ fontSize: '11px', color: 'var(--muted)', display: 'block', marginBottom: '6px' }}>
                  Measurement Type
                </label>
                <select
                  value={addType}
                  onChange={(e) => handleTypeChange(e.target.value as any)}
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
                  <option value="hrv">Heart Rate Variability HRV (ms)</option>
                </select>
              </div>

              <div style={{ marginBottom: '14px' }}>
                <label style={{ fontSize: '11px', color: 'var(--muted)', display: 'block', marginBottom: '6px' }}>
                  Value ({addUnit})
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

              <div style={{ marginBottom: '20px' }}>
                <label style={{ fontSize: '11px', color: 'var(--muted)', display: 'block', marginBottom: '6px' }}>
                  Source Tag
                </label>
                <select
                  value={addSource}
                  onChange={(e) => setAddSource(e.target.value as any)}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: '8px',
                    border: '1px solid var(--line-strong)',
                    background: 'var(--panel-2)',
                    color: 'var(--text)',
                  }}
                >
                  <option value="manual">Manual Entry</option>
                  <option value="import">Imported Dataset</option>
                  <option value="demo">Demo Wearable</option>
                </select>
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
                  Submit & Validate
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Export Report Modal */}
      {showExportModal && (
        <div className="export-dialog-backdrop" onClick={() => setShowExportModal(false)}>
          <div className="export-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="export-dialog-header">
              <div>
                <span className="app-kicker">TELEMETRY EXPORT</span>
                <h3>Export Health & Trend Report</h3>
                <p>Select your preferred data format for the {activeRange} observation window.</p>
              </div>
              <button
                className="export-dialog-close"
                onClick={() => setShowExportModal(false)}
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            <div className="export-preview-box">
              <span className="app-kicker">REPORT SUMMARY · {activeRange}</span>
              <div className="export-preview-grid">
                <div className="export-stat-item">
                  <small>PATIENT PROFILE</small>
                  <strong>{profile.name}</strong>
                </div>
                <div className="export-stat-item">
                  <small>MEAN HEART RATE</small>
                  <strong>74.2 BPM</strong>
                </div>
                <div className="export-stat-item">
                  <small>TRUST QUALITY</small>
                  <strong>96.4%</strong>
                </div>
              </div>
            </div>

            <div className="export-options-list">
              <button
                type="button"
                className="export-option-card"
                onClick={handleExportJson}
                id="export-json-btn"
              >
                <div className="export-option-icon">
                  <Icon name="command" size={18} />
                </div>
                <div className="export-option-info">
                  <strong>Download Full Telemetry Report (.JSON)</strong>
                  <small>Comprehensive metadata, statistics, deviations & model trust confidence</small>
                </div>
                <Icon name="arrow" size={14} />
              </button>

              <button
                type="button"
                className="export-option-card"
                onClick={handleExportCsv}
                id="export-csv-btn"
              >
                <div className="export-option-icon">
                  <Icon name="activity" size={18} />
                </div>
                <div className="export-option-info">
                  <strong>Download CSV Data Spreadsheet (.CSV)</strong>
                  <small>Tabular time-series values suitable for Excel, Python, or statistical software</small>
                </div>
                <Icon name="arrow" size={14} />
              </button>

              <button
                type="button"
                className="export-option-card"
                onClick={handlePrint}
                id="export-print-btn"
              >
                <div className="export-option-icon">
                  <Icon name="history" size={18} />
                </div>
                <div className="export-option-info">
                  <strong>Print / Save as PDF</strong>
                  <small>Formatted document snapshot for clinical consultation or records</small>
                </div>
                <Icon name="arrow" size={14} />
              </button>
            </div>
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
