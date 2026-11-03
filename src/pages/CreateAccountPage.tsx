import React, { useState } from 'react';
import { Logo } from '../components/Logo';
import { Icon } from '../components/Icons';
import { SocialAuthModal } from '../components/SocialAuthModal';
import { UserProfile, saveUserProfile, setAuthToken } from '../types';
import { apiEndpoint } from '../api';

interface CreateAccountPageProps {
  go: (page: string) => void;
  theme: 'dark' | 'light';
  setTheme: (theme: 'dark' | 'light') => void;
  onAccountCreated: (profile: UserProfile) => void;
}

export function CreateAccountPage({
  go,
  theme,
  setTheme,
  onAccountCreated,
}: CreateAccountPageProps) {
  // Focus field tracking for dynamic mascot animation
  const [focusField, setFocusField] = useState<
    | 'name'
    | 'email'
    | 'password'
    | 'age'
    | 'sex'
    | 'height'
    | 'weight'
    | 'restingHr'
    | 'activityLevel'
    | 'healthGoal'
    | null
  >(null);

  // Form state
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Baseline health details
  const [age, setAge] = useState<number>(29);
  const [sex, setSex] = useState<UserProfile['sex']>('Male');
  const [height, setHeight] = useState('178 cm');
  const [weight, setWeight] = useState('72 kg');
  const [restingHr, setRestingHr] = useState<number>(64);
  const [activityLevel, setActivityLevel] = useState<UserProfile['activityLevel']>('Moderately Active');
  const [healthGoal, setHealthGoal] = useState<UserProfile['healthGoal']>('Cardiovascular Wellness');

  // Social Auth Modal state
  const [socialProvider, setSocialProvider] = useState<'google' | 'apple' | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleQuickDemoFill = () => {
    setName('Demo User');
    setEmail('demo.user@example.com');
    setPassword('DemoPass123!');
    setAge(29);
    setSex('Other');
    setHeight('175 cm');
    setWeight('70 kg');
    setRestingHr(65);
    setActivityLevel('Moderately Active');
    setHealthGoal('Cardiovascular Wellness');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    const regName = name.trim();
    const regEmail = email.trim();
    const regPass = password;

    if (!regName || !regEmail || !regPass) {
      setErrorMsg('Please enter your full name, email address, and password.');
      return;
    }

    if (regPass.length < 6) {
      setErrorMsg('Password must be at least 6 characters.');
      return;
    }

    setIsSubmitting(true);

    const newProfile: UserProfile = {
      name: regName,
      email: regEmail,
      age: Number(age) || 29,
      sex,
      height: height.trim() || '175 cm',
      weight: weight.trim() || '70 kg',
      restingHr: Number(restingHr) || 65,
      activityLevel,
      healthGoal,
      provider: 'email',
    };

    try {
      const res = await fetch(apiEndpoint('/api/auth/register'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: newProfile.email,
          password: regPass,
          name: newProfile.name,
          age: newProfile.age,
          sex: newProfile.sex,
          height: newProfile.height,
          weight: newProfile.weight,
          resting_hr: newProfile.restingHr,
          activity_level: newProfile.activityLevel,
          health_goal: newProfile.healthGoal,
          provider: 'email',
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setAuthToken(data.token);
        saveUserProfile(newProfile);
        onAccountCreated(newProfile);
        go('overview');
        return;
      }

      const err = await res.json().catch(() => ({}));
      setErrorMsg(err.detail || 'Registration encountered an issue. Please verify fields or sign in.');
    } catch {
      setErrorMsg('Network error: Unable to connect to registration server. Please check your connection and retry.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getMascotThought = () => {
    switch (focusField) {
      case 'name':
        return 'Excited to meet you! What should we call you? 👋';
      case 'email':
        return 'Your telemetry stays strictly confidential 🔒';
      case 'password':
        return 'No peeking! Covering my eyes while you type 🙈';
      case 'age':
        return 'Age tunes our heart rate reserve & threshold zones 📈';
      case 'sex':
        return 'Calibrates standard physiological baselines 🧬';
      case 'height':
      case 'weight':
        return 'Biometrics help calculate accurate motion & energy 🏃';
      case 'restingHr':
        return 'Resting HR calibrates our real-time anomaly detector ❤️';
      case 'activityLevel':
        return 'Customizes baseline activity filtering & motion masks ⚡';
      case 'healthGoal':
        return 'Fantastic target! We will align insights to this goal 🎯';
      default:
        return 'Ready to calibrate your research health profile! ✨';
    }
  };

  return (
    <main
      className={`login-page create-account-page focus-${focusField ?? 'none'} ${
        password ? 'has-password' : ''
      }`}
    >
      {/* Site Header */}
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
      <section className="login-art create-art">
        <div className="login-grid" />
        <div className="login-art-copy">
          <span className="kicker">PERSONALIZED CALIBRATION</span>
          <h1>
            Build your profile.
            <br />
            <em>Calibrate your baseline.</em>
          </h1>
          <p>
            Provide baseline health metrics to calibrate real-time trust scoring
            and personalized anomaly detection.
          </p>
        </div>

        {/* Mascot Stage */}
        <div className="mascot-stage" aria-hidden="true">
          {/* Mascot Thought Bubble reacting to active field */}
          <div className="mascot-speech-bubble">
            <span className="bubble-dot" />
            <p>{getMascotThought()}</p>
          </div>

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
            <b>Zero Clinical Leakage.</b> Your health metrics stay encrypted on your device.
          </span>
        </div>
      </section>

      {/* Account & Health Details Form Panel */}
      <section className="login-panel create-panel">
        <div className="login-form-wrap create-form-wrap">
          <span className="login-step">NEW PROFILE REGISTRATION · 01</span>
          <h2>Create account.</h2>
          <p>Fill in your basic credentials and physiological baseline.</p>

          {errorMsg && (
            <div
              className="registration-error-banner"
              style={{
                backgroundColor: 'rgba(239, 68, 68, 0.12)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                color: '#ef4444',
                padding: '10px 14px',
                borderRadius: '8px',
                marginBottom: '16px',
                fontSize: '13px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <Icon name="shield" size={16} />
              <span>{errorMsg}</span>
            </div>
          )}

          <div style={{ marginBottom: '14px' }}>
            <button
              type="button"
              onClick={handleQuickDemoFill}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                padding: '9px 14px',
                background: 'rgba(59, 130, 246, 0.08)',
                border: '1px solid rgba(59, 130, 246, 0.3)',
                color: '#3b82f6',
                fontWeight: 600,
                fontSize: '12.5px',
                borderRadius: '8px',
                cursor: 'pointer',
              }}
            >
              <Icon name="sparkles" size={15} />
              <span>Auto-Fill Demo Baseline Biometrics</span>
            </button>
          </div>

          {/* Functional Social Login Buttons */}
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

          <div className="login-divider">
            <span>or sign up with email</span>
          </div>

          {errorMsg && (
            <div
              className="registration-error-banner"
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
                <span style={{ flex: 1 }}>{errorMsg}</span>
              </div>
              <button
                type="button"
                onClick={() => { setErrorMsg(null); }}
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

          <form onSubmit={handleSubmit}>
            {/* Step 1: Account Credentials */}
            <div className="form-subheading">
              <Icon name="user" size={14} />
              <span>Personal Credentials</span>
            </div>

            <label className={focusField === 'name' ? 'field-active' : ''}>
              <span>Full Name</span>
              <div className="input-shell">
                <Icon name="user" />
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  onFocus={() => setFocusField('name')}
                  onBlur={() => setFocusField(null)}
                  placeholder="e.g. Jane Doe"
                  required
                />
              </div>
            </label>

            <label className={focusField === 'email' ? 'field-active' : ''}>
              <span>Email Address</span>
              <div className="input-shell">
                <Icon name="shield" />
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
              <span>Password</span>
              <div className="input-shell">
                <Icon name="shield" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onFocus={() => setFocusField('password')}
                  onBlur={() => setFocusField(null)}
                  placeholder="Choose a secure password"
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

            {/* Step 2: Health & Physiological Baseline */}
            <div className="form-subheading health-subheading">
              <Icon name="activity" size={14} />
              <span>Baseline Health Details</span>
            </div>

            <div className="form-row-2">
              <label className={focusField === 'age' ? 'field-active' : ''}>
                <span>Age (years)</span>
                <div className="input-shell">
                  <input
                    type="number"
                    min="1"
                    max="120"
                    value={age}
                    onChange={(e) => setAge(Number(e.target.value) || 0)}
                    onFocus={() => setFocusField('age')}
                    onBlur={() => setFocusField(null)}
                    required
                  />
                </div>
              </label>

              <label className={focusField === 'sex' ? 'field-active' : ''}>
                <span>Biological Sex</span>
                <div className="input-shell select-shell">
                  <select
                    value={sex}
                    onChange={(e) => setSex(e.target.value as UserProfile['sex'])}
                    onFocus={() => setFocusField('sex')}
                    onBlur={() => setFocusField(null)}
                  >
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                    <option value="Prefer not to say">Prefer not to say</option>
                  </select>
                </div>
              </label>
            </div>

            <div className="form-row-2">
              <label className={focusField === 'height' ? 'field-active' : ''}>
                <span>Height</span>
                <div className="input-shell">
                  <input
                    type="text"
                    value={height}
                    onChange={(e) => setHeight(e.target.value)}
                    onFocus={() => setFocusField('height')}
                    onBlur={() => setFocusField(null)}
                    placeholder="178 cm"
                    required
                  />
                </div>
              </label>

              <label className={focusField === 'weight' ? 'field-active' : ''}>
                <span>Weight</span>
                <div className="input-shell">
                  <input
                    type="text"
                    value={weight}
                    onChange={(e) => setWeight(e.target.value)}
                    onFocus={() => setFocusField('weight')}
                    onBlur={() => setFocusField(null)}
                    placeholder="72 kg"
                    required
                  />
                </div>
              </label>
            </div>

            <div className="form-row-2">
              <label className={focusField === 'restingHr' ? 'field-active' : ''}>
                <span>Resting HR (bpm)</span>
                <div className="input-shell">
                  <input
                    type="number"
                    min="35"
                    max="200"
                    value={restingHr}
                    onChange={(e) => setRestingHr(Number(e.target.value) || 0)}
                    onFocus={() => setFocusField('restingHr')}
                    onBlur={() => setFocusField(null)}
                    required
                  />
                </div>
              </label>

              <label className={focusField === 'activityLevel' ? 'field-active' : ''}>
                <span>Activity Level</span>
                <div className="input-shell select-shell">
                  <select
                    value={activityLevel}
                    onChange={(e) =>
                      setActivityLevel(e.target.value as UserProfile['activityLevel'])
                    }
                    onFocus={() => setFocusField('activityLevel')}
                    onBlur={() => setFocusField(null)}
                  >
                    <option value="Sedentary">Sedentary</option>
                    <option value="Lightly Active">Lightly Active</option>
                    <option value="Moderately Active">Moderately Active</option>
                    <option value="Very Active">Very Active</option>
                  </select>
                </div>
              </label>
            </div>

            <label className={focusField === 'healthGoal' ? 'field-active' : ''}>
              <span>Primary Health & Wellness Goal</span>
              <div className="input-shell select-shell">
                <select
                  value={healthGoal}
                  onChange={(e) =>
                    setHealthGoal(e.target.value as UserProfile['healthGoal'])
                  }
                  onFocus={() => setFocusField('healthGoal')}
                  onBlur={() => setFocusField(null)}
                >
                  <option value="Cardiovascular Wellness">Cardiovascular Wellness</option>
                  <option value="Athletic Performance">Athletic Performance</option>
                  <option value="Stress & Recovery">Stress & Recovery</option>
                  <option value="Sleep Optimization">Sleep Optimization</option>
                </select>
              </div>
            </label>

            <button className="login-submit" type="submit">
              Complete Profile & Enter VitaSense <Icon name="arrow" />
            </button>
          </form>

          <p className="signup-copy">
            Already have an account?{' '}
            <button type="button" onClick={() => go('login')}>
              Sign in
            </button>
          </p>
        </div>
      </section>

      {/* Social Auth Modal */}
      <SocialAuthModal
        provider={socialProvider}
        onClose={() => setSocialProvider(null)}
        onSuccess={(profile) => {
          setSocialProvider(null);
          onAccountCreated(profile);
          go('overview');
        }}
      />
    </main>
  );
}
