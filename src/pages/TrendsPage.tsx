import React, { useState } from 'react';
import { Icon } from '../components/Icons';

export function TrendsPage() {
  const [activeRange, setActiveRange] = useState('7D');

  return (
    <div className="feature-page">
      <div className="page-title">
        <div>
          <span className="app-kicker">HEALTH TRENDS</span>
          <h1>
            Patterns, <em>made visible.</em>
          </h1>
          <p>
            Compare signals with your historical baseline and inspect every
            deviation.
          </p>
        </div>
        <button className="button button-soft" type="button">
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
    </div>
  );
}
