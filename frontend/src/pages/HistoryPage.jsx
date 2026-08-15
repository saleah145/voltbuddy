import { EmptyState, PageHeader, StatCard } from '../components/Shared'
import { useVoltBuddy } from '../context/VoltBuddyContext'
import { formatHour, formatSimulationTimestamp } from '../utils/format'

export default function HistoryPage() {
  const { history, totalHistorySavings, averageSavings, clearHistory } = useVoltBuddy()

  return (
    <div className="history-page page-identity-history">
      <PageHeader
        eyebrow="HISTORY"
        title="Recent VoltBuddy activity"
        description="Review your latest simulations and how estimated savings changed from run to run."
        action={
          history.length > 0 ? (
            <button className="danger-button" onClick={clearHistory}>
              Clear history
            </button>
          ) : null
        }
      />

      <div className="stats-grid">
        <StatCard label="Total estimated savings" value={`$${totalHistorySavings.toFixed(2)}`} />
        <StatCard label="Average per simulation" value={`$${averageSavings.toFixed(2)}`} />
        <StatCard label="Simulations run" value={history.length} />
      </div>

      <section className="panel">
        {history.length === 0 ? (
          <EmptyState icon="🕘" title="No simulations yet">
            Run your first VoltBuddy plan and it will appear here.
          </EmptyState>
        ) : (
          <div className="history-list">
            {history.map((item) => {
              const timestamp = formatSimulationTimestamp(item.created_at)

              return (
                <div className="history-card" key={item.id}>
                  <div className="history-main">
                    <div className="history-icon">{item.tier === 'peak' || item.tier === 'on_peak' ? '⚡' : '🌿'}</div>
                    <div className="history-run-details">
                      <div className="history-date-row">
                        <strong>{timestamp.date}</strong>
                        {timestamp.time && <span className="history-run-time">{timestamp.time}</span>}
                      </div>
                      <span className="history-simulation-time">
                        Simulated {formatHour(item.hour)} · {item.tier.replaceAll('_', ' ')} · ${item.electricity_rate}/kWh
                      </span>
                    </div>
                  </div>

                  <div className="history-costs">
                    <div>
                      <span>Normal</span>
                      <strong>${item.normal_cost}/hr</strong>
                    </div>
                    <div>
                      <span>VoltBuddy</span>
                      <strong>${item.optimized_cost}/hr</strong>
                    </div>
                    <div className="saved-value">
                      <span>Saved</span>
                      <strong>${item.savings}/hr</strong>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}
