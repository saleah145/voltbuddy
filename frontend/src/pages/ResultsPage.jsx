import { NavLink } from 'react-router-dom'
import { EmptyState, PageHeader, StatCard } from '../components/Shared'
import { useVoltBuddy } from '../context/VoltBuddyContext'
import { getRateMessage } from '../utils/format'

export default function ResultsPage() {
  const { simulation } = useVoltBuddy()

  if (!simulation) {
    return (
      <div className="results-page page-identity-results">
        <PageHeader eyebrow="RESULTS" title="Latest optimization results" description="Run a simulation to see your results here." />
        <EmptyState
          icon="⚡"
          title="No results yet"
          action={
            <NavLink className="primary-button" to="/simulate">
              Run a simulation →
            </NavLink>
          }
        >
          Once you optimize a schedule, your cost comparison and recommendations will show up here.
        </EmptyState>
      </div>
    )
  }

  return (
    <div className="results-page page-identity-results">
      <PageHeader
        eyebrow="RESULTS"
        title="Your VoltBuddy plan"
        description="Here's what changed, what stayed the same, and why."
        action={
          <div className="setup-next-actions">
            <NavLink className="secondary-button" to="/schedule">View Full Schedule</NavLink>
            <NavLink className="secondary-button" to="/simulate">Run Another Simulation</NavLink>
            <NavLink className="secondary-button" to="/">Back to Dashboard</NavLink>
          </div>
        }
      />

      {simulation.daily_plan && (
        <section className="results-report-banner">
          <div>
            <span className="report-kicker">YOUR SAVINGS REPORT</span>
            <strong>${simulation.daily_plan.estimated_daily_savings.toFixed(2)} estimated saved per day</strong>
            <small>{simulation.daily_plan.shifted_appliances} appliance{simulation.daily_plan.shifted_appliances === 1 ? '' : 's'} moved to cheaper times.</small>
          </div>
          <NavLink className="primary-button" to="/schedule">Open schedule →</NavLink>
        </section>
      )}

      <section className="panel rate-panel">
        <div>
          <p className="eyebrow">CURRENT ELECTRICITY CONDITIONS</p>
          <h2>{simulation.grid.tier.replaceAll('_', ' ').toUpperCase()}</h2>
          <div className="large-metric">${simulation.grid.rate}<small>/kWh</small></div>
          <p className="muted">{getRateMessage(simulation.grid)}</p>
        </div>
        <div className="hero-orb small">{simulation.grid.tier === 'on_peak' ? '⚡' : '🌿'}</div>
        <NavLink className="text-action-button" to="/rates" style={{ alignSelf: 'flex-start' }}>
          View rate details →
        </NavLink>
      </section>

      <div className="stats-grid">
        <StatCard label="Normal cost" value={`$${simulation.without_voltbuddy}/hr`} note="If everything kept running" />
        <StatCard label="With VoltBuddy" value={`$${simulation.with_voltbuddy}/hr`} note="After smart adjustments" />
        <StatCard label="Estimated savings" value={`$${simulation.total_savings_per_hour}/hr`} note="Potential hourly savings" />
      </div>

      {simulation.daily_plan && (
        <>
          <section className="panel daily-plan-hero">
            <div>
              <p className="eyebrow">24-HOUR OPTIMIZATION</p>
              <h2>Your cheaper daily schedule</h2>
              <p className="muted">
                VoltBuddy evaluated every allowed start time across the day and kept critical or non-flexible appliances in place.
              </p>
            </div>

            <div className="daily-savings-metric">
              <span>Estimated daily savings</span>
              <strong>${simulation.daily_plan.estimated_daily_savings.toFixed(2)}</strong>
              <small>
                {simulation.daily_plan.shifted_appliances} appliance{simulation.daily_plan.shifted_appliances === 1 ? '' : 's'} shifted
              </small>
            </div>
          </section>

          <div className="stats-grid daily-stats-grid">
            <StatCard label="Original daily cost" value={`$${simulation.daily_plan.original_daily_cost.toFixed(2)}`} note="Using your selected start time" />
            <StatCard label="VoltBuddy daily cost" value={`$${simulation.daily_plan.optimized_daily_cost.toFixed(2)}`} note="After valid schedule shifts" />
            <StatCard
              label="Cheapest rate"
              value={`$${Math.min(...simulation.daily_plan.hourly_rates.map((item) => item.rate)).toFixed(3)}/kWh`}
              note="Lowest published rate today"
            />
          </div>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">SHIFTED VS UNCHANGED</p>
                <h2>Quick summary</h2>
              </div>
              <NavLink className="text-action-button" to="/schedule">Full schedule →</NavLink>
            </div>
            <div className="schedule-list">
              {simulation.daily_plan.schedule.map((item) => (
                <div className={`schedule-card ${item.shifted ? 'shifted' : 'unchanged'}`} key={item.id}>
                  <div className="schedule-card-heading">
                    <div>
                      <h3>{item.name}</h3>
                      <span>{item.runtime_hours} hr{item.runtime_hours === 1 ? '' : 's'} · {item.kw} kW</span>
                    </div>
                    <span className={`schedule-status ${item.shifted ? 'shifted' : 'unchanged'}`}>
                      {item.shifted ? 'Shifted' : 'Unchanged'}
                    </span>
                  </div>
                  <p>{item.reason}</p>
                  {item.savings > 0 && (
                    <div className="schedule-savings">
                      <span>Estimated savings</span>
                      <strong>${item.savings.toFixed(2)}/day</strong>
                    </div>
                  )}
                </div>
              ))}
            </div>
            <p className="runtime-plan-note">{simulation.daily_plan.runtime_note}</p>
          </section>
        </>
      )}

      <section className="panel results-recommendations-teaser">
        <div>
          <p className="eyebrow">WANT THE FULL BREAKDOWN?</p>
          <h2>See why VoltBuddy made each decision</h2>
          <p className="muted">
            {simulation.optimization_summary.shift_recommendations} recommendation{simulation.optimization_summary.shift_recommendations === 1 ? '' : 's'} and a per-appliance score breakdown.
          </p>
        </div>
        <NavLink className="primary-button" to="/recommendations">
          View Recommendations →
        </NavLink>
      </section>
    </div>
  )
}
