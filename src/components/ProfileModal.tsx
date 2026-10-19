import React, { useState } from 'react';
import { Icon } from './Icons';
import { UserProfile, saveUserProfile } from '../types';

interface ProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  userProfile: UserProfile;
  onUpdateProfile: (updated: UserProfile) => void;
  onLogout: () => void;
}

export function ProfileModal({
  isOpen,
  onClose,
  userProfile,
  onUpdateProfile,
  onLogout,
}: ProfileModalProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Form state
  const [formData, setFormData] = useState<UserProfile>(userProfile);

  // Synchronize formData when userProfile prop changes
  React.useEffect(() => {
    setFormData(userProfile);
  }, [userProfile]);

  if (!isOpen) return null;

  const initials = userProfile.name
    .split(' ')
    .map((n) => n[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase() || 'U';

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    saveUserProfile(formData);
    onUpdateProfile(formData);
    setSaveSuccess(true);
    setIsEditing(false);
    setTimeout(() => setSaveSuccess(false), 2500);
  };

  return (
    <div className="profile-modal-backdrop" onClick={onClose}>
      <div className="profile-modal-window" onClick={(e) => e.stopPropagation()}>
        {/* Modal Top Bar */}
        <div className="profile-modal-topbar">
          <div className="profile-badge-row">
            <span className="profile-kicker">PERSONAL HEALTH PROFILE</span>
            {saveSuccess && (
              <span className="save-success-tag">
                <Icon name="check" size={12} /> Saved
              </span>
            )}
          </div>
          <button className="profile-modal-close" onClick={onClose} aria-label="Close profile">
            ✕
          </button>
        </div>

        {/* User Card Header */}
        <div className="profile-card-header">
          <div className="profile-avatar-large">
            {initials}
            <span className="profile-status-online" title="Telemetry calibrated" />
          </div>

          <div className="profile-header-meta">
            <h2>{userProfile.name}</h2>
            <p className="profile-email">{userProfile.email}</p>
            <div className="profile-tags">
              <span className="profile-provider-pill">
                {userProfile.provider === 'google' && <Icon name="google" size={13} />}
                {userProfile.provider === 'apple' && <Icon name="apple" size={13} />}
                {userProfile.provider === 'email' && <Icon name="shield" size={13} />}
                <span>
                  {userProfile.provider === 'google'
                    ? 'Google Account'
                    : userProfile.provider === 'apple'
                    ? 'Apple ID'
                    : 'VitaSense Direct'}
                </span>
              </span>
              <span className="profile-plan-pill">Research Telemetry Active</span>
            </div>
          </div>

          {/* Action Symbols: Edit Symbol and Logout Symbol */}
          <div className="profile-header-actions">
            <button
              type="button"
              className={`profile-action-btn edit-btn ${isEditing ? 'active' : ''}`}
              onClick={() => setIsEditing(!isEditing)}
              title="Edit personal & health details"
              aria-label="Edit details"
            >
              <Icon name="edit" size={16} />
              <span>{isEditing ? 'Cancel' : 'Edit'}</span>
            </button>

            <button
              type="button"
              className="profile-action-btn logout-btn"
              onClick={onLogout}
              title="Log out of VitaSense"
              aria-label="Log out"
            >
              <Icon name="logout" size={16} />
              <span>Log out</span>
            </button>
          </div>
        </div>

        {/* Content Section: View Mode vs Edit Mode */}
        <div className="profile-modal-body">
          {!isEditing ? (
            <div className="profile-view-grid">
              <div className="profile-section-title">
                <Icon name="activity" size={16} />
                <span>Baseline Health Metrics</span>
              </div>

              <div className="profile-metrics-cards">
                <div className="metric-box">
                  <small>AGE</small>
                  <strong>{userProfile.age} <span className="unit">yrs</span></strong>
                </div>

                <div className="metric-box">
                  <small>BIOLOGICAL SEX</small>
                  <strong>{userProfile.sex}</strong>
                </div>

                <div className="metric-box">
                  <small>HEIGHT</small>
                  <strong>{userProfile.height}</strong>
                </div>

                <div className="metric-box">
                  <small>WEIGHT</small>
                  <strong>{userProfile.weight}</strong>
                </div>

                <div className="metric-box highlight-metric">
                  <small>RESTING HEART RATE</small>
                  <strong>{userProfile.restingHr} <span className="unit">bpm</span></strong>
                </div>

                <div className="metric-box">
                  <small>ACTIVITY LEVEL</small>
                  <strong>{userProfile.activityLevel}</strong>
                </div>
              </div>

              <div className="profile-goal-card">
                <div className="goal-icon">
                  <Icon name="pulse" size={18} />
                </div>
                <div className="goal-meta">
                  <small>PRIMARY HEALTH GOAL</small>
                  <strong>{userProfile.healthGoal}</strong>
                  <p>Thresholds and anomaly sensitivity calibrated to this wellness target.</p>
                </div>
              </div>
            </div>
          ) : (
            <form className="profile-edit-form" onSubmit={handleSave}>
              <div className="profile-section-title">
                <Icon name="edit" size={16} />
                <span>Edit Personal & Health Details</span>
              </div>

              <div className="form-fields-grid">
                <label className="profile-field">
                  <span>Full Name</span>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                  />
                </label>

                <label className="profile-field">
                  <span>Email Address</span>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    required
                  />
                </label>

                <label className="profile-field">
                  <span>Age</span>
                  <input
                    type="number"
                    min="1"
                    max="120"
                    value={formData.age}
                    onChange={(e) => setFormData({ ...formData, age: Number(e.target.value) || 0 })}
                    required
                  />
                </label>

                <label className="profile-field">
                  <span>Biological Sex</span>
                  <select
                    value={formData.sex}
                    onChange={(e) =>
                      setFormData({ ...formData, sex: e.target.value as UserProfile['sex'] })
                    }
                  >
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                    <option value="Prefer not to say">Prefer not to say</option>
                  </select>
                </label>

                <label className="profile-field">
                  <span>Height</span>
                  <input
                    type="text"
                    value={formData.height}
                    onChange={(e) => setFormData({ ...formData, height: e.target.value })}
                    placeholder="e.g. 178 cm"
                    required
                  />
                </label>

                <label className="profile-field">
                  <span>Weight</span>
                  <input
                    type="text"
                    value={formData.weight}
                    onChange={(e) => setFormData({ ...formData, weight: e.target.value })}
                    placeholder="e.g. 72 kg"
                    required
                  />
                </label>

                <label className="profile-field">
                  <span>Resting HR (bpm)</span>
                  <input
                    type="number"
                    min="35"
                    max="200"
                    value={formData.restingHr}
                    onChange={(e) =>
                      setFormData({ ...formData, restingHr: Number(e.target.value) || 0 })
                    }
                    required
                  />
                </label>

                <label className="profile-field">
                  <span>Activity Level</span>
                  <select
                    value={formData.activityLevel}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        activityLevel: e.target.value as UserProfile['activityLevel'],
                      })
                    }
                  >
                    <option value="Sedentary">Sedentary (desk job, minimal motion)</option>
                    <option value="Lightly Active">Lightly Active (1-3 workouts/week)</option>
                    <option value="Moderately Active">Moderately Active (3-5 workouts/week)</option>
                    <option value="Very Active">Very Active (daily intense training)</option>
                  </select>
                </label>

                <label className="profile-field full-width">
                  <span>Primary Wellness Goal</span>
                  <select
                    value={formData.healthGoal}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        healthGoal: e.target.value as UserProfile['healthGoal'],
                      })
                    }
                  >
                    <option value="Cardiovascular Wellness">Cardiovascular Wellness</option>
                    <option value="Athletic Performance">Athletic Performance</option>
                    <option value="Stress & Recovery">Stress & Recovery</option>
                    <option value="Sleep Optimization">Sleep Optimization</option>
                  </select>
                </label>
              </div>

              <div className="profile-edit-actions">
                <button
                  type="button"
                  className="button button-quiet"
                  onClick={() => {
                    setFormData(userProfile);
                    setIsEditing(false);
                  }}
                >
                  Cancel
                </button>
                <button type="submit" className="button button-primary">
                  <Icon name="check" size={16} /> Save Changes
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
