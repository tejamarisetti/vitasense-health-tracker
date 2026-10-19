import React, { useEffect, useState } from 'react';
import { Icon } from '../components/Icons';

interface SettingsPageProps {
  go: (page: string) => void;
  theme?: 'dark' | 'light';
  setTheme?: (theme: 'dark' | 'light') => void;
}

interface AssistantHealth {
  status: string;
  engine: string;
  category: string;
}

export function SettingsPage({ go, theme = 'dark', setTheme }: SettingsPageProps) {
  const [health, setHealth] = useState<AssistantHealth | null>(null);
  const [selectedSubject, setSelectedSubject] = useState('S1');
  const [waveformSpeed, setWaveformSpeed] = useState('1.0x');

  useEffect(() => {
    fetch('/api/assistant/health')
      .then((r) => r.json())
      .then((data) => setHealth(data))
      .catch(() => setHealth({ status: 'fallback', engine: 'rule_fallback', category: 'connection error' }));
  }, []);

  return (
    <div className="settings-page">
      <div className="page-title">
        <div>
          <span className="app-kicker">SYSTEM PREFERENCES</span>
          <h1>Settings & System Diagnostics</h1>
          <p>
            Configure telemetry replay, inspect assistant engine health, and access research evaluation benchmarks.
          </p>
        </div>
      </div>

      <div className="settings-grid">
        {/* Research (evaluators) Section - Requirement 4 */}
        <section className="settings-section research-evaluators-section">
          <div className="section-header">
            <div className="section-icon-wrap mint">
              <Icon name="command" />
            </div>
            <div>
              <h2>Research (evaluators)</h2>
              <p>Statistical benchmarks, validation results, and paired hypothesis tests for reviewers.</p>
            </div>
          </div>

          <div className="research-eval-card">
            <div className="eval-card-header">
              <span className="status-pill info">15-Subject Protocol</span>
              <span className="eval-badge">Ratified Empirical Results</span>
            </div>
            <h3>PPG-DaLiA Benchmark Evaluation Suite</h3>
            <p>
              Inspect the empirical performance comparison between Arm 1 (unvalidated baseline),
              Arm 2 (ENMO motion gate), Arm 3a (heuristic trust filter), and Arm 3b (adaptive ramp).
              Includes paired Wilcoxon signed-rank tests, 95% confidence intervals, per-fault breakdown (F1–F7),
              and edge-of-grid cross-validation distributions.
            </p>

            <div className="eval-card-highlights">
              <div>
                <small>Core Finding</small>
                <strong>H1 Not Supported</strong>
              </div>
              <div>
                <small>Coverage</small>
                <strong>15 Subjects · 38.8 hrs</strong>
              </div>
              <div>
                <small>Evaluated Regimes</small>
                <strong>All, Still, Motion, Transient</strong>
              </div>
            </div>

            <div className="eval-card-footer">
              <button
                className="button button-primary"
                onClick={() => go('benchmark')}
                type="button"
                id="view-benchmarks-button"
              >
                <span>Launch Benchmark Results</span>
                <Icon name="arrow" />
              </button>
            </div>
          </div>
        </section>

        {/* Assistant Engine & Health Diagnostics */}
        <section className="settings-section">
          <div className="section-header">
            <div className="section-icon-wrap violet">
              <Icon name="ai" />
            </div>
            <div>
              <h2>Assistant Engine Diagnostics</h2>
              <p>Live classification status and fallback routing inspection.</p>
            </div>
          </div>

          <div className="settings-card">
            <div className="diagnostic-row">
              <span className="diag-label">Active Assistant Engine</span>
              <div className="diag-value">
                <span className={`engine-dot ${health?.engine === 'llm' ? 'ok' : 'fallback'}`} />
                <strong>{health?.engine === 'llm' ? 'LLM (Cloud AI)' : 'Rule Fallback Engine'}</strong>
              </div>
            </div>

            <div className="diagnostic-row">
              <span className="diag-label">Health Status</span>
              <span className={`status-pill ${health?.status === 'ok' ? '' : 'warning'}`}>
                {health?.status === 'ok' ? 'Healthy (200 OK)' : `Fallback Active (${health?.category || 'evaluating'})`}
              </span>
            </div>

            <div className="diagnostic-row">
              <span className="diag-label">Intent Classification</span>
              <span className="diag-text">
                Fuzzy greeting regex + rule-based ambiguity guard with zero data leaks.
              </span>
            </div>

            <div className="diagnostic-row">
              <span className="diag-label">Key Security Audit</span>
              <span className="diag-badge-secure">
                <Icon name="shield" size={14} />
                <span>Zero keys logged, echoed, or stored in client bundles</span>
              </span>
            </div>
          </div>
        </section>

        {/* Replay Telemetry Preferences */}
        <section className="settings-section">
          <div className="section-header">
            <div className="section-icon-wrap cyan">
              <Icon name="activity" />
            </div>
            <div>
              <h2>Replay Telemetry Data</h2>
              <p>Configure cached PPG-DaLiA subject stream for Signal Lab.</p>
            </div>
          </div>

          <div className="settings-card">
            <div className="diagnostic-row">
              <span className="diag-label">Active Subject Dataset</span>
              <select
                className="settings-select"
                value={selectedSubject}
                onChange={(e) => setSelectedSubject(e.target.value)}
              >
                {Array.from({ length: 15 }, (_, i) => `S${i + 1}`).map((s) => (
                  <option key={s} value={s}>
                    {s} (PPG-DaLiA Protocol)
                  </option>
                ))}
              </select>
            </div>

            <div className="diagnostic-row">
              <span className="diag-label">Signal Playback Speed</span>
              <div className="speed-selector">
                {['0.5x', '1.0x', '2.0x'].map((sp) => (
                  <button
                    key={sp}
                    type="button"
                    className={`speed-btn ${waveformSpeed === sp ? 'active' : ''}`}
                    onClick={() => setWaveformSpeed(sp)}
                  >
                    {sp}
                  </button>
                ))}
              </div>
            </div>

            <div className="diagnostic-row">
              <span className="diag-label">Data Environment</span>
              <span className="diag-text">REPLAY: public dataset, not live · Read-only disk cache</span>
            </div>
          </div>
        </section>

        {/* Display & Appearance */}
        {setTheme && (
          <section className="settings-section">
            <div className="section-header">
              <div className="section-icon-wrap">
                <Icon name={theme === 'dark' ? 'sun' : 'moon'} />
              </div>
              <div>
                <h2>Appearance</h2>
                <p>Customize interface theme and contrast.</p>
              </div>
            </div>

            <div className="settings-card">
              <div className="diagnostic-row">
                <span className="diag-label">Interface Theme</span>
                <div className="theme-toggle-row">
                  <button
                    type="button"
                    className={`button ${theme === 'dark' ? 'button-primary' : 'button-soft'}`}
                    onClick={() => setTheme('dark')}
                  >
                    <Icon name="moon" size={16} />
                    <span>Dark Theme</span>
                  </button>
                  <button
                    type="button"
                    className={`button ${theme === 'light' ? 'button-primary' : 'button-soft'}`}
                    onClick={() => setTheme('light')}
                  >
                    <Icon name="sun" size={16} />
                    <span>Light Theme</span>
                  </button>
                </div>
              </div>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
