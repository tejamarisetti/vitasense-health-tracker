import React, { useState } from 'react';
import { Logo } from '../components/Logo';
import { Icon } from '../components/Icons';
import { SocialAuthModal } from '../components/SocialAuthModal';
import { UserProfile, saveUserProfile, setAuthToken } from '../types';
import { apiEndpoint } from '../api';

interface LoginPageProps {
  go: (page: string) => void;
  theme: 'dark' | 'light';
  setTheme: (theme: 'dark' | 'light') => void;
  onLoginSuccess?: (profile: UserProfile) => void;
}

export function LoginPage({ go, theme, setTheme, onLoginSuccess }: LoginPageProps) {
  const [focusField, setFocusField] = useState<'email' | 'password' | null>(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [socialProvider, setSocialProvider] = useState<'google' | 'apple' | null>(null);
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotSent, setForgotSent] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleQuickDemoLogin = async () => {
    setAuthError(null);
    setIsLoading(true);
    try {
      const res = await fetch(apiEndpoint('/api/auth/demo'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (res.ok) {
        const data = await res.json();
        setAuthToken(data.token);
        const p: UserProfile = {
          name: data.profile.name || 'DEMO',
          email: data.user.email,
          age: data.profile.age || 29,
          sex: data.profile.sex || 'Other',
          height: data.profile.height || '175 cm',
          weight: data.profile.weight || '70 kg',
          restingHr: data.profile.resting_hr || 65,
          activityLevel: data.profile.activity_level || 'Moderately Active',
          healthGoal: data.profile.health_goal || 'Cardiovascular Wellness',
          provider: data.profile.provider || 'email',
        };
        saveUserProfile(p);
        if (onLoginSuccess) onLoginSuccess(p);
        go('overview');
        return;
      }
      const errData = await res.json().catch(() => ({}));
      setAuthError(errData.detail || 'Demo authentication failed on server. Please retry.');
    } catch {
      setAuthError('Network error: Unable to connect to authentication server. Please check your connection and retry.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);

    const loginEmail = email.trim();
    const loginPass = password;

    if (!loginEmail || !loginPass) {
      setAuthError('Please enter both email and password.');
      return;
    }

    setIsLoading(true);

    try {
      const res = await fetch(apiEndpoint('/api/auth/login'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: loginEmail, password: loginPass }),
      });

      if (res.ok) {
        const data = await res.json();
        setAuthToken(data.token);
        const p: UserProfile = {
          name: data.profile.name || loginEmail.split('@')[0],
          email: data.user.email,
          age: data.profile.age || 29,
          sex: data.profile.sex || 'Male',
          height: data.profile.height || '178 cm',
          weight: data.profile.weight || '72 kg',
          restingHr: data.profile.resting_hr || 64,
          activityLevel: data.profile.activity_level || 'Moderately Active',
          healthGoal: data.profile.health_goal || 'Cardiovascular Wellness',
          provider: data.profile.provider || 'email',
        };
        saveUserProfile(p);
        if (onLoginSuccess) onLoginSuccess(p);
        go('overview');
        return;
      }

      const errData = await res.json().catch(() => ({}));
      setAuthError(errData.detail || 'Authentication failed. Please verify your credentials.');
    } catch {
      setAuthError('Network error: Unable to connect to authentication server. Please check your connection and retry.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main
      className={`login-page focus-${focusField ?? 'none'} ${
        password ? 'has-password' : ''
      }`}
    >
      <header className="login-header">
        <button
          className="login-logo"
          onClick={() => go('landing')}
          aria-label="Back to VitaSense home"
          type="button"
        >
          <Logo />
        </button>

        <button
          className="icon-button"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          aria-label="Toggle theme"
          type="button"
        >
          <Icon name={theme === 'dark' ? 'sun' : 'moon'} />
        </button>
      </header>

      {/* Interactive Mascot Art Section */}
      <section className="login-art">
        <div className="login-grid" />
        <div className="login-art-copy">
          <span className="kicker">WELCOME TO VITASENSE</span>
          <h1>
            Your health story
            <br />
            starts with <em>one signal.</em>
          </h1>
          <p>
            Private, explainable, and designed to help you understand every
            measurement.
          </p>
        </div>

        <div className="mascot-stage" aria-hidden="true">
          {/* Mascot Tall */}
          <div className="mascot mascot-tall">
            <div className="mascot-antenna">
              <i />
            </div>
            <div className="mascot-face">
              <span className="mascot-eye eye-left">
                <i />
              </span>
              <span className="mascot-eye eye-right">
                <i />
              </span>
              <span className="mascot-mouth" />
            </div>
            <span className="mascot-arm arm-left" />
            <span className="mascot-arm arm-right" />
            <span className="mascot-hand hand-left">
              <i />
              <i />
              <i />
            </span>
            <span className="mascot-hand hand-right">
              <i />
              <i />
              <i />
            </span>
            <div className="mascot-glow" />
          </div>

          {/* Mascot Round */}
          <div className="mascot mascot-round">
            <div className="mascot-face">
              <span className="mascot-eye eye-left">
                <i />
              </span>
              <span className="mascot-eye eye-right">
                <i />
              </span>
              <span className="mascot-mouth" />
            </div>
            <span className="mascot-arm arm-left" />
            <span className="mascot-arm arm-right" />
            <span className="mascot-hand hand-left">
              <i />
              <i />
              <i />
            </span>
            <span className="mascot-hand hand-right">
              <i />
              <i />
              <i />
            </span>
          </div>

          <div className="mascot-orbit orbit-one">
            <i />
          </div>
          <div className="mascot-orbit orbit-two">
            <i />
          </div>

          <span className="floating-symbol symbol-pulse">
            <Icon name="pulse" />
          </span>
          <span className="floating-symbol symbol-ai">
            <Icon name="sparkles" />
          </span>
          <span className="floating-symbol symbol-shield">
            <Icon name="shield" />
          </span>
          <div className="mascot-shadow" />
        </div>

        <div className="login-safety">
          <Icon name="shield" />
          <span>
            <b>Your data stays yours.</b> Protected with privacy-first
            architecture.
          </span>
        </div>
      </section>

      {/* Login Form Panel */}
      <section className="login-panel">
        <div className="login-form-wrap">
          <span className="login-step">SECURE ACCESS · 01</span>
          <h2>Welcome back.</h2>
          <p>Enter your details to continue to your health workspace.</p>

          {authError && (
            <div
              className="login-error-banner"
              style={{
                backgroundColor: 'rgba(239, 68, 68, 0.12)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                color: '#ef4444',
                padding: '12px 14px',
                borderRadius: '8px',
                marginBottom: '16px',
                fontSize: '13px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Icon name="shield" size={16} />
                <span style={{ flex: 1 }}>{authError}</span>
              </div>
              <button
                type="button"
                onClick={() => { setAuthError(null); }}
                style={{
                  alignSelf: 'flex-start',
                  background: 'rgba(239, 68, 68, 0.2)',
                  border: '1px solid #ef4444',
                  color: '#ef4444',
                  borderRadius: '6px',
                  padding: '4px 10px',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Retry
              </button>
            </div>
          )}

          <div style={{ marginBottom: '14px' }}>
            <button
              type="button"
              id="quick-demo-login-btn"
              onClick={handleQuickDemoLogin}
              disabled={isLoading}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                padding: '11px 16px',
                background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(6, 95, 70, 0.25))',
                border: '1px solid rgba(16, 185, 129, 0.4)',
                color: '#10b981',
                fontWeight: 600,
                fontSize: '13.5px',
                borderRadius: '8px',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
            >
              <Icon name="sparkles" size={16} />
              <span>{isLoading ? 'Connecting...' : 'Instant Demo Access (DEMO)'}</span>
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            <label className={focusField === 'email' ? 'field-active' : ''}>
              <span>Email address</span>
              <div className="input-shell">
                <Icon name="user" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onFocus={() => setFocusField('email')}
                  onBlur={() => setFocusField(null)}
                  placeholder="user@example.com"
                  required
                />
              </div>
            </label>

            <label className={focusField === 'password' ? 'field-active' : ''}>
              <span>
                Password{' '}
                <button
                  type="button"
                  onClick={() => {
                    setForgotEmail(email || '');
                    setShowForgotModal(true);
                  }}
                  title="Password reset is not enabled in this deployment"
                >
                  Forgot password? <small style={{ color: 'var(--faint)' }}>(Not Enabled)</small>
                </button>
              </span>
              <div className="input-shell">
                <Icon name="shield" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onFocus={() => setFocusField('password')}
                  onBlur={() => setFocusField(null)}
                  placeholder="Enter your password"
                  required
                />
                <button
                  type="button"
                  className="show-password"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? 'Hide' : 'Show'}
                </button>
              </div>
            </label>

            <label className="remember">
              <input type="checkbox" />
              <i /> Keep me signed in on this device
            </label>

            <button className="login-submit" type="submit" disabled={isLoading}>
              {isLoading ? 'Verifying...' : 'Enter VitaSense'} <Icon name="arrow" />
            </button>
          </form>

          <div className="login-divider">
            <span>or continue with</span>
          </div>

          <div className="social-login">
            <button
              type="button"
              className="social-btn google-btn disabled"
              disabled
              title="Google authentication is not available in this build"
              style={{ opacity: 0.6, cursor: 'not-allowed', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}
            >
              <Icon name="google" size={17} />
              <span>Google <small style={{ fontSize: '9px', opacity: 0.8 }}>(Not available)</small></span>
            </button>
            <button
              type="button"
              className="social-btn apple-btn disabled"
              disabled
              title="Apple authentication is not available in this build"
              style={{ opacity: 0.6, cursor: 'not-allowed', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}
            >
              <Icon name="apple" size={17} />
              <span>Apple <small style={{ fontSize: '9px', opacity: 0.8 }}>(Not available)</small></span>
            </button>
          </div>

          <p className="signup-copy">
            New to VitaSense?{' '}
            <button type="button" onClick={() => go('create-account')}>
              Create an account
            </button>
          </p>

          <div className="login-demo">
            <span>
              <Icon name="sparkles" />
            </span>
            <p>
              <b>Exploring the concept?</b>
              Any details or social sign-in will calibrate your research profile.
            </p>
          </div>
        </div>
      </section>

      {/* Social Auth Modal */}
      <SocialAuthModal
        provider={socialProvider}
        onClose={() => setSocialProvider(null)}
        onSuccess={(profile) => {
          setSocialProvider(null);
          if (onLoginSuccess) {
            onLoginSuccess(profile);
          }
          go('overview');
        }}
      />

      {/* Forgot Password Modal (Marked Not Enabled per PRD) */}
      {showForgotModal && (
        <div className="forgot-dialog-backdrop" onClick={() => setShowForgotModal(false)}>
          <div className="forgot-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="forgot-dialog-header">
              <div>
                <span className="app-kicker">ACCOUNT SECURITY</span>
                <h3>Password Reset</h3>
                <p>Self-service recovery status</p>
              </div>
              <button
                className="forgot-dialog-close"
                onClick={() => setShowForgotModal(false)}
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            <div style={{ textAlign: 'center', padding: '16px 0' }}>
              <div style={{ fontSize: '32px', marginBottom: '12px' }}>🔒</div>
              <h4 style={{ fontSize: '15px', marginBottom: '6px' }}>Password Reset Not Enabled</h4>
              <p style={{ color: 'var(--muted)', fontSize: '13px', marginBottom: '20px', lineHeight: 1.6 }}>
                Password reset is not enabled in this build.
              </p>
              <button
                type="button"
                className="button button-soft"
                style={{ width: '100%' }}
                onClick={() => setShowForgotModal(false)}
              >
                Return to Sign In
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
