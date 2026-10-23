import React, { useState, useEffect } from 'react';
import { Icon } from '../components/Icons';
import { getAuthToken } from '../types';

interface AssessmentPageProps {
  go?: (page: string) => void;
}

interface AssessmentAnswers {
  primary_symptom: string;
  intensity: 'mild' | 'moderate' | 'severe';
  duration: string;
  activity_context: string;
  warning_signs: string[];
  notes: string;
  is_demo: boolean;
}

interface AssessmentResult {
  id: number;
  user_id: number;
  risk_level: 'Low Risk Signal' | 'Moderate Risk Signal' | 'Elevated Risk Signal';
  risk_score: number;
  contributing_factors: string[];
  feature_contributions: Record<string, number>;
  uncertainty_range?: [number, number] | null;
  uncertainty_note?: string;
  model_version: string;
  is_demo: boolean;
  missing_data_notes: string[];
  model_limitations: string;
  when_to_seek_care: string;
  disclaimer: string;
  created_at: string;
}

export function AssessmentPage({ go }: AssessmentPageProps) {
  const [step, setStep] = useState<'form' | 'review' | 'result'>('form');
  const [answers, setAnswers] = useState<AssessmentAnswers>({
    primary_symptom: 'racing_heart',
    intensity: 'moderate',
    duration: '15_to_30m',
    activity_context: 'resting',
    warning_signs: [],
    notes: '',
    is_demo: false,
  });

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AssessmentResult | null>(null);
  const [history, setHistory] = useState<AssessmentResult[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const primarySymptoms = [
    { id: 'racing_heart', label: 'Racing Heart (Tachycardia)', desc: 'Rapid, pounding heartbeats' },
    { id: 'palpitations', label: 'Palpitations', desc: 'Fluttering or thumping sensation in chest' },
    { id: 'skipped_beats', label: 'Skipped Beats', desc: 'Sensation of pauses or missed heartbeats' },
    { id: 'chest_tightness', label: 'Chest Discomfort / Tightness', desc: 'Sensation of pressure or constriction' },
    { id: 'dizziness', label: 'Dizziness / Lightheadedness', desc: 'Feeling unsteady or faint' },
    { id: 'shortness_of_breath', label: 'Shortness of Breath', desc: 'Labored breathing or feeling winded' },
    { id: 'fatigue', label: 'Sudden Fatigue', desc: 'Unusual, unexpected exhaustion' },
    { id: 'none_routine', label: 'Routine Check (No Symptoms)', desc: 'Regular wellness screening' },
  ];

  const contexts = [
    { id: 'resting', label: 'Resting / Lying Down' },
    { id: 'sitting_desk', label: 'Sitting / Sedentary Work' },
    { id: 'light_activity', label: 'Light Walking / Chores' },
    { id: 'vigorous_exercise', label: 'Vigorous Exercise / Workout' },
    { id: 'emotional_stress', label: 'Emotionally Stressed / Anxious' },
    { id: 'caffeine_stimulants', label: 'Post-Caffeine / Energy Drink' },
  ];

  const durations = [
    { id: 'under_5m', label: '< 5 Minutes' },
    { id: '5_to_15m', label: '5 - 15 Minutes' },
    { id: '15_to_30m', label: '15 - 30 Minutes' },
    { id: 'over_30m', label: '> 30 Minutes' },
    { id: 'continuous', label: 'Continuous / Ongoing' },
  ];

  const warningOptions = [
    { id: 'radiating_pain', label: 'Chest pressure radiating to left arm, neck, or jaw' },
    { id: 'acute_breathlessness', label: 'Sudden acute breathlessness while resting' },
    { id: 'syncope', label: 'Loss of consciousness, near-fainting, or blacking out' },
  ];

  const fetchHistory = async () => {
    const token = getAuthToken();
    if (!token) return;
    try {
      const res = await fetch('/api/assessment/history', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setHistory(data);
      }
    } catch {
      // Ignore network errors on initial fetch
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleToggleWarning = (signId: string) => {
    setAnswers((prev) => {
      const exists = prev.warning_signs.includes(signId);
      const nextSigns = exists
        ? prev.warning_signs.filter((s) => s !== signId)
        : [...prev.warning_signs, signId];
      return { ...prev, warning_signs: nextSigns };
    });
  };

  const loadDemoScenario = () => {
    setAnswers({
      primary_symptom: 'chest_tightness',
      intensity: 'severe',
      duration: 'over_30m',
      activity_context: 'resting',
      warning_signs: ['radiating_pain'],
      notes: 'Demonstration scenario: persistent tight sensation during quiet rest.',
      is_demo: true,
    });
    setErrorMessage(null);
  };

  const handleGoToReview = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setStep('review');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSubmitAssessment = async () => {
    setLoading(true);
    setErrorMessage(null);
    const token = getAuthToken();

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const res = await fetch('/api/assessment/submit', {
        method: 'POST',
        headers,
        body: JSON.stringify(answers),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Failed to evaluate assessment' }));
        throw new Error(err.detail || 'Server assessment error');
      }

      const data: AssessmentResult = await res.json();
      setResult(data);
      setStep('result');
      fetchHistory();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (err: any) {
      setErrorMessage(err.message || 'Unable to submit assessment. Please check backend connection.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="assessment-page" style={{ padding: '24px 32px', maxWidth: '1100px', margin: '0 auto' }}>
      {/* Page Header */}
      <div style={{ marginBottom: '28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <span style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.08em', color: 'var(--brand-mint)', textTransform: 'uppercase' }}>
              PRD FR-06 & FR-07 MODULE
            </span>
            <h1 style={{ fontSize: '28px', fontWeight: 800, margin: '4px 0 6px', color: 'var(--text-primary)' }}>
              Symptom-Based Risk Screening Lab
            </h1>
            <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '14px', maxWidth: '700px' }}>
              Guided symptom questionnaire with mandatory answer review, rule-based screening risk categorization,
              and transparent AI/ML feature attribution (uncertainty not estimated for this demo ruleset).
            </p>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              type="button"
              className="btn-secondary"
              onClick={loadDemoScenario}
              style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '9px 16px', borderRadius: '8px', fontSize: '13px', cursor: 'pointer' }}
            >
              <Icon name="sparkles" /> Load Demo Scenario
            </button>
            {go && (
              <button
                type="button"
                className="btn-outline"
                onClick={() => go('overview')}
                style={{ padding: '9px 16px', borderRadius: '8px', fontSize: '13px', cursor: 'pointer' }}
              >
                Back to Overview
              </button>
            )}
          </div>
        </div>

        {/* Step Indicator */}
        <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
          {[
            { key: 'form', label: '1. Guided Questionnaire' },
            { key: 'review', label: '2. Review & Edit Answers (FR-06)' },
            { key: 'result', label: '3. Screening & AI Explanation (FR-07)' },
          ].map((s) => {
            const isActive = step === s.key;
            return (
              <div
                key={s.key}
                style={{
                  flex: 1,
                  padding: '10px 14px',
                  borderRadius: '8px',
                  background: isActive ? 'rgba(78, 222, 128, 0.12)' : 'var(--surface-subtle)',
                  border: isActive ? '1px solid var(--brand-mint)' : '1px solid var(--border-color)',
                  color: isActive ? 'var(--brand-mint)' : 'var(--text-muted)',
                  fontSize: '13px',
                  fontWeight: isActive ? 700 : 500,
                  textAlign: 'center',
                }}
              >
                {s.label}
              </div>
            );
          })}
        </div>
      </div>

      {errorMessage && (
        <div style={{ background: 'rgba(239, 68, 68, 0.12)', border: '1px solid #ef4444', borderRadius: '8px', padding: '14px 18px', marginBottom: '20px', color: '#fca5a5', fontSize: '14px' }}>
          <strong>Error:</strong> {errorMessage}
        </div>
      )}

      {/* STEP 1: FORM */}
      {step === 'form' && (
        <form onSubmit={handleGoToReview} style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Question 1: Primary Symptom */}
          <div className="app-panel" style={{ padding: '20px', borderRadius: '12px', background: 'var(--surface-card)', border: '1px solid var(--border-color)' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '0 0 4px', color: 'var(--text-primary)' }}>
              1. What primary sensation or symptom are you experiencing?
            </h3>
            <p style={{ margin: '0 0 16px', color: 'var(--text-muted)', fontSize: '13px' }}>
              Select the chief subjective sensation that best reflects your current cardiac or pulmonary state.
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '10px' }}>
              {primarySymptoms.map((sym) => {
                const selected = answers.primary_symptom === sym.id;
                return (
                  <button
                    key={sym.id}
                    type="button"
                    onClick={() => setAnswers({ ...answers, primary_symptom: sym.id })}
                    style={{
                      textAlign: 'left',
                      padding: '12px 14px',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      background: selected ? 'rgba(56, 189, 248, 0.12)' : 'var(--surface-card)',
                      border: selected ? '1.5px solid #38bdf8' : '1px solid var(--border-color)',
                      color: 'var(--text-primary)',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div style={{ fontWeight: 600, fontSize: '13px', color: selected ? '#38bdf8' : 'var(--text-primary)' }}>
                      {sym.label}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                      {sym.desc}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Question 2: Intensity & Duration */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
            <div className="app-panel" style={{ padding: '20px', borderRadius: '12px', background: 'var(--surface-card)', border: '1px solid var(--border-color)' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '0 0 4px', color: 'var(--text-primary)' }}>
                2. Subjective Sensation Intensity
              </h3>
              <p style={{ margin: '0 0 14px', color: 'var(--text-muted)', fontSize: '13px' }}>
                How intense is the discomfort or sensation?
              </p>
              <div style={{ display: 'flex', gap: '8px' }}>
                {(['mild', 'moderate', 'severe'] as const).map((lvl) => {
                  const selected = answers.intensity === lvl;
                  return (
                    <button
                      key={lvl}
                      type="button"
                      onClick={() => setAnswers({ ...answers, intensity: lvl })}
                      style={{
                        flex: 1,
                        padding: '12px',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        textTransform: 'capitalize',
                        fontWeight: 600,
                        fontSize: '13px',
                        background: selected
                          ? lvl === 'severe'
                            ? 'rgba(239, 68, 68, 0.2)'
                            : lvl === 'moderate'
                            ? 'rgba(245, 158, 11, 0.2)'
                            : 'rgba(56, 189, 248, 0.2)'
                          : 'var(--surface-card)',
                        border: selected
                          ? `1.5px solid ${lvl === 'severe' ? '#ef4444' : lvl === 'moderate' ? '#f59e0b' : '#38bdf8'}`
                          : '1px solid var(--border-color)',
                        color: selected ? 'var(--text-primary)' : 'var(--text-muted)',
                      }}
                    >
                      {lvl}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="app-panel" style={{ padding: '20px', borderRadius: '12px', background: 'var(--surface-card)', border: '1px solid var(--border-color)' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '0 0 4px', color: 'var(--text-primary)' }}>
                3. Episode Duration
              </h3>
              <p style={{ margin: '0 0 14px', color: 'var(--text-muted)', fontSize: '13px' }}>
                How long has this sensation lasted?
              </p>
              <select
                value={answers.duration}
                onChange={(e) => setAnswers({ ...answers, duration: e.target.value })}
                style={{
                  width: '100%',
                  padding: '11px 14px',
                  borderRadius: '8px',
                  background: 'var(--surface-card)',
                  border: '1px solid var(--border-color)',
                  color: 'var(--text-primary)',
                  fontSize: '14px',
                  cursor: 'pointer',
                }}
              >
                {durations.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Question 4: Activity Context */}
          <div className="app-panel" style={{ padding: '20px', borderRadius: '12px', background: 'var(--surface-card)', border: '1px solid var(--border-color)' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '0 0 4px', color: 'var(--text-primary)' }}>
              4. Activity and Behavioral Context
            </h3>
            <p style={{ margin: '0 0 14px', color: 'var(--text-muted)', fontSize: '13px' }}>
              What were you doing when you noticed the sensation? Symptoms occurring at quiet rest are evaluated differently than exertional symptoms.
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '10px' }}>
              {contexts.map((c) => {
                const selected = answers.activity_context === c.id;
                return (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => setAnswers({ ...answers, activity_context: c.id })}
                    style={{
                      textAlign: 'left',
                      padding: '12px 14px',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      background: selected ? 'rgba(168, 85, 247, 0.12)' : 'var(--surface-card)',
                      border: selected ? '1.5px solid #a855f7' : '1px solid var(--border-color)',
                      color: selected ? '#c084fc' : 'var(--text-primary)',
                      fontSize: '13px',
                      fontWeight: selected ? 600 : 500,
                    }}
                  >
                    {c.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Question 5: Warning Signs */}
          <div className="app-panel" style={{ padding: '20px', borderRadius: '12px', background: 'var(--surface-card)', border: '1px solid var(--border-color)' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '0 0 4px', color: 'var(--text-primary)' }}>
              5. Acute Red Flag Warning Signs
            </h3>
            <p style={{ margin: '0 0 14px', color: 'var(--text-muted)', fontSize: '13px' }}>
              Check any signs that apply. These indicators directly influence emergency advisory logic.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {warningOptions.map((opt) => {
                const isChecked = answers.warning_signs.includes(opt.id);
                return (
                  <label
                    key={opt.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px',
                      padding: '12px 14px',
                      borderRadius: '8px',
                      background: isChecked ? 'rgba(239, 68, 68, 0.10)' : 'var(--surface-card)',
                      border: isChecked ? '1px solid #ef4444' : '1px solid var(--border-color)',
                      cursor: 'pointer',
                      fontSize: '13px',
                      color: isChecked ? '#fca5a5' : 'var(--text-primary)',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => handleToggleWarning(opt.id)}
                      style={{ width: '16px', height: '16px', accentColor: '#ef4444' }}
                    />
                    <span>{opt.label}</span>
                  </label>
                );
              })}
            </div>
          </div>

          {/* Notes */}
          <div className="app-panel" style={{ padding: '20px', borderRadius: '12px', background: 'var(--surface-card)', border: '1px solid var(--border-color)' }}>
            <h3 style={{ fontSize: '15px', fontWeight: 700, margin: '0 0 4px', color: 'var(--text-primary)' }}>
              Optional Context Notes
            </h3>
            <textarea
              rows={2}
              value={answers.notes}
              onChange={(e) => setAnswers({ ...answers, notes: e.target.value })}
              placeholder="e.g. Just drank double espresso, or feeling recovering from flu..."
              style={{
                width: '100%',
                padding: '10px 12px',
                borderRadius: '8px',
                background: 'var(--surface-card)',
                border: '1px solid var(--border-color)',
                color: 'var(--text-primary)',
                fontSize: '13px',
                fontFamily: 'inherit',
                marginTop: '6px',
              }}
            />
          </div>

          {/* Continue to Review Button */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
            <button
              type="submit"
              className="btn-primary"
              style={{
                padding: '12px 28px',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              Review Answers Before Submitting (FR-06) <Icon name="arrow" />
            </button>
          </div>
        </form>
      )}

      {/* STEP 2: MANDATORY REVIEW & EDIT (PRD FR-06) */}
      {step === 'review' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="app-panel" style={{ padding: '24px', borderRadius: '12px', background: 'var(--surface-card)', border: '1px solid var(--brand-mint)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
              <span style={{ color: 'var(--brand-mint)' }}><Icon name="shield" /></span>
              <h2 style={{ fontSize: '18px', fontWeight: 800, margin: 0, color: 'var(--text-primary)' }}>
                Step 2: Review Your Responses Before Evaluation
              </h2>
            </div>
            <p style={{ margin: '0 0 20px', color: 'var(--text-secondary)', fontSize: '14px' }}>
              Per product requirement <b>FR-06</b>, you must review and have the opportunity to correct your questionnaire
              inputs before submitting them to the screening ruleset.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '14px', marginBottom: '24px' }}>
              <div style={{ background: 'var(--surface-subtle)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>Primary Sensation</span>
                <p style={{ margin: '4px 0 0', fontWeight: 700, fontSize: '14px', color: 'var(--text-primary)' }}>
                  {primarySymptoms.find((s) => s.id === answers.primary_symptom)?.label}
                </p>
              </div>

              <div style={{ background: 'var(--surface-subtle)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>Intensity</span>
                <p style={{ margin: '4px 0 0', fontWeight: 700, fontSize: '14px', color: 'var(--text-primary)', textTransform: 'capitalize' }}>
                  {answers.intensity}
                </p>
              </div>

              <div style={{ background: 'var(--surface-subtle)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>Duration</span>
                <p style={{ margin: '4px 0 0', fontWeight: 700, fontSize: '14px', color: 'var(--text-primary)' }}>
                  {durations.find((d) => d.id === answers.duration)?.label}
                </p>
              </div>

              <div style={{ background: 'var(--surface-subtle)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>Activity Context</span>
                <p style={{ margin: '4px 0 0', fontWeight: 700, fontSize: '14px', color: 'var(--text-primary)' }}>
                  {contexts.find((c) => c.id === answers.activity_context)?.label}
                </p>
              </div>
            </div>

            <div style={{ background: 'var(--surface-subtle)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-color)', marginBottom: '24px' }}>
              <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>Acute Warning Signs</span>
              <p style={{ margin: '4px 0 0', fontSize: '14px', color: answers.warning_signs.length > 0 ? '#fca5a5' : 'var(--text-primary)', fontWeight: 600 }}>
                {answers.warning_signs.length > 0
                  ? answers.warning_signs.map((s) => warningOptions.find((w) => w.id === s)?.label).join('; ')
                  : 'No acute warning signs reported.'}
              </p>
            </div>

            {answers.notes && (
              <div style={{ background: 'var(--surface-subtle)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-color)', marginBottom: '24px' }}>
                <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>Notes</span>
                <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--text-primary)' }}>{answers.notes}</p>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
              <button
                type="button"
                className="btn-outline"
                onClick={() => setStep('form')}
                style={{ padding: '10px 20px', borderRadius: '8px', fontSize: '14px', cursor: 'pointer' }}
              >
                ← Edit Answers
              </button>

              <button
                type="button"
                className="btn-primary"
                onClick={handleSubmitAssessment}
                disabled={loading}
                style={{
                  padding: '12px 28px',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontWeight: 700,
                  cursor: loading ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                {loading ? 'Evaluating Model...' : 'Confirm & Run Screening Assessment'} <Icon name="arrow" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* STEP 3: RESULTS & AI/ML EXPLANATION (FR-06 & FR-07) */}
      {step === 'result' && result && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Risk Signal Banner */}
          <div
            className="app-panel"
            style={{
              padding: '28px',
              borderRadius: '12px',
              background:
                result.risk_level === 'Elevated Risk Signal'
                  ? 'rgba(239, 68, 68, 0.12)'
                  : result.risk_level === 'Moderate Risk Signal'
                  ? 'rgba(245, 158, 11, 0.12)'
                  : 'rgba(56, 189, 248, 0.12)',
              border: `1.5px solid ${
                result.risk_level === 'Elevated Risk Signal'
                  ? '#ef4444'
                  : result.risk_level === 'Moderate Risk Signal'
                  ? '#f59e0b'
                  : '#38bdf8'
              }`,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
              <div>
                <span
                  style={{
                    display: 'inline-block',
                    padding: '4px 10px',
                    borderRadius: '6px',
                    fontSize: '12px',
                    fontWeight: 800,
                    textTransform: 'uppercase',
                    background:
                      result.risk_level === 'Elevated Risk Signal'
                        ? '#ef4444'
                        : result.risk_level === 'Moderate Risk Signal'
                        ? '#f59e0b'
                        : '#0284c7',
                    color: '#fff',
                    marginBottom: '10px',
                  }}
                >
                  {result.risk_level}
                </span>
                <h2 style={{ fontSize: '24px', fontWeight: 800, margin: '0 0 6px', color: 'var(--text-primary)' }}>
                  Screening Risk Signal: {(result.risk_score * 100).toFixed(0)}%
                </h2>
                <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '14px' }}>
                  {result.disclaimer}
                </p>
              </div>

              {/* Prediction Uncertainty (FR-07) */}
              <div
                style={{
                  background: 'var(--surface-card)',
                  padding: '14px 18px',
                  borderRadius: '10px',
                  border: '1px solid var(--border-color)',
                  textAlign: 'right',
                  minWidth: '240px',
                }}
              >
                <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Prediction Uncertainty (FR-07)
                </div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: '#f59e0b', margin: '6px 0' }}>
                  {result.uncertainty_range
                    ? `[${(result.uncertainty_range[0] * 100).toFixed(0)}% — ${(result.uncertainty_range[1] * 100).toFixed(0)}%]`
                    : (result.uncertainty_note || 'uncertainty not estimated for this demo ruleset')}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  Model Version: <b>{result.model_version || 'DEMO RULESET v2.1, not evaluated'}</b>
                </div>
              </div>
            </div>
          </div>

          {/* AI/ML Feature Contributions (FR-07) */}
          <div className="app-panel" style={{ padding: '24px', borderRadius: '12px', background: 'var(--surface-card)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span style={{ color: 'var(--brand-mint)' }}><Icon name="sparkles" /></span>
              <h3 style={{ fontSize: '17px', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
                FR-07 AI/ML Explanation: Transparent Feature Attributions
              </h3>
            </div>
            <p style={{ margin: '0 0 20px', color: 'var(--text-muted)', fontSize: '13px' }}>
              Deterministic feature contribution weights show how each category contributed to the screening score without fabrication.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {Object.entries(result.feature_contributions).map(([featureName, weight]) => {
                const cleanName = featureName.replace(/_/g, ' ').replace('factor', '').trim();
                const pct = Math.round(weight * 100);
                return (
                  <div key={featureName}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 600, color: 'var(--text-primary)', textTransform: 'capitalize' }}>{cleanName}</span>
                      <span style={{ fontWeight: 700, color: 'var(--brand-mint)' }}>+{weight.toFixed(3)} (+{pct}%)</span>
                    </div>
                    <div style={{ height: '8px', background: 'var(--surface-subtle)', borderRadius: '4px', overflow: 'hidden' }}>
                      <div
                        style={{
                          height: '100%',
                          width: `${Math.min(100, (weight / 0.40) * 100)}%`,
                          background: 'linear-gradient(90deg, #38bdf8, #4ade80)',
                          borderRadius: '4px',
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Contributing Factors & Clinical Next Steps */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
            <div className="app-panel" style={{ padding: '20px', borderRadius: '12px', background: 'var(--surface-card)', border: '1px solid var(--border-color)' }}>
              <h4 style={{ fontSize: '15px', fontWeight: 700, margin: '0 0 10px', color: 'var(--text-primary)' }}>
                Contributing Factors
              </h4>
              <ul style={{ margin: 0, paddingLeft: '18px', color: 'var(--text-secondary)', fontSize: '13px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {result.contributing_factors.map((factor, idx) => (
                  <li key={idx}>{factor}</li>
                ))}
              </ul>
            </div>

            <div className="app-panel" style={{ padding: '20px', borderRadius: '12px', background: 'var(--surface-card)', border: '1px solid var(--border-color)' }}>
              <h4 style={{ fontSize: '15px', fontWeight: 700, margin: '0 0 10px', color: 'var(--text-primary)' }}>
                When to Seek Professional Medical Care
              </h4>
              <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '13px', lineHeight: '1.5' }}>
                {result.when_to_seek_care}
              </p>
            </div>
          </div>

          {/* Action buttons */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px' }}>
            <button
              type="button"
              className="btn-outline"
              onClick={() => {
                setStep('form');
                setResult(null);
              }}
              style={{ padding: '10px 20px', borderRadius: '8px', fontSize: '13px', cursor: 'pointer' }}
            >
              Retake Assessment
            </button>

            {go && (
              <button
                type="button"
                className="btn-primary"
                onClick={() => go('trends')}
                style={{ padding: '10px 24px', borderRadius: '8px', fontSize: '13px', cursor: 'pointer' }}
              >
                View in History & Trends
              </button>
            )}
          </div>
        </div>
      )}

      {/* Past Assessments History Drawer / Card */}
      {history.length > 0 && (
        <div className="app-panel" style={{ marginTop: '36px', padding: '24px', borderRadius: '12px', background: 'var(--surface-card)', border: '1px solid var(--border-color)' }}>
          <h3 style={{ fontSize: '17px', fontWeight: 700, margin: '0 0 14px', color: 'var(--text-primary)' }}>
            Assessment Audit History
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {history.map((h) => (
              <div
                key={h.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '12px 16px',
                  borderRadius: '8px',
                  background: 'var(--surface-subtle)',
                  border: '1px solid var(--border-color)',
                  fontSize: '13px',
                }}
              >
                <div>
                  <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{h.risk_level}</span>
                  <span style={{ color: 'var(--text-muted)', marginLeft: '10px' }}>
                    Score: {(h.risk_score * 100).toFixed(0)}%
                    {h.uncertainty_range && h.uncertainty_range.length === 2
                      ? ` (Uncertainty: [${(h.uncertainty_range[0] * 100).toFixed(0)}% - ${(h.uncertainty_range[1] * 100).toFixed(0)}%])`
                      : ` (${h.uncertainty_note || 'uncertainty not estimated for this demo ruleset'})`}
                  </span>
                  {h.is_demo && <span className="tag-badge" style={{ marginLeft: '10px', fontSize: '10px' }}>DEMO</span>}
                </div>
                <time style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                  {new Date(h.created_at).toLocaleString()}
                </time>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
