export interface UserProfile {
  name: string;
  email: string;
  age: number;
  sex: 'Male' | 'Female' | 'Other' | 'Prefer not to say';
  height: string;
  weight: string;
  restingHr: number;
  activityLevel: 'Sedentary' | 'Lightly Active' | 'Moderately Active' | 'Very Active';
  healthGoal: 'Cardiovascular Wellness' | 'Athletic Performance' | 'Stress & Recovery' | 'Sleep Optimization';
  provider: 'email' | 'google' | 'apple';
}

export const defaultUserProfile: UserProfile = {
  name: 'Alex Morgan',
  email: 'alex@example.com',
  age: 29,
  sex: 'Male',
  height: '178 cm',
  weight: '72 kg',
  restingHr: 64,
  activityLevel: 'Moderately Active',
  healthGoal: 'Cardiovascular Wellness',
  provider: 'email',
};

export interface ComponentCheckResult {
  status: 'pass' | 'fail' | 'warning';
  score: number;
  details: string;
}

export interface MeasurementRecord {
  id: number;
  user_id: number;
  type: 'heart_rate' | 'spo2' | 'respiratory_rate' | 'hrv';
  value: number;
  unit: string;
  timestamp: string;
  source: 'manual' | 'import' | 'demo';
  trust_score: number;
  quality_flags: string[];
  component_checks: Record<string, ComponentCheckResult>;
  created_at: string;
}

const STORAGE_KEY = 'vitasense_user_profile';
const TOKEN_KEY = 'vitasense_auth_token';

export function getAuthToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch (err) {
    return null;
  }
}

export function setAuthToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch (err) {
    console.warn('Could not save auth token to localStorage', err);
  }
}

export function clearAuthToken(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch (err) {
    console.warn('Could not remove auth token from localStorage', err);
  }
}

export function loadUserProfile(): UserProfile {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      return { ...defaultUserProfile, ...parsed };
    }
  } catch (err) {
    console.warn('Could not load user profile from storage', err);
  }
  return defaultUserProfile;
}

export function saveUserProfile(profile: UserProfile): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
  } catch (err) {
    console.warn('Could not save user profile to storage', err);
  }
}
