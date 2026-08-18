import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useVoltBuddy } from '../context/VoltBuddyContext'

const NAV_ITEMS = [
  { to: '/', end: true, icon: '⌂', label: 'Dashboard' },
  { to: '/home', icon: '🏠', label: 'Home' },
  { to: '/appliances', icon: '🔎', label: 'Appliances' },
  { to: '/simulate', icon: '⚡', label: 'Optimize' },
  { to: '/schedule', icon: '🗓', label: 'Schedule' },
  { to: '/rates', icon: '🌐', label: 'Rates' },
  { to: '/history', icon: '🕘', label: 'History' },
  { to: '/insights', icon: '📈', label: 'Insights' },
]

// The bottom tab bar on mobile only has room for the primary first-time
// flow; Rates/History/Insights stay reachable from the "More" menu item.
const MOBILE_PRIMARY_ITEMS = NAV_ITEMS.slice(0, 5)

export default function AppLayout() {
  const { backendError, initialLoading, retryInitialLoad } = useVoltBuddy()
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname])

  return (
    <div className="app-shell">
      <aside className={menuOpen ? 'sidebar mobile-open' : 'sidebar'}>
        <div className="brand">
          <div className="brand-logo-wrap">
            <img src="/horicon.png" alt="VoltBuddy" className="brand-logo-image" />
            <span>Smart energy simulator</span>
          </div>
          <button
            type="button"
            className="mobile-menu-close"
            aria-label="Close menu"
            onClick={() => setMenuOpen(false)}
          >
            ✕
          </button>
        </div>

        <nav className="app-nav">
          {NAV_ITEMS.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end}>
              {item.icon} <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <img
            src="/favicon.png"
            alt=""
            className="sidebar-footer-logo"
            aria-hidden="true"
          />
          <span className={backendError ? 'status-dot-offline' : 'status-dot-online'} />
          {backendError ? 'Backend unreachable' : 'Backend connected'}
        </div>
      </aside>

      {menuOpen && <div className="mobile-menu-scrim" onClick={() => setMenuOpen(false)} />}

      <div className="app-main">
        <header className="topbar">
          <button
            type="button"
            className="mobile-menu-button"
            aria-label="Open menu"
            onClick={() => setMenuOpen(true)}
          >
            ☰
          </button>
          <div>
            <span className="topbar-label">VOLTBUDDY</span>
            <strong>Smarter energy use, without guessing.</strong>
          </div>
        </header>

        {backendError && !initialLoading && (
          <div className="backend-error-banner" role="alert">
            <span>Can't reach the VoltBuddy backend. Make sure FastAPI is running.</span>
            <button type="button" className="text-action-button" onClick={retryInitialLoad}>
              Retry
            </button>
          </div>
        )}

        <main className="page-container">
          <Outlet />
        </main>

        <nav className="mobile-bottom-nav" aria-label="Primary">
          {MOBILE_PRIMARY_ITEMS.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end}>
              <span className="mobile-bottom-nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
          <button type="button" onClick={() => setMenuOpen(true)}>
            <span className="mobile-bottom-nav-icon">⋯</span>
            <span>More</span>
          </button>
        </nav>
      </div>
    </div>
  )
}
