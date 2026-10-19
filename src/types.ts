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

const STORAGE_KEY = 'vitasense_user_profile';

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
