import React, { useState, useEffect } from 'react';
import { Icon } from '../components/Icons';
import { UserAlert, getAuthToken } from '../types';

interface AlertsPageProps {
  go?: (page: string) => void;
}

export function AlertsPage({ go }: AlertsPageProps) {
  const [alerts, setAlerts] = useState<UserAlert[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'all' | 'active' | 'acknowledged' | 'dismissed'>('active');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Modal for creating/triggering an alert (test duplicate suppression)
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newTitle, setNewTitle] = useState('Elevated Heart Rate Observed');
  const [newMessage, setNewMessage] = useState('Resting pulse observed at 94 bpm across 3 consecutive epochs during low motion.');
  const [newSeverity, setNewSeverity] = useState<'info' | 'warning' | 'critical'>('warning');
  const [newCategory, setNewCategory] = useState('observation');
  const [createSubmitting, setCreateSubmitting] = useState(false);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4500);
  };

  const fetchAlerts = async () => {
    const token = getAuthToken();
    if (!token) {
      // Demo alerts for unauthenticated preview
      setAlerts([
        {
          id: 101,
          user_id: 1,
          title: 'Two readings may contain motion artifacts',
          message: 'Rapid signal change and increased noise were detected in wearable telemetry stream during subject movement.',
          severity: 'warning',
          category: 'quality',
          status: 'active',
          created_at: new Date(Date.now() - 3600000).toISOString(),
          informational_notice: 'For informational purposes only; not a medical diagnosis or clinical alert.',
        },
        {
          id: 102,
          user_id: 1,
          title: 'Recent measurements differ from baseline',
          message: 'Review the seven-day trend and confirm the latest readings are reliable against your 64 BPM resting baseline.',
          severity: 'info',
          category: 'health',
          status: 'active',
          created_at: new Date(Date.now() - 7200000).toISOString(),
          informational_notice: 'For informational purposes only; not a medical diagnosis or clinical alert.',
        },
      ]);
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`/api/alerts?status=${activeTab}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setAlerts(data);
      } else {
        console.warn('Failed to fetch user alerts');
      }
    } catch (err) {
      console.warn('Network error loading alerts', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, [activeTab]);

  const handleAcknowledge = async (id: number) => {
    const token = getAuthToken();
    if (!token) {
      setAlerts((prev) =>
        prev.map((a) =>
          a.id === id ? { ...a, status: 'acknowledged', acknowledged_at: new Date().toISOString() } : a
        )
      );
      showToast('✓ Alert acknowledged (stored in historical records; event is preserved).');
      return;
    }

    try {
      const res = await fetch(`/api/alerts/${id}/acknowledge`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        showToast('✓ Alert acknowledged. Event retained in permanent record.');
        fetchAlerts();
      } else {
        const err = await res.json();
        showToast(`⚠️ Failed: ${err.detail || 'Could not acknowledge alert'}`);
      }
    } catch (err) {
      showToast('⚠️ Network error acknowledging alert');
    }
  };

  const handleDismiss = async (id: number) => {
    const token = getAuthToken();
    if (!token) {
      setAlerts((prev) =>
        prev.map((a) =>
          a.id === id ? { ...a, status: 'dismissed', dismissed_at: new Date().toISOString() } : a
        )
      );
      showToast('✓ Alert dismissed (dismissal recorded; event is never deleted).');
      return;
    }

    try {
      const res = await fetch(`/api/alerts/${id}/dismiss`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        showToast('✓ Alert dismissed. Preserved in user historical records.');
        fetchAlerts();
      } else {
        const err = await res.json();
        showToast(`⚠️ Failed: ${err.detail || 'Could not dismiss alert'}`);
      }
    } catch (err) {
      showToast('⚠️ Network error dismissing alert');
    }
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = getAuthToken();
    if (!token) {
      showToast('⚠️ Please log in to record user alerts.');
      setShowCreateModal(false);
      return;
    }

    setCreateSubmitting(true);
    try {
      const res = await fetch('/api/alerts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          title: newTitle,
          message: newMessage,
          severity: newSeverity,
          category: newCategory,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.duplicate) {
          showToast(`ℹ️ Duplicate Alert Suppressed: ${data.message}`);
        } else {
          showToast('✓ Alert created successfully.');
        }
        setShowCreateModal(false);
        fetchAlerts();
      } else {
        const err = await res.json();
        showToast(`⚠️ Error: ${err.detail || 'Failed to create alert'}`);
      }
    } catch (err) {
      showToast('⚠️ Network error submitting alert');
    } finally {
      setCreateSubmitting(false);
    }
  };

  return (
    <div className="feature-page">
      <div className="page-title">
        <div>
          <span className="app-kicker">INFORMATIONAL NOTIFICATIONS (FR-09)</span>
          <h1>
            Signals that need <em>your attention.</em>
          </h1>
          <p>
            Health observations and data-quality warnings are kept strictly separate. Events are permanent and never deleted upon acknowledgement.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            type="button"
            className="button button-primary"
            onClick={() => setShowCreateModal(true)}
            id="trigger-alert-btn"
          >
            <span>+ Log Observation Alert</span>
          </button>
        </div>
      </div>

      {/* Mandatory Informational Disclaimer Banner */}
      <div
        style={{
          background: 'rgba(53, 230, 211, 0.08)',
          border: '1px solid rgba(53, 230, 211, 0.25)',
          borderRadius: '12px',
          padding: '14px 18px',
          marginBottom: '24px',
          display: 'flex',
          alignItems: 'center',
          gap: '14px',
        }}
      >
        <span style={{ color: 'var(--aqua)', fontSize: '20px' }}>ℹ️</span>
        <div style={{ flex: 1, fontSize: '12px', lineHeight: 1.5, color: 'var(--muted)' }}>
          <strong style={{ color: 'var(--text)', display: 'block', marginBottom: '2px' }}>
            Informational Self-Monitoring Notice
          </strong>
          Alerts reflect user-specific software thresholds, data quality checks, and sensor artifacts. VitaSense AI does <strong>not</strong> provide continuous emergency monitoring or clinical diagnoses. In an acute emergency, always contact qualified medical services immediately.
        </div>
      </div>

      {/* Status Filter Tabs */}
      <div
        style={{
          display: 'flex',
          gap: '8px',
          borderBottom: '1px solid var(--line)',
          paddingBottom: '12px',
          marginBottom: '20px',
        }}
      >
        {(['active', 'acknowledged', 'dismissed', 'all'] as const).map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            style={{
              background: activeTab === tab ? 'var(--panel-2)' : 'transparent',
              color: activeTab === tab ? 'var(--mint)' : 'var(--muted)',
              border: activeTab === tab ? '1px solid var(--line-strong)' : '1px solid transparent',
              borderRadius: '8px',
              padding: '8px 16px',
              fontSize: '12px',
              fontWeight: activeTab === tab ? 600 : 500,
              textTransform: 'capitalize',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            {tab} Alerts
          </button>
        ))}
      </div>

      {/* Alerts List */}
      <div className="alerts-list">
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--muted)' }}>
            Loading your alert timeline...
          </div>
        ) : alerts.length === 0 ? (
          <div
            style={{
              textAlign: 'center',
              padding: '48px 24px',
              background: 'var(--panel)',
              borderRadius: '14px',
              border: '1px solid var(--line)',
              color: 'var(--muted)',
            }}
          >
            <div style={{ fontSize: '32px', marginBottom: '10px' }}>✓</div>
            <h3 style={{ margin: '0 0 6px', fontSize: '16px', color: 'var(--text)' }}>
              No {activeTab !== 'all' ? activeTab : ''} alerts found
            </h3>
            <p style={{ margin: 0, fontSize: '12px' }}>
              All physiological telemetry signals and data quality checks are operating within normal baseline limits.
            </p>
          </div>
        ) : (
          alerts.map((alert) => {
            const isWarning = alert.severity === 'warning';
            const isCritical = alert.severity === 'critical';
            const iconType = alert.category === 'quality' ? 'activity' : 'trend';
            const formattedDate = new Date(alert.created_at).toLocaleString([], {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            });

            return (
              <div key={alert.id} className="alert-section" style={{ marginBottom: '16px' }}>
                <article
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'auto 1fr auto',
                    gap: '18px',
                    padding: '20px',
                    borderRadius: '14px',
                    border: '1px solid var(--line)',
                    background: 'var(--panel)',
                    alignItems: 'center',
                  }}
                >
                  <span
                    className={`alert-icon ${isCritical ? 'warning' : isWarning ? 'warning' : 'info'}`}
                    style={{
                      background: isCritical
                        ? 'rgba(239, 68, 68, 0.15)'
                        : isWarning
                        ? 'rgba(255, 191, 105, 0.15)'
                        : 'rgba(125, 211, 252, 0.15)',
                      color: isCritical ? '#f87171' : isWarning ? '#ffbf69' : 'var(--cyan)',
                    }}
                  >
                    <Icon name={iconType} />
                  </span>

                  <div>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '6px' }}>
                      <span
                        className={`status-pill ${isCritical ? 'warning' : isWarning ? 'warning' : 'info'}`}
                        style={{
                          textTransform: 'uppercase',
                          letterSpacing: '0.05em',
                          fontWeight: 700,
                          fontSize: '9px',
                        }}
                      >
                        {alert.severity} · {alert.category}
                      </span>

                      <span
                        style={{
                          fontSize: '10px',
                          padding: '3px 7px',
                          borderRadius: '6px',
                          background:
                            alert.status === 'active'
                              ? 'rgba(53, 230, 211, 0.12)'
                              : alert.status === 'acknowledged'
                              ? 'rgba(167, 139, 250, 0.15)'
                              : 'rgba(144, 161, 185, 0.12)',
                          color:
                            alert.status === 'active'
                              ? 'var(--aqua)'
                              : alert.status === 'acknowledged'
                              ? 'var(--violet)'
                              : 'var(--muted)',
                          textTransform: 'capitalize',
                          fontWeight: 600,
                        }}
                      >
                        {alert.status}
                      </span>
                    </div>

                    <h3 style={{ margin: '0 0 6px', fontSize: '15px' }}>{alert.title}</h3>
                    <p style={{ color: 'var(--muted)', margin: '0 0 8px', fontSize: '12px', lineHeight: 1.5 }}>
                      {alert.message}
                    </p>

                    <div style={{ fontSize: '11px', color: 'var(--faint)', display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                      <span>Recorded: {formattedDate}</span>
                      {alert.acknowledged_at && (
                        <span style={{ color: 'var(--violet)' }}>
                          Acknowledged: {new Date(alert.acknowledged_at).toLocaleTimeString()}
                        </span>
                      )}
                      {alert.dismissed_at && (
                        <span>Dismissed: {new Date(alert.dismissed_at).toLocaleTimeString()}</span>
                      )}
                      <span style={{ fontStyle: 'italic' }}>• Informational only; event preserved</span>
                    </div>
                  </div>

                  {/* Actions: Acknowledge & Dismiss */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', minWidth: '120px' }}>
                    {alert.status === 'active' && (
                      <button
                        type="button"
                        className="button button-primary"
                        onClick={() => handleAcknowledge(alert.id)}
                        style={{ minHeight: '34px', fontSize: '11px', padding: '0 12px' }}
                      >
                        <Icon name="check" size={13} />
                        <span>Acknowledge</span>
                      </button>
                    )}

                    {alert.status !== 'dismissed' && (
                      <button
                        type="button"
                        className="button button-quiet"
                        onClick={() => handleDismiss(alert.id)}
                        style={{ minHeight: '34px', fontSize: '11px', padding: '0 12px' }}
                      >
                        <span>Dismiss</span>
                      </button>
                    )}

                    {alert.status === 'dismissed' && (
                      <span style={{ fontSize: '11px', color: 'var(--faint)', textAlign: 'center' }}>
                        Archived
                      </span>
                    )}
                  </div>
                </article>
              </div>
            );
          })
        )}
      </div>

      {/* Log Observation Modal (Test Duplicate Suppression & Alert Logging) */}
      {showCreateModal && (
        <div className="add-meas-modal-backdrop" onClick={() => setShowCreateModal(false)}>
          <div className="add-meas-modal" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '18px' }}>
              <div>
                <span className="app-kicker">USER OBSERVATION (FR-09)</span>
                <h3 style={{ margin: '4px 0 0', fontSize: '18px' }}>Log Informational Alert</h3>
              </div>
              <button
                className="export-dialog-close"
                onClick={() => setShowCreateModal(false)}
                type="button"
              >
                ✕
              </button>
            </div>

            <p style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '16px' }}>
              Create an observational alert for your personal timeline. Submissions within a 60-second window with the same title are automatically deduplicated.
            </p>

            <form onSubmit={handleCreateSubmit}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ fontSize: '11px', color: 'var(--muted)', display: 'block', marginBottom: '6px' }}>
                  Alert Title
                </label>
                <input
                  type="text"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
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

              <div style={{ marginBottom: '14px' }}>
                <label style={{ fontSize: '11px', color: 'var(--muted)', display: 'block', marginBottom: '6px' }}>
                  Message & Clinical Observation
                </label>
                <textarea
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  rows={3}
                  required
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: '8px',
                    border: '1px solid var(--line-strong)',
                    background: 'var(--panel-2)',
                    color: 'var(--text)',
                    resize: 'vertical',
                  }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '20px' }}>
                <div>
                  <label style={{ fontSize: '11px', color: 'var(--muted)', display: 'block', marginBottom: '6px' }}>
                    Severity
                  </label>
                  <select
                    value={newSeverity}
                    onChange={(e) => setNewSeverity(e.target.value as any)}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: '1px solid var(--line-strong)',
                      background: 'var(--panel-2)',
                      color: 'var(--text)',
                    }}
                  >
                    <option value="info">Info</option>
                    <option value="warning">Warning</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '11px', color: 'var(--muted)', display: 'block', marginBottom: '6px' }}>
                    Category
                  </label>
                  <select
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: '1px solid var(--line-strong)',
                      background: 'var(--panel-2)',
                      color: 'var(--text)',
                    }}
                  >
                    <option value="observation">Observation</option>
                    <option value="quality">Data Quality</option>
                    <option value="health">Physiological</option>
                    <option value="system">System</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button
                  type="button"
                  className="button button-quiet"
                  onClick={() => setShowCreateModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="button button-primary" disabled={createSubmitting}>
                  {createSubmitting ? 'Recording...' : 'Record Alert'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Floating Toast */}
      {toastMessage && (
        <div className="export-toast">
          <Icon name="check" size={16} />
          <span>{toastMessage}</span>
        </div>
      )}
    </div>
  );
}
