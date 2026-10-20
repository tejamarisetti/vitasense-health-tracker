import React, { useState } from 'react';
import { Icon } from '../components/Icons';
import { loadUserProfile } from '../types';

export function TrendsPage() {
  const [activeRange, setActiveRange] = useState('7D');
  const [showExportModal, setShowExportModal] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const profile = loadUserProfile();

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
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
                <stop offset="1" stopColor="#35e6d3" stopOpacity="0" />
              </linearGradient>
            </defs>
            <path
              className="trend-area"
              d="M0 260 C80 270 95 180 170 205 S267 285 340 225 440 90 510 160 615 280 690 190 820 95 1000 110 V360H0Z"
            />
            <path
              className="baseline"
              d="M0 230 C170 206 270 239 400 207 S700 222 1000 188"
            />
            <path
              className="trend-line"
              d="M0 260 C80 270 95 180 170 205 S267 285 340 225 440 90 510 160 615 280 690 190 820 95 1000 110"
            />
            <line className="cursor-line" x1="510" y1="0" x2="510" y2="360" />
            <circle cx="510" cy="160" r="7" />
          </svg>
        </div>

        <div className="chart-labels">
          <span>MON 20</span>
          <span>TUE 21</span>
          <span>WED 22</span>
          <span>THU 23</span>
          <span>FRI 24</span>
          <span>SAT 25</span>
          <span>SUN 26</span>
        </div>
      </article>

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
