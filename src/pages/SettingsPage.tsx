import { apiEndpoint } from '../api';
import React, { useEffect, useState } from 'react';
import { Icon } from '../components/Icons';
import { getAuthToken, clearAuthToken } from '../types';

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

  // Contact Us state (FR-11)
  const [contactName, setContactName] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [contactCategory, setContactCategory] = useState('general');
  const [contactSubject, setContactSubject] = useState('');
  const [contactMessage, setContactMessage] = useState('');
  const [contactStatus, setContactStatus] = useState<{ type: 'success' | 'error' | 'rate-limit'; text: string } | null>(null);
  const [contactSubmitting, setContactSubmitting] = useState(false);

  // Privacy & Account Controls state (FR-13)
  const [exportLoading, setExportLoading] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deletePassword, setDeletePassword] = useState('');
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [accountActionMessage, setAccountActionMessage] = useState<string | null>(null);

  const isLoggedIn = !!getAuthToken();

  useEffect(() => {
    fetch(apiEndpoint('/api/assistant/health'))
      .then((r) => r.json())
      .then((data) => setHealth(data))
      .catch(() => setHealth({ status: 'fallback', engine: 'rule_fallback', category: 'connection error' }));
  }, []);

  const handleContactSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setContactStatus(null);
    setContactSubmitting(true);

    try {
      const res = await fetch(apiEndpoint('/api/contact'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: contactName,
          email: contactEmail,
          category: contactCategory,
          subject: contactSubject,
          message: contactMessage,
        }),
      });

      const data = await res.json();
      if (res.status === 200) {
        setContactStatus({
          type: 'success',
          text: `✓ Message sent successfully! Confirmation ID: #${data.inquiry_id}. We have received your inquiry.`,
        });
        setContactSubject('');
        setContactMessage('');
      } else if (res.status === 429) {
        setContactStatus({
          type: 'rate-limit',
          text: `⚠️ Rate limit exceeded: ${data.detail || 'Too many submissions. Please wait 1 minute before sending another message.'}`,
        });
      } else {
        setContactStatus({
          type: 'error',
          text: `⚠️ Validation error: ${data.detail || 'Could not submit inquiry. Please review your input.'}`,
        });
      }
    } catch (err) {
      setContactStatus({
        type: 'error',
        text: '⚠️ Network error: Could not reach the server to submit inquiry.',
      });
    } finally {
      setContactSubmitting(false);
    }
  };

  const handleExportData = async () => {
    const token = getAuthToken();
    if (!token) {
      setAccountActionMessage('⚠️ You must be signed in to export your personal health data.');
      return;
    }

    setExportLoading(true);
    setAccountActionMessage(null);
    try {
      const res = await fetch(apiEndpoint('/api/auth/export'), {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        const data = await res.json();
        const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(JSON.stringify(data, null, 2))}`;
        const downloadAnchor = document.createElement('a');
        downloadAnchor.setAttribute('href', jsonString);
        downloadAnchor.setAttribute('download', `vitasense-account-export-${new Date().toISOString().slice(0, 10)}.json`);
        document.body.appendChild(downloadAnchor);
        downloadAnchor.click();
        downloadAnchor.remove();

        setAccountActionMessage('✓ Full account telemetry, profile, and alert records exported successfully.');
      } else {
        const err = await res.json();
        setAccountActionMessage(`⚠️ Export failed: ${err.detail || 'Unauthorized'}`);
      }
    } catch (err) {
      setAccountActionMessage('⚠️ Network error during data export.');
    } finally {
      setExportLoading(false);
    }
  };

  const handleDeleteAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = getAuthToken();
    if (!token) {
      setAccountActionMessage('⚠️ You must be signed in to perform account deletion.');
      return;
    }

    setDeleteLoading(true);
    try {
      const res = await fetch(apiEndpoint('/api/auth/account'), {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ password: deletePassword }),
      });

      if (res.ok) {
        clearAuthToken();
        localStorage.removeItem('vitasense_user_profile');
        setDeleteConfirmOpen(false);
        alert('Your account, telemetry measurements, and alerts have been permanently deleted.');
        go('landing');
      } else {
        const err = await res.json();
        alert(`Deletion failed: ${err.detail || 'Password incorrect or unauthorized.'}`);
      }
    } catch (err) {
      alert('Network error while deleting account.');
    } finally {
      setDeleteLoading(false);
    }
  };

  return (
    <div className="settings-page">
      <div className="page-title">
        <div>
          <span className="app-kicker">SYSTEM PREFERENCES & PRIVACY</span>
          <h1>Settings, Support & Privacy</h1>
          <p>
            Configure telemetry replay, submit inquiries, manage privacy controls, and access research evaluation benchmarks.
          </p>
        </div>
      </div>

      <div className="settings-grid">
        {/* Research (evaluators) Section */}
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
              <span className="eval-badge">Empirical Results</span>
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

        {/* Privacy & Account Controls (FR-13) */}
        <section className="settings-section">
          <div className="section-header">
            <div className="section-icon-wrap" style={{ background: 'rgba(167, 139, 250, 0.15)', color: 'var(--violet)' }}>
              <Icon name="shield" />
            </div>
            <div>
              <h2>Privacy & Account Controls (FR-13)</h2>
              <p>Self-service data export, GDPR/HIPAA-aligned record download, and permanent account removal.</p>
            </div>
          </div>

          <div className="settings-card">
            {accountActionMessage && (
              <div
                style={{
                  background: accountActionMessage.startsWith('✓') ? 'rgba(5, 150, 105, 0.12)' : 'rgba(239, 68, 68, 0.12)',
                  border: accountActionMessage.startsWith('✓') ? '1px solid rgba(5, 150, 105, 0.3)' : '1px solid rgba(239, 68, 68, 0.3)',
                  color: accountActionMessage.startsWith('✓') ? 'var(--mint)' : '#f87171',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  fontSize: '12px',
                  marginBottom: '16px',
                }}
              >
                {accountActionMessage}
              </div>
            )}

            <div className="diagnostic-row" style={{ alignItems: 'flex-start', paddingBottom: '16px' }}>
              <div>
                <strong style={{ fontSize: '13px', display: 'block', marginBottom: '4px' }}>Export Personal Data</strong>
                <span className="diag-text" style={{ fontSize: '11px', color: 'var(--muted)' }}>
                  Download all your stored profile records, physiological measurements, trust evaluations, and alerts as a sanitized JSON bundle.
                </span>
              </div>
              <button
                type="button"
                className="button button-primary"
                onClick={handleExportData}
                disabled={exportLoading || !isLoggedIn}
                style={{ minHeight: '38px', fontSize: '11px', whiteSpace: 'nowrap' }}
              >
                <Icon name="command" size={14} />
                <span>{exportLoading ? 'Exporting...' : isLoggedIn ? 'Export My Data (.JSON)' : 'Sign In Required'}</span>
              </button>
            </div>

            <div className="diagnostic-row" style={{ alignItems: 'flex-start', borderTop: '1px solid var(--line)', paddingTop: '16px' }}>
              <div>
                <strong style={{ fontSize: '13px', color: '#f87171', display: 'block', marginBottom: '4px' }}>
                  Delete Account & Erase Records
                </strong>
                <span className="diag-text" style={{ fontSize: '11px', color: 'var(--muted)' }}>
                  Permanently deletes your user credentials, sessions, profile, all historical measurements, and alert events. This cannot be undone.
                </span>
              </div>
              <button
                type="button"
                className="button button-quiet"
                onClick={() => setDeleteConfirmOpen(true)}
                disabled={!isLoggedIn}
                style={{
                  minHeight: '38px',
                  fontSize: '11px',
                  borderColor: 'rgba(239, 68, 68, 0.35)',
                  color: '#f87171',
                  whiteSpace: 'nowrap',
                }}
              >
                <span>{isLoggedIn ? 'Delete Account' : 'Sign In Required'}</span>
              </button>
            </div>
          </div>
        </section>

        {/* Contact Us Section (FR-11) */}
        <section className="settings-section">
          <div className="section-header">
            <div className="section-icon-wrap cyan">
              <Icon name="activity" />
            </div>
            <div>
              <h2>Contact Support & Research Inquiries (FR-11)</h2>
              <p>Submit platform inquiries, protocol questions, or data feedback directly to the team.</p>
            </div>
          </div>

          <div className="settings-card">
            <div
              style={{
                fontSize: '11px',
                color: 'var(--faint)',
                marginBottom: '14px',
                background: 'rgba(125, 211, 252, 0.05)',
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid rgba(125, 211, 252, 0.15)',
              }}
            >
              🔒 <strong>Privacy Assurance:</strong> Messages are securely stored with rate-limiting protection. No personal health telemetry is ever captured or logged during inquiries.
            </div>

            {contactStatus && (
              <div
                style={{
                  background:
                    contactStatus.type === 'success'
                      ? 'rgba(5, 150, 105, 0.12)'
                      : contactStatus.type === 'rate-limit'
                      ? 'rgba(245, 158, 11, 0.12)'
                      : 'rgba(239, 68, 68, 0.12)',
                  border:
                    contactStatus.type === 'success'
                      ? '1px solid rgba(5, 150, 105, 0.3)'
                      : contactStatus.type === 'rate-limit'
                      ? '1px solid rgba(245, 158, 11, 0.3)'
                      : '1px solid rgba(239, 68, 68, 0.3)',
                  color:
                    contactStatus.type === 'success'
                      ? 'var(--mint)'
                      : contactStatus.type === 'rate-limit'
                      ? '#f59e0b'
                      : '#f87171',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  fontSize: '12px',
                  marginBottom: '16px',
                }}
              >
                {contactStatus.text}
              </div>
            )}

            <form onSubmit={handleContactSubmit}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                <div>
                  <label style={{ fontSize: '11px', color: 'var(--muted)', display: 'block', marginBottom: '4px' }}>
                    Your Name
                  </label>
                  <input
                    type="text"
                    value={contactName}
                    onChange={(e) => setContactName(e.target.value)}
                    placeholder="Alex Morgan"
                    required
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: '8px',
                      border: '1px solid var(--line-strong)',
                      background: 'var(--panel-2)',
                      color: 'var(--text)',
                      fontSize: '12px',
                    }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: '11px', color: 'var(--muted)', display: 'block', marginBottom: '4px' }}>
                    Email Address
                  </label>
                  <input
                    type="email"
                    value={contactEmail}
                    onChange={(e) => setContactEmail(e.target.value)}
                    placeholder="user@example.com"
                    required
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: '8px',
                      border: '1px solid var(--line-strong)',
                      background: 'var(--panel-2)',
                      color: 'var(--text)',
                      fontSize: '12px',
                    }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '12px', marginBottom: '12px' }}>
                <div>
                  <label style={{ fontSize: '11px', color: 'var(--muted)', display: 'block', marginBottom: '4px' }}>
                    Category
                  </label>
                  <select
                    value={contactCategory}
                    onChange={(e) => setContactCategory(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: '8px',
                      border: '1px solid var(--line-strong)',
                      background: 'var(--panel-2)',
                      color: 'var(--text)',
                      fontSize: '12px',
                    }}
                  >
                    <option value="general">General Inquiry</option>
                    <option value="research">Research Protocol</option>
                    <option value="bug_report">Bug Report</option>
                    <option value="privacy">Privacy Request</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '11px', color: 'var(--muted)', display: 'block', marginBottom: '4px' }}>
                    Subject
                  </label>
                  <input
                    type="text"
                    value={contactSubject}
                    onChange={(e) => setContactSubject(e.target.value)}
                    placeholder="Summary of your inquiry..."
                    required
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: '8px',
                      border: '1px solid var(--line-strong)',
                      background: 'var(--panel-2)',
                      color: 'var(--text)',
                      fontSize: '12px',
                    }}
                  />
                </div>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ fontSize: '11px', color: 'var(--muted)', display: 'block', marginBottom: '4px' }}>
                  Message (min 10 characters)
                </label>
                <textarea
                  value={contactMessage}
                  onChange={(e) => setContactMessage(e.target.value)}
                  placeholder="Provide details about your question, protocol replication, or issue..."
                  rows={4}
                  required
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    border: '1px solid var(--line-strong)',
                    background: 'var(--panel-2)',
                    color: 'var(--text)',
                    fontSize: '12px',
                    resize: 'vertical',
                  }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button
                  type="submit"
                  className="button button-primary"
                  disabled={contactSubmitting}
                  style={{ minHeight: '38px', fontSize: '12px' }}
                >
                  <Icon name="arrow" size={14} />
                  <span>{contactSubmitting ? 'Submitting securely...' : 'Send Inquiry'}</span>
                </button>
              </div>
            </form>
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

      {/* Account Deletion Confirmation Modal */}
      {deleteConfirmOpen && (
        <div className="add-meas-modal-backdrop" onClick={() => setDeleteConfirmOpen(false)}>
          <div className="add-meas-modal" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
              <div>
                <span className="app-kicker" style={{ color: '#f87171' }}>IRREVERSIBLE ACTION</span>
                <h3 style={{ margin: '4px 0 0', fontSize: '18px', color: '#f87171' }}>Confirm Account Deletion</h3>
              </div>
              <button
                className="export-dialog-close"
                onClick={() => setDeleteConfirmOpen(false)}
                type="button"
              >
                ✕
              </button>
            </div>

            <p style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '16px', lineHeight: 1.5 }}>
              Are you completely sure? This will delete your account credentials, all associated measurements, and all logged alert observations. <strong>All your stored data will be permanently wiped from the database.</strong>
            </p>

            <form onSubmit={handleDeleteAccount}>
              <div style={{ marginBottom: '18px' }}>
                <label style={{ fontSize: '11px', color: 'var(--muted)', display: 'block', marginBottom: '6px' }}>
                  Please enter your password to confirm:
                </label>
                <input
                  type="password"
                  value={deletePassword}
                  onChange={(e) => setDeletePassword(e.target.value)}
                  placeholder="Your current password"
                  required
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: '8px',
                    border: '1px solid var(--line-strong)',
                    background: 'var(--panel-2)',
                    color: 'var(--text)',
                    fontSize: '12px',
                  }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button
                  type="button"
                  className="button button-quiet"
                  onClick={() => setDeleteConfirmOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="button"
                  disabled={deleteLoading}
                  style={{ background: '#ef4444', color: '#fff', borderColor: '#dc2626' }}
                >
                  {deleteLoading ? 'Deleting...' : 'Permanently Delete Everything'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
