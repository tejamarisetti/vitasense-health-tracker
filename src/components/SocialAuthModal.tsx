import React, { useState } from 'react';
import { Icon } from './Icons';
import { UserProfile, saveUserProfile } from '../types';

interface SocialAuthModalProps {
  provider: 'google' | 'apple' | null;
  onClose: () => void;
  onSuccess: (profile: UserProfile) => void;
}

export function SocialAuthModal({ provider, onClose, onSuccess }: SocialAuthModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedGoogleAccount, setSelectedGoogleAccount] = useState<'default' | 'custom'>('default');
  const [customEmail, setCustomEmail] = useState('');
  const [appleShareEmail, setAppleShareEmail] = useState<'share' | 'hide'>('share');

  if (!provider) return null;

  const handleGoogleConfirm = () => {
    setIsSubmitting(true);
    setTimeout(() => {
      const email = selectedGoogleAccount === 'custom' && customEmail.trim()
        ? customEmail.trim()
        : 'alex.morgan@gmail.com';
      const name = selectedGoogleAccount === 'custom'
        ? (customEmail.split('@')[0] || 'Google User')
        : 'Alex Morgan';
      
      const newProfile: UserProfile = {
        name,
        email,
        age: 29,
        sex: 'Male',
        height: '178 cm',
        weight: '72 kg',
        restingHr: 64,
        activityLevel: 'Moderately Active',
        healthGoal: 'Cardiovascular Wellness',
        provider: 'google',
      };
      saveUserProfile(newProfile);
      setIsSubmitting(false);
      onSuccess(newProfile);
    }, 600);
  };

  const handleAppleConfirm = () => {
    setIsSubmitting(true);
    setTimeout(() => {
      const email = appleShareEmail === 'share'
        ? 'alex.morgan@icloud.com'
        : 'alex.privaterelay@appleid.com';

      const newProfile: UserProfile = {
        name: 'Alex Morgan',
        email,
        age: 29,
        sex: 'Male',
        height: '178 cm',
        weight: '72 kg',
        restingHr: 64,
        activityLevel: 'Moderately Active',
        healthGoal: 'Cardiovascular Wellness',
        provider: 'apple',
      };
      saveUserProfile(newProfile);
      setIsSubmitting(false);
      onSuccess(newProfile);
    }, 600);
  };

  return (
    <div className="social-modal-backdrop" onClick={onClose}>
      <div className="social-modal-window" onClick={(e) => e.stopPropagation()}>
        <button className="social-modal-close" onClick={onClose} aria-label="Close">
          ✕
        </button>

        {provider === 'google' && (
          <div className="social-modal-content google-auth-content">
            <div className="social-brand-header">
              <span className="google-icon-shell">
                <Icon name="google" size={28} />
              </span>
              <h3>Sign in with Google</h3>
              <p>Choose an account to continue to <b>VitaSense AI</b></p>
            </div>

            <div className="social-account-list">
              <div
                className={`social-account-item ${selectedGoogleAccount === 'default' ? 'selected' : ''}`}
                onClick={() => setSelectedGoogleAccount('default')}
              >
                <div className="account-avatar google-avatar">AM</div>
                <div className="account-meta">
                  <strong>Alex Morgan</strong>
                  <small>alex.morgan@gmail.com</small>
                </div>
                {selectedGoogleAccount === 'default' && <Icon name="check" size={16} />}
              </div>

              <div
                className={`social-account-item ${selectedGoogleAccount === 'custom' ? 'selected' : ''}`}
                onClick={() => setSelectedGoogleAccount('custom')}
              >
                <div className="account-avatar custom-avatar">+</div>
                <div className="account-meta">
                  <strong>Use another Google account</strong>
                  <small>Sign in with work or personal email</small>
                </div>
                {selectedGoogleAccount === 'custom' && <Icon name="check" size={16} />}
              </div>
            </div>

            {selectedGoogleAccount === 'custom' && (
              <div className="custom-account-input">
                <input
                  type="email"
                  value={customEmail}
                  onChange={(e) => setCustomEmail(e.target.value)}
                  placeholder="name@gmail.com"
                  autoFocus
                />
              </div>
            )}

            <div className="social-modal-terms">
              To continue, Google will share your name, email address, and language preference with VitaSense.
            </div>

            <div className="social-modal-actions">
              <button
                type="button"
                className="button button-quiet"
                onClick={onClose}
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="button button-primary"
                onClick={handleGoogleConfirm}
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Signing in…' : 'Continue as Alex'}
              </button>
            </div>
          </div>
        )}

        {provider === 'apple' && (
          <div className="social-modal-content apple-auth-content">
            <div className="social-brand-header">
              <span className="apple-icon-shell">
                <Icon name="apple" size={28} />
              </span>
              <h3>Sign in with Apple ID</h3>
              <p>Use your Apple ID to sign in to <b>VitaSense AI</b></p>
            </div>

            <div className="apple-auth-details">
              <div className="apple-user-pill">
                <Icon name="apple" size={16} />
                <span>Alex Morgan (alex.morgan@icloud.com)</span>
              </div>

              <div className="apple-options-group">
                <label className="apple-option-label">
                  <input
                    type="radio"
                    name="appleEmail"
                    checked={appleShareEmail === 'share'}
                    onChange={() => setAppleShareEmail('share')}
                  />
                  <div>
                    <strong>Share My Email</strong>
                    <small>alex.morgan@icloud.com</small>
                  </div>
                </label>

                <label className="apple-option-label">
                  <input
                    type="radio"
                    name="appleEmail"
                    checked={appleShareEmail === 'hide'}
                    onChange={() => setAppleShareEmail('hide')}
                  />
                  <div>
                    <strong>Hide My Email</strong>
                    <small>Forward to alex.privaterelay@appleid.com</small>
                  </div>
                </label>
              </div>
            </div>

            <div className="social-modal-terms">
              Your Apple ID information will be protected using Apple's privacy architecture.
            </div>

            <div className="social-modal-actions">
              <button
                type="button"
                className="button button-quiet"
                onClick={onClose}
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="button button-primary"
                onClick={handleAppleConfirm}
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Verifying Touch ID…' : 'Continue with Apple'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
