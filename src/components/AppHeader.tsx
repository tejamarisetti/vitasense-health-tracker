import React from 'react';
import { Logo } from './Logo';
import { Icon } from './Icons';
import { UserProfile } from '../types';

interface AppHeaderProps {
  theme: 'dark' | 'light';
  setTheme: (theme: 'dark' | 'light') => void;
  userProfile?: UserProfile;
  onSearchClick?: () => void;
  onNotificationsClick?: () => void;
  onProfileClick?: () => void;
}

export function AppHeader({
  theme,
  setTheme,
  userProfile,
  onSearchClick,
  onNotificationsClick,
  onProfileClick,
}: AppHeaderProps) {
  const initials = userProfile?.name
    ? userProfile.name
        .split(' ')
        .map((n) => n[0])
        .filter(Boolean)
        .slice(0, 2)
        .join('')
        .toUpperCase()
    : 'AM';

  return (
    <header className="app-header">
      <div className="mobile-logo">
        <Logo />
      </div>

      <div className="connection">
        <i /> All systems connected
      </div>

      <div className="app-actions">
        <button className="command" onClick={onSearchClick} type="button">
          <Icon name="search" />
          <span>Search or ask anything</span>
          <kbd>⌘ K</kbd>
        </button>

        <button
          className="icon-button"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          aria-label="Toggle theme"
          type="button"
        >
          <Icon name={theme === 'dark' ? 'sun' : 'moon'} />
        </button>

        <button
          className="icon-button has-notice"
          onClick={onNotificationsClick}
          aria-label="Notifications"
          type="button"
        >
          <Icon name="bell" />
          <i />
        </button>

        <button
          className="avatar-btn"
          onClick={onProfileClick}
          title={`Profile: ${userProfile?.name || 'Alex Morgan'} (Click to view/edit details)`}
          aria-label="Open personal profile"
          type="button"
        >
          <div className="avatar">
            {initials}
          </div>
        </button>
      </div>
    </header>
  );
}
