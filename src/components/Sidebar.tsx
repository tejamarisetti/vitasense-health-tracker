import React from 'react';
import { Logo } from './Logo';
import { Icon, IconName } from './Icons';

export interface NavItem {
  page: string;
  label: string;
  icon: IconName;
}

export const navItems: NavItem[] = [
  { page: 'overview', label: 'Overview', icon: 'home' },
  { page: 'companion', label: 'AI Companion', icon: 'ai' },
  { page: 'trends', label: 'Health Trends', icon: 'trend' },
  { page: 'signals', label: 'Signal Lab', icon: 'activity' },
  { page: 'assessment', label: 'Symptom Lab', icon: 'shield' },
  { page: 'alerts', label: 'Alerts', icon: 'bell' }
];

interface SidebarProps {
  page: string;
  go: (page: string) => void;
  onProfileClick?: () => void;
}

export function Sidebar({ page, go, onProfileClick }: SidebarProps) {
  return (
    <aside className="sidebar">
      <button
        className="side-logo"
        onClick={() => go('landing')}
        aria-label="Back to landing"
      >
        <Logo compact />
      </button>

      <nav>
        {navItems.map((n) => (
          <button
            key={n.page}
            className={page === n.page ? 'active' : ''}
            onClick={() => go(n.page)}
            title={n.label}
          >
            <Icon name={n.icon} />
            <span>{n.label}</span>
            {n.page === 'alerts' && <b className="nav-badge">2</b>}
          </button>
        ))}

        <div className="nav-separator" />

        <button title="Health History" onClick={() => go('trends')}>
          <Icon name="history" />
          <span>Health History</span>
        </button>

        <button
          title="Personal Health Profile"
          onClick={() => (onProfileClick ? onProfileClick() : go('overview'))}
        >
          <Icon name="user" />
          <span>Profile</span>
        </button>
      </nav>

      <button
        className={`side-settings ${page === 'settings' ? 'active' : ''}`}
        title="Settings"
        onClick={() => go('settings')}
      >
        <Icon name="settings" />
        <span>Settings</span>
      </button>
    </aside>
  );
}
