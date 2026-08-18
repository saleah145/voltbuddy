import { NavLink } from 'react-router-dom'
import { StatCard } from '../components/Shared'
import { useVoltBuddy } from '../context/VoltBuddyContext'

export default function DashboardPage() {
  const {
    hasHome,
    appliances,
    homes,
    activeHomeName,
    liveGrid,
    liveGridLoading,
    simulation,
    estimatedSavings,
    appliancesShifted,
    initialLoading,
  } = useVoltBuddy()

  // Only claim a specific "current home" once we know which one is active —
  // guessing the first saved home would be misleading if the person hasn't
  // explicitly loaded one this session.
  const homeLabel = activeHomeName || null

  return (
    <div className="dashboard-page page-identity-dashboard">
      <section className="welcome-hero">
        <div className="welcome-copy">
          <p className="eyebrow">SMARTER HOME ENERGY</p>
          <h1>VoltBuddy helps you find cheaper times to run your home appliances.</h1>
          <p className="welcome-description">
            Add what you have, tell VoltBuddy when you normally use it, and get a
            simple plan for saving money — without decoding your utility bill.
          </p>

          <div className="dashboard-cta-row">
            {initialLoading ? (
              <span className="secondary-button welcome-cta disabled-link" aria-disabled="true">
                Loading your home...
              </span>
            ) : hasHome ? (
              <NavLink className="primary-button welcome-cta" to="/home">
                Manage Home
              </NavLink>
            ) : (
              <NavLink className="primary-button welcome-cta" to="/home">
                Set Up Home
              </NavLink>
            )}
            <NavLink className="secondary-button welcome-cta" to="/simulate">
              Start Optimizing
            </NavLink>
          </div>

          <p className="welcome-helper">
            {initialLoading
              ? 'Checking your saved appliances...'
              : hasHome
                ? `${appliances.length} appliance${appliances.length === 1 ? '' : 's'} saved${homeLabel ? ` in ${homeLabel}` : ''}.`
                : 'Start with what is in your home. VoltBuddy handles the energy details.'}
          </p>
        </div>

        <div className="welcome-visual" aria-hidden="true">
          <div className="welcome-home-icon">
            <img
              src="/favicon.png"
              alt=""
              style={{
                width: '92px',
                height: '92px',
                objectFit: 'contain',
                display: 'block',
              }}
            />
          </div>
          <div className="welcome-signal welcome-signal-one">⚡</div>
          <div className="welcome-signal welcome-signal-two">↓</div>
        </div>
      </section>

      <section className="dashboard-launch-grid">
        <NavLink className="dashboard-launch-card primary" to="/simulate">
          <span className="launch-kicker">OPTIMIZE</span>
          <strong>Build today’s plan</strong>
          <small>Choose your appliances and let VoltBuddy find cheaper times.</small>
          <span className="launch-arrow">→</span>
        </NavLink>

        <NavLink className="dashboard-launch-card" to="/appliances">
          <span className="launch-kicker">APPLIANCES</span>
          <strong>Add something new</strong>
          <small>Search the catalog, upload a photo, or use an estimate.</small>
          <span className="launch-arrow">→</span>
        </NavLink>

        <NavLink className="dashboard-launch-card" to="/schedule">
          <span className="launch-kicker">SCHEDULE</span>
          <strong>See your latest timeline</strong>
          <small>Compare your normal routine with the VoltBuddy plan.</small>
          <span className="launch-arrow">→</span>
        </NavLink>
      </section>

      <section className="panel dashboard-grid-status">
        <div className="panel-heading simplified-heading">
          <div>
            <p className="eyebrow">RIGHT NOW</p>
            <h2>Grid &amp; rate status</h2>
          </div>
          <NavLink className="text-action-button" to="/rates">
            View details →
          </NavLink>
        </div>

        {liveGridLoading ? (
          <p className="muted">Checking current grid conditions...</p>
        ) : liveGrid?.available ? (
          <div className="metric-list">
            <div>
              <span>Current demand</span>
              <strong>{Number(liveGrid.demand_mwh).toLocaleString()} MWh</strong>
            </div>
            <div>
              <span>Trend</span>
              <strong>
                {liveGrid.condition === 'rising' ? '↗ Rising' : liveGrid.condition === 'falling' ? '↘ Falling' : '→ Stable'}
              </strong>
            </div>
          </div>
        ) : (
          <p className="muted">Live grid data is unavailable right now, but you can still run a simulation using published rate tiers.</p>
        )}
      </section>

      {hasHome && (
        <section className="panel">
          <div className="panel-heading simplified-heading">
            <div>
              <p className="eyebrow">YOUR HOME</p>
              <h2>{homeLabel || 'Current setup'}</h2>
            </div>
          </div>
          <p className="muted">
            {appliances.length} appliance{appliances.length === 1 ? '' : 's'} saved.{' '}
            {homes.length > 1 ? `${homes.length} saved homes available.` : ''}
          </p>
        </section>
      )}

      <section className="welcome-value-section" aria-label="What VoltBuddy gives you">
        <div className="welcome-section-heading">
          <p className="eyebrow">{simulation ? 'YOUR LAST PLAN' : "WHAT YOU'LL GET"}</p>
          <h2>
            {simulation
              ? 'A quick look at your most recent optimization.'
              : 'A clear answer, not another energy dashboard to figure out.'}
          </h2>
        </div>

        {simulation ? (
          <div className="stats-grid">
            <StatCard
              label="Estimated daily savings"
              value={estimatedSavings != null ? `$${estimatedSavings.toFixed(2)}` : '—'}
            />
            <StatCard
              label="Appliances shifted"
              value={appliancesShifted != null ? appliancesShifted : '—'}
            />
            <StatCard label="Current rate" value={simulation.grid ? `$${simulation.grid.rate}/kWh` : '—'} />
          </div>
        ) : (
          <div className="welcome-value-grid">
            <article className="welcome-value-card">
              <div className="welcome-value-icon">$</div>
              <h3>Estimated savings</h3>
              <p>See how much changing when you use flexible appliances could save.</p>
            </article>

            <article className="welcome-value-card">
              <div className="welcome-value-icon">◷</div>
              <h3>Smarter timing</h3>
              <p>Find lower-cost times to run appliances that can be moved.</p>
            </article>

            <article className="welcome-value-card">
              <div className="welcome-value-icon">✓</div>
              <h3>Clear recommendations</h3>
              <p>See what VoltBuddy recommends, when to do it, and why it helps.</p>
            </article>
          </div>
        )}

        {simulation && (
          <NavLink className="secondary-button" to="/results">
            View full results →
          </NavLink>
        )}
      </section>
    </div>
  )
}
