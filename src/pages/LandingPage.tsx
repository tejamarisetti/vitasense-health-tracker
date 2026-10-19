import React from 'react';
import { Logo } from '../components/Logo';
import { Icon } from '../components/Icons';
import { Orb } from '../components/Orb';
import { Waveform } from '../components/Waveform';

interface LandingPageProps {
  go: (page: string) => void;
  theme: 'dark' | 'light';
  setTheme: (theme: 'dark' | 'light') => void;
}

export function LandingPage({ go, theme, setTheme }: LandingPageProps) {
  return (
    <main className="landing">
      {/* Site Header */}
      <header className="site-header">
        <Logo />
        <nav className="site-nav" aria-label="Main navigation">
          <a href="#platform">Platform</a>
          <a href="#science">Science</a>
          <a href="#research">Research</a>
          <a href="#about">About</a>
        </nav>
        <div className="header-actions">
          <button
            className="icon-button"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            aria-label="Toggle theme"
            type="button"
          >
            <Icon name={theme === 'dark' ? 'sun' : 'moon'} />
          </button>
          <button
            className="button button-quiet"
            onClick={() => go('login')}
            type="button"
          >
            Sign in
          </button>
          <button
            className="button button-soft"
            onClick={() => go('create-account')}
            type="button"
          >
            Create account
          </button>
        </div>
      </header>

      {/* Hero Section */}
      <section className="hero">
        <div className="hero-grid" />
        <div className="hero-copy">
          <div className="eyebrow">
            <span /> Intelligence for every signal
          </div>
          <h1>
            Your health.
            <br />
            <em>Decoded by AI.</em>
          </h1>
          <p>
            Turn health data into meaningful insights with intelligent monitoring,
            personalized trends, and explainable AI.
          </p>
          <div className="hero-actions">
            <button
              className="button button-primary"
              onClick={() => go('create-account')}
              type="button"
            >
              Get Started <Icon name="arrow" />
            </button>
            <a className="text-link" href="#science">
              <span className="play">▶</span> Discover the technology
            </a>
          </div>
          <div className="trust-row">
            <span>
              <Icon name="shield" /> Privacy-first architecture
            </span>
            <span>
              <Icon name="sparkles" /> Explainable by design
            </span>
          </div>
        </div>

        <div className="hero-visual">
          <Orb />

          <div className="floating-card float-heart">
            <span className="float-icon mint">
              <Icon name="pulse" />
            </span>
            <div>
              <small>HEART RATE</small>
              <strong>
                72 <b>BPM</b>
              </strong>
            </div>
            <span className="trend-up">↗ 3%</span>
          </div>

          <div className="floating-card float-quality">
            <div className="quality-ring">
              <span>96</span>
            </div>
            <div>
              <small>DATA QUALITY</small>
              <strong>Excellent signal</strong>
              <p>All sensors connected</p>
            </div>
          </div>

          <div className="floating-card float-ai">
            <Icon name="sparkles" />
            <span>AI pattern detected</span>
            <i />
          </div>

          <span className="visual-label label-a">BIO SIGNAL · 01</span>
          <span className="visual-label label-b">LIVE ANALYSIS</span>
        </div>

        <a href="#platform" className="scroll-cue">
          <span /> Scroll to decode
        </a>
      </section>

      {/* 01 / LIVE HEALTH */}
      <section className="dimension section-shell" id="platform">
        <div className="section-heading">
          <div>
            <span className="kicker">01 / LIVE HEALTH</span>
            <h2>
              Health, in a
              <br />
              <em>new dimension.</em>
            </h2>
          </div>
          <p>
            A living picture of your wellbeing—signals, patterns, and context
            brought together in one calm, intelligent space.
          </p>
        </div>

        <div className="metric-stage">
          <div className="metric-feature">
            <div className="panel-top">
              <span>
                <i className="live-dot" /> LIVE SIGNAL
              </span>
              <button type="button" aria-label="More options">
                <Icon name="more" />
              </button>
            </div>
            <div className="metric-number">
              72 <small>BPM</small>
            </div>
            <Waveform large />
            <div className="metric-footer">
              <span>
                Resting range <b>60–100</b>
              </span>
              <span>Updated now</span>
            </div>
          </div>

          <div className="metric-stack">
            <article>
              <span className="float-icon cyan">
                <Icon name="drop" />
              </span>
              <div>
                <small>OXYGEN ESTIMATE</small>
                <strong>
                  97<sup>%</sup>
                </strong>
              </div>
              <span className="stable">Stable</span>
            </article>

            <article>
              <span className="float-icon violet">
                <Icon name="activity" />
              </span>
              <div>
                <small>RESPIRATORY RATE</small>
                <strong>
                  16<sup>/min</sup>
                </strong>
              </div>
              <svg className="spark" viewBox="0 0 120 40">
                <path d="M0 27 15 26 25 13 37 29 50 23 61 24 72 10 82 28 95 22 120 20" />
              </svg>
            </article>

            <div className="disclaimer">
              <Icon name="shield" />
              <span>
                <b>Illustrative demo measurements</b>
                Connect a supported data source to view personal insights.
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* 02 / EXPLAINABLE AI */}
      <section className="intelligence section-shell" id="science">
        <div className="ai-visual">
          <div className="mini-orb">
            <Orb small />
          </div>
          <span className="data-pill pill-a">
            Baseline
            <br />
            <b>Established</b>
          </span>
          <span className="data-pill pill-b">
            Confidence
            <br />
            <b>Context aware</b>
          </span>
          <span className="data-pill pill-c">
            Signal quality
            <br />
            <b>Validated</b>
          </span>
        </div>

        <div className="science-copy">
          <span className="kicker">02 / EXPLAINABLE AI</span>
          <h2>
            Intelligence behind
            <br />
            the <em>insights.</em>
          </h2>
          <p>
            VitaSense connects the dots without hiding the reasoning. Every
            insight includes the signals, context, and uncertainty behind it.
          </p>
          <ul>
            <li>
              <span>01</span>
              <div>
                <b>Patterns, not panic</b>
                <small>
                  Understand changes against your own historical baseline.
                </small>
              </div>
            </li>
            <li>
              <span>02</span>
              <div>
                <b>Evidence you can explore</b>
                <small>Trace every observation back to supporting data.</small>
              </div>
            </li>
            <li>
              <span>03</span>
              <div>
                <b>Uncertainty made visible</b>
                <small>Clear limitations. No black-box diagnoses.</small>
              </div>
            </li>
          </ul>
          <button
            className="text-button"
            onClick={() => go('companion')}
            type="button"
          >
            Meet your AI companion <Icon name="arrow" />
          </button>
        </div>
      </section>

      {/* 03 / THE FULL PICTURE */}
      <section className="story section-shell" id="research">
        <div className="story-head">
          <span className="kicker">03 / THE FULL PICTURE</span>
          <h2>
            Every signal tells a story.
            <br />
            <em>See the whole journey.</em>
          </h2>
        </div>

        <div className="story-grid">
          <article className="story-chart">
            <div className="panel-top">
              <div>
                <small>WEEKLY BASELINE</small>
                <strong>Your rhythm, over time</strong>
              </div>
              <span className="range-tabs">
                <b>7D</b>
                <i>30D</i>
                <i>90D</i>
              </span>
            </div>
            <svg viewBox="0 0 700 250" preserveAspectRatio="none">
              <defs>
                <linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
                  <stop stopColor="#35e6d3" stopOpacity=".3" />
                  <stop offset="1" stopColor="#35e6d3" stopOpacity="0" />
                </linearGradient>
              </defs>
              <path
                className="area"
                d="M0 198 C45 175 67 182 103 145 S174 177 215 130 283 102 326 135 395 113 430 83 503 122 550 71 637 67 700 35 V250H0Z"
              />
              <path
                className="chartline"
                d="M0 198 C45 175 67 182 103 145 S174 177 215 130 283 102 326 135 395 113 430 83 503 122 550 71 637 67 700 35"
              />
            </svg>
            <div className="chart-labels">
              <span>MON</span>
              <span>TUE</span>
              <span>WED</span>
              <span>THU</span>
              <span>FRI</span>
              <span>SAT</span>
              <span>SUN</span>
            </div>
          </article>

          <article className="research-card">
            <Icon name="command" size={26} />
            <span className="kicker">FOR RESEARCHERS</span>
            <h3>
              Built to question,
              <br />
              test, and learn.
            </h3>
            <p>
              Structured datasets, signal validation, experiment tracking, and
              transparent model evaluation in one workspace.
            </p>
            <div className="research-stats">
              <span>
                <b>04</b>
                Model runs
              </span>
              <span>
                <b>12k</b>
                Signal points
              </span>
            </div>
            <button onClick={() => go('signals')} type="button">
              Explore research tools <Icon name="arrow" />
            </button>
          </article>
        </div>
      </section>

      {/* Final CTA */}
      <section className="final-cta section-shell">
        <Orb small />
        <div>
          <span className="kicker">YOUR HEALTH, MORE CLEARLY</span>
          <h2>
            Ready to decode
            <br />
            your signals?
          </h2>
          <p>Step into a more connected view of your health.</p>
          <button
            className="button button-primary"
            onClick={() => go('login')}
            type="button"
          >
            Launch VitaSense <Icon name="arrow" />
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer>
        <Logo />
        <p>Intelligence for a healthier tomorrow.</p>
        <span>© 2026 VitaSense AI · Research demonstration</span>
      </footer>
    </main>
  );
}
