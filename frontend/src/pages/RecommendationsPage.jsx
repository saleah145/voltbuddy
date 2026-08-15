import { NavLink } from 'react-router-dom'
import { EmptyState, PageHeader } from '../components/Shared'
import { useVoltBuddy } from '../context/VoltBuddyContext'
import { getApplianceIcon, getDecisionLabel, getRecommendationIcon } from '../utils/format'

export default function RecommendationsPage() {
  const { simulation } = useVoltBuddy()

  if (!simulation) {
    return (
      <div className="recommendations-page page-identity-results">
        <PageHeader eyebrow="RECOMMENDATIONS" title="Recommendations & decisions" description="Run a simulation to see VoltBuddy's reasoning here." />
        <EmptyState
          icon="⚡"
          title="No recommendations yet"
          action={
            <NavLink className="primary-button" to="/simulate">
              Run a simulation →
            </NavLink>
          }
        >
          Once you optimize a schedule, VoltBuddy's recommendations and per-appliance decisions will show up here.
        </EmptyState>
      </div>
    )
  }

  return (
    <div className="recommendations-page page-identity-results">
      <PageHeader
        eyebrow="RECOMMENDATIONS"
        title="Why VoltBuddy made these calls"
        description="The reasoning and scores behind your results."
        action={<NavLink className="secondary-button" to="/results">Back to results</NavLink>}
      />

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">DECISION SUMMARY</p>
            <h2>What VoltBuddy decided</h2>
          </div>
        </div>
        <p className="muted">
          VoltBuddy used a deterministic weighted score across price, appliance priority, power draw, live demand, and the current generation mix.{' '}
          {simulation.optimization_summary.paused_appliances} appliance{simulation.optimization_summary.paused_appliances === 1 ? ' was' : 's were'} paused and{' '}
          {simulation.optimization_summary.shift_recommendations}{' '}
          {simulation.optimization_summary.shift_recommendations === 1 ? 'was' : 'were'} recommended for shifting.
        </p>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">RECOMMENDATIONS</p>
            <h2>What you can do next</h2>
          </div>
        </div>

        {simulation.recommendations?.length > 0 ? (
          <div className="recommendation-list">
            {simulation.recommendations.map((recommendation, index) => (
              <div className={`recommendation-card ${recommendation.priority}`} key={`${recommendation.type}-${recommendation.appliance_id || 'home'}-${index}`}>
                <div className="recommendation-icon">{getRecommendationIcon(recommendation.type)}</div>
                <div>
                  <div className="recommendation-top">
                    <h3>{recommendation.title}</h3>
                    <span className={`priority-badge ${recommendation.priority}`}>{recommendation.priority}</span>
                  </div>
                  <p>{recommendation.message}</p>
                  {recommendation.best_time && (
                    <div className="recommendation-meta">
                      <span>Best time</span>
                      <strong>{recommendation.best_time}</strong>
                    </div>
                  )}
                  {recommendation.best_time_reason && <small>{recommendation.best_time_reason}</small>}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState icon="✓" title="No extra changes recommended">
            VoltBuddy did not find any additional actions beyond the appliance decisions below.
          </EmptyState>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">APPLIANCE DECISIONS</p>
            <h2>Your home</h2>
          </div>
        </div>

        <div className="appliance-grid">
          {simulation.appliances.map((appliance) => (
            <div className="decision-card" key={appliance.id}>
              <div className="decision-card-top">
                <div className="selector-icon">{getApplianceIcon(appliance.id)}</div>
                <div>
                  <h3>{appliance.name}</h3>
                  <p>{appliance.kw} kW power use</p>
                </div>
              </div>

              <div className={`decision-pill ${appliance.decision}`}>{getDecisionLabel(appliance.decision)}</div>

              <p>{appliance.reason}</p>

              <div className="score-row">
                <span>Optimization score</span>
                <strong>{appliance.optimization_score}</strong>
              </div>

              <div className="score-track">
                <div className="score-fill" style={{ width: `${Math.max(0, Math.min(appliance.optimization_score, 100))}%` }} />
              </div>

              {appliance.score_factors?.length > 0 && (
                <ul className="factor-list">
                  {appliance.score_factors.map((factor, index) => (
                    <li key={`${appliance.id}-${index}`}>{factor}</li>
                  ))}
                </ul>
              )}

              <div className="cost-row">
                <span>Current cost</span>
                <strong>${appliance.cost_per_hour}/hr</strong>
              </div>

              {appliance.savings_per_hour > 0 && (
                <div className="cost-row savings">
                  <span>Estimated savings</span>
                  <strong>${appliance.savings_per_hour}/hr</strong>
                </div>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
