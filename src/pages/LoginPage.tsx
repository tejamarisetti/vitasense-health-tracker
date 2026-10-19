import React, { useState } from 'react';
import { Logo } from '../components/Logo';
import { Icon } from '../components/Icons';
import { SocialAuthModal } from '../components/SocialAuthModal';
import { UserProfile, saveUserProfile } from '../types';

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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const updatedProfile: UserProfile = {
      name: email.split('@')[0] || 'Alex Morgan',
      email: email || 'alex@example.com',
      age: 29,
      sex: 'Male',
      height: '178 cm',
      weight: '72 kg',
      restingHr: 64,
      activityLevel: 'Moderately Active',
      healthGoal: 'Cardiovascular Wellness',
      provider: 'email',
    };
    saveUserProfile(updatedProfile);
    if (onLoginSuccess) {
      onLoginSuccess(updatedProfile);
    }
    go('overview');
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
                  placeholder="alex@example.com"
                  required
                />
              </div>
            </label>

            <label className={focusField === 'password' ? 'field-active' : ''}>
              <span>
                Password{' '}
                <button type="button">Forgot password?</button>
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
              <input type="checkbox" defaultChecked />
              <i /> Keep me signed in on this device
            </label>

            <button className="login-submit" type="submit">
              Enter VitaSense <Icon name="arrow" />
            </button>
          </form>

          <div className="login-divider">
            <span>or continue with</span>
          </div>

          <div className="social-login">
            <button
              type="button"
              className="social-btn google-btn"
              onClick={() => setSocialProvider('google')}
            >
              <Icon name="google" size={17} />
              <span>Google</span>
            </button>
            <button
              type="button"
              className="social-btn apple-btn"
              onClick={() => setSocialProvider('apple')}
            >
              <Icon name="apple" size={17} />
              <span>Apple</span>
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
    </main>
  );
}
