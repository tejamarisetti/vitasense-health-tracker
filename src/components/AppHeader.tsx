import React from 'react';
import { Logo } from './Logo';
import { Icon } from './Icons';

interface AppHeaderProps {
  theme: 'dark' | 'light';
  setTheme: (theme: 'dark' | 'light') => void;
  onSearchClick?: () => void;
  onNotificationsClick?: () => void;
}

export function AppHeader({
  theme,
  setTheme,
  onSearchClick,
  onNotificationsClick
}: AppHeaderProps) {
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

        <div className="avatar" title="Alex Morgan">
          AM
        </div>
      </div>
    </header>
  );
}
