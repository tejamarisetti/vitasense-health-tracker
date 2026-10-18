import React, { useState } from 'react';
import { Icon } from '../components/Icons';
import { MetricCard } from '../components/MetricCard';
import { Waveform } from '../components/Waveform';

interface OverviewPageProps {
  go: (page: string) => void;
}

export function OverviewPage({ go }: OverviewPageProps) {
  const [activeRange, setActiveRange] = useState('LIVE');

  return (
    <div className="overview">
      <div className="page-title">
        <div>
          <span className="app-kicker">MONDAY, MAY 20</span>
          <h1>
            Your health, <em>at a glance.</em>
          </h1>
          <p>Good morning, Alex. Here’s what your signals are saying today.</p>
        </div>
        <button
          className="button button-soft"
          onClick={() => go('trends')}
          type="button"
        >
          <Icon name="history" /> View health history
        </button>
      </div>

      <div className="dashboard-grid">
        {/* Real-time Body Signals */}
        <article className="body-signals">
          <div className="panel-top">
            <div>
              <span className="app-kicker">REAL-TIME OVERVIEW</span>
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
              <span>HEART RATE</span>
              <strong>
                72 <small>BPM</small>
              </strong>
              <b>Within your typical range</b>
            </div>
            <div>
              <span>SpO₂ ESTIMATE</span>
              <strong>
                97<small>%</small>
              </strong>
              <b>Illustrative measurement</b>
            </div>
          </div>

          <div className="live-chart">
            <div className="chart-grid" />
            <Waveform large />
            <span className="chart-note">
              72 BPM <i>10:42:06</i>
            </span>
          </div>

          <div className="signal-meta">
            <span>
              <i className="live-dot" /> Streaming demo data
            </span>
            <span>Last updated 10:42 AM</span>
            <span>Source: Demo wearable</span>
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
            <button type="button" aria-label="More options">
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
            Your recent measurements show a change from your previous baseline.
            Review the trend and confirm that the latest readings are reliable.
          </p>

          <div className="uncertainty">
            <Icon name="shield" />
            <span>
              <b>Context matters</b>
              This is an observation, not a diagnosis.
            </span>
          </div>

          <div className="insight-actions">
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
            label="SpO₂ ESTIMATE"
            value="97"
            unit="%"
            change="1.2%"
          >
            <svg className="mini-spark" viewBox="0 0 180 45">
              <path d="M0 31 22 29 40 30 57 17 72 25 89 23 108 9 125 23 146 20 180 12" />
            </svg>
          </MetricCard>

          <MetricCard
            icon="activity"
            label="RESPIRATORY RATE"
            value="16"
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
              <span className="quality-score">96%</span>
            </div>
            <div className="quality-bar">
              <i />
            </div>
            <div className="quality-list">
              <span>
                <i className="good" /> Completeness <b>98%</b>
              </span>
              <span>
                <i className="good" /> Freshness <b>Current</b>
              </span>
              <span>
                <i className="warn" /> Flagged readings <b>2</b>
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
              <span className="app-kicker">7-DAY TREND</span>
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
            <button type="button" aria-label="More options">
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
                <small>Heart rate · 72 BPM</small>
              </p>
              <time>10:42 AM</time>
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
                <small>98% completeness</small>
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
            All measurements shown are illustrative demo data and are not intended
            for diagnosis or medical decisions.
          </span>
          <button type="button">Learn more</button>
        </div>
      </div>
    </div>
  );
}
