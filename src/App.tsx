import React, { useState } from 'react';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { OverviewPage } from './pages/OverviewPage';
import { CompanionPage } from './pages/CompanionPage';
import { SignalsPage } from './pages/SignalsPage';
import { TrendsPage } from './pages/TrendsPage';
import { AlertsPage } from './pages/AlertsPage';
import { BenchmarkPage } from './pages/BenchmarkPage';
import { SettingsPage } from './pages/SettingsPage';
import { Sidebar, navItems } from './components/Sidebar';
import { AppHeader } from './components/AppHeader';
import { Icon } from './components/Icons';

export function App() {
  const [page, setPage] = useState<string>('landing');
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');

  const go = (targetPage: string) => {
    setPage(targetPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className={theme === 'light' ? 'theme-light' : 'theme-dark'}>
      {page === 'landing' ? (
        <LandingPage go={go} theme={theme} setTheme={setTheme} />
      ) : page === 'login' ? (
        <LoginPage go={go} theme={theme} setTheme={setTheme} />
      ) : (
        <div className="workspace">
          <Sidebar page={page} go={go} />

          <div className="app-shell">
            <AppHeader
              theme={theme}
              setTheme={setTheme}
              onSearchClick={() => go('companion')}
              onNotificationsClick={() => go('alerts')}
            />

            <main className="app-main">
              {page === 'overview' && <OverviewPage go={go} />}
              {page === 'companion' && <CompanionPage />}
              {page === 'signals' && <SignalsPage />}
              {page === 'benchmark' && <BenchmarkPage />}
              {page === 'trends' && <TrendsPage />}
              {page === 'alerts' && <AlertsPage go={go} />}
              {page === 'settings' && <SettingsPage go={go} theme={theme} setTheme={setTheme} />}
            </main>
          </div>

          {/* Mobile Bottom Navigation */}
          <nav className="mobile-nav">
            {navItems.map((n) => (
              <button
                key={n.page}
                className={page === n.page ? 'active' : ''}
                onClick={() => go(n.page)}
                type="button"
              >
                <Icon name={n.icon} />
                <span>{n.label.split(' ')[0]}</span>
              </button>
            ))}
            <button
              className={page === 'settings' ? 'active' : ''}
              onClick={() => go('settings')}
              type="button"
            >
              <Icon name="settings" />
              <span>Settings</span>
            </button>
          </nav>
        </div>
      )}
    </div>
  );
}

export default App;
