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
  { page: 'benchmark', label: 'Benchmarks', icon: 'command' },
  { page: 'alerts', label: 'Alerts', icon: 'bell' }
];

interface SidebarProps {
  page: string;
  go: (page: string) => void;
}

export function Sidebar({ page, go }: SidebarProps) {
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

        <button title="Profile" onClick={() => go('overview')}>
          <Icon name="user" />
          <span>Profile</span>
        </button>
      </nav>

      <button className="side-settings" title="Settings" onClick={() => go('signals')}>
        <Icon name="settings" />
        <span>Settings</span>
      </button>
    </aside>
  );
}
