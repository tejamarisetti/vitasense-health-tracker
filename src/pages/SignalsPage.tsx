import React, { useState } from 'react';
import { Icon } from '../components/Icons';
import { Waveform } from '../components/Waveform';

export function SignalsPage() {
  const [eventStatus, setEventStatus] = useState<'flagged' | 'accepted' | 'excluded'>('flagged');

  return (
    <div className="feature-page">
      <div className="page-title">
        <div>
          <span className="app-kicker">SIGNAL LAB / VALIDATION</span>
          <h1>
            Trust begins with <em>good data.</em>
          </h1>
          <p>
            Inspect signal integrity, artifacts, and software-level validation checks.
          </p>
        </div>
        <button className="button button-soft" type="button">
          Export report <Icon name="arrow" />
        </button>
      </div>

      <div className="validation-grid">
        {/* Signal Inspector */}
        <article className="signal-inspector">
          <div className="panel-top">
            <div>
              <small>RAW SIGNAL · TODAY, 10:30–10:45</small>
              <h2>Sensor waveform</h2>
            </div>
            <span className="status-pill">Analysis complete</span>
          </div>

          <div className="validation-wave">
            <Waveform large />
            <span className="flag flag-one">Motion artifact</span>
            <span className="flag flag-two">Missing data · 4s</span>
          </div>

          <div className="chart-labels">
            <span>10:30</span>
            <span>10:33</span>
            <span>10:36</span>
            <span>10:39</span>
            <span>10:42</span>
            <span>10:45</span>
          </div>
        </article>

        {/* Quality Summary */}
        <article className="validation-summary">
          <span className="app-kicker">QUALITY SUMMARY</span>
          <div className="big-quality">
            <strong>96</strong>
            <span>
              %<small>High integrity</small>
            </span>
          </div>

          <div className="quality-bar">
            <i />
          </div>

          <ul>
            <li>
              <span>
                <i className="good" /> Completeness
              </span>
              <b>98.4%</b>
            </li>
            <li>
              <span>
                <i className="good" /> Freshness
              </span>
              <b>12 sec</b>
            </li>
            <li>
              <span>
                <i className="warn" /> Potential artifacts
              </span>
              <b>2</b>
            </li>
            <li>
              <span>
                <i className="good" /> Out-of-range values
              </span>
              <b>None</b>
            </li>
          </ul>
        </article>

        {/* Event Inspector */}
        <article className="event-inspector">
          <div>
            <span className="app-kicker">EVENT INSPECTOR</span>
            <h3>Potential motion artifact</h3>
            <p>10:37:18 · Reading #VS-10428</p>
          </div>

          <div className="event-details">
            <span>
              <small>ORIGINAL READING</small>
              <b>104 BPM</b>
            </span>
            <span>
              <small>VALIDATION RESULT</small>
              <b className={eventStatus === 'flagged' ? 'flagged' : ''}>
                {eventStatus === 'flagged'
                  ? 'Flagged'
                  : eventStatus === 'accepted'
                  ? 'Accepted'
                  : 'Excluded'}
              </b>
            </span>
            <span>
              <small>CHECKS APPLIED</small>
              <b>4 of 4</b>
            </span>
          </div>

          <div className="explanation">
            <Icon name="ai" />
            <p>
              <b>Why was this flagged?</b>
              The reading changed rapidly while signal noise increased. This
              software check may indicate movement; it does not test the physical
              accuracy of the sensor.
            </p>
          </div>

          <div className="event-actions">
            <button
              onClick={() => setEventStatus('accepted')}
              type="button"
              style={{
                borderColor: eventStatus === 'accepted' ? 'var(--mint)' : undefined,
                color: eventStatus === 'accepted' ? 'var(--mint)' : undefined
              }}
            >
              Accept reading
            </button>
            <button
              onClick={() => setEventStatus('excluded')}
              type="button"
              style={{
                borderColor: eventStatus === 'excluded' ? 'var(--violet)' : undefined,
                color: eventStatus === 'excluded' ? 'var(--violet)' : undefined
              }}
            >
              Exclude from trends
            </button>
          </div>
        </article>
      </div>
    </div>
  );
}
