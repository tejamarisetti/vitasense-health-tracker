import React from 'react';
import { Icon } from '../components/Icons';

interface AlertsPageProps {
  go?: (page: string) => void;
}

export function AlertsPage({ go }: AlertsPageProps) {
  return (
    <div className="feature-page">
      <div className="page-title">
        <div>
          <span className="app-kicker">ALERT CENTER</span>
          <h1>
            Signals that need <em>your attention.</em>
          </h1>
          <p>
            Health observations and data-quality warnings are kept clearly
            separate.
          </p>
        </div>
      </div>

      <div className="alerts-list">
        {/* Data Quality Section */}
        <div className="alert-section">
          <h2>Data quality</h2>
          <article onClick={() => go?.('signals')} style={{ cursor: 'pointer' }}>
            <span className="alert-icon warning">
              <Icon name="activity" />
            </span>
            <div>
              <span className="status-pill warning">Review suggested</span>
              <h3>Two readings may contain motion artifacts</h3>
              <p>
                Rapid signal change and increased noise were detected in today’s
                wearable data.
              </p>
              <small>Today · 10:37 AM · Supporting data available</small>
            </div>
            <button
              type="button"
              aria-label="Inspect alert"
              onClick={(e) => {
                e.stopPropagation();
                go?.('signals');
              }}
            >
              <Icon name="chevron" />
            </button>
          </article>
        </div>

        {/* Health Observations Section */}
        <div className="alert-section">
          <h2>Health observations</h2>
          <article onClick={() => go?.('trends')} style={{ cursor: 'pointer' }}>
            <span className="alert-icon info">
              <Icon name="trend" />
            </span>
            <div>
              <span className="status-pill info">Observation</span>
              <h3>Recent measurements differ from your baseline</h3>
              <p>
                Review the seven-day trend and confirm the latest readings are
                reliable.
              </p>
              <small>Today · 9:18 AM · Not a diagnosis</small>
            </div>
            <button
              type="button"
              aria-label="Inspect observation"
              onClick={(e) => {
                e.stopPropagation();
                go?.('trends');
              }}
            >
              <Icon name="chevron" />
            </button>
          </article>
        </div>
      </div>
    </div>
  );
}
