import { EmptyState, PageHeader } from '../components/Shared'
import { useVoltBuddy } from '../context/VoltBuddyContext'
import { getCarbonLabel } from '../utils/format'

export default function RatesPage() {
  const { liveGrid, liveGridLoading, loadLiveGrid, carbonData, carbonLoading, loadCarbonData } = useVoltBuddy()

  return (
    <div className="rates-page page-identity-rates">
      <PageHeader
        eyebrow="LIVE GRID"
        title="Regional electricity conditions"
        description="See live Southern Company demand from EIA-930 alongside VoltBuddy's generation-mix carbon signal. This explains why VoltBuddy recommended certain times."
        action={
          <button
            className="secondary-button"
            onClick={() => {
              loadLiveGrid()
              loadCarbonData()
            }}
          >
            Refresh all
          </button>
        }
      />

      <section className="rates-context-strip">
        <span className="rates-context-icon">⚡</span>
        <div>
          <strong>Why this page exists</strong>
          <p>These are the price and grid conditions behind VoltBuddy’s recommendations.</p>
        </div>
      </section>

      <div className="two-column">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">GRID DEMAND</p>
              <h2>Southern Company region</h2>
            </div>
          </div>

          {liveGridLoading ? (
            <p className="muted">Loading live grid data...</p>
          ) : liveGrid?.available ? (
            <>
              <div className="large-metric">
                {Number(liveGrid.demand_mwh).toLocaleString()} <small>MWh</small>
              </div>

              <div className={`signal-pill ${liveGrid.condition}`}>
                {liveGrid.condition === 'rising' ? '↗ Rising' : liveGrid.condition === 'falling' ? '↘ Falling' : '→ Stable'}
              </div>

              <div className="metric-list">
                <div>
                  <span>Previous hour</span>
                  <strong>{liveGrid.previous_demand_mwh == null ? '—' : `${Number(liveGrid.previous_demand_mwh).toLocaleString()} MWh`}</strong>
                </div>
                <div>
                  <span>Hourly change</span>
                  <strong>
                    {liveGrid.demand_change_percent == null ? '—' : `${liveGrid.demand_change_percent > 0 ? '+' : ''}${liveGrid.demand_change_percent}%`}
                  </strong>
                </div>
                <div>
                  <span>Latest EIA period</span>
                  <strong>{liveGrid.period || '—'}</strong>
                </div>
              </div>

              <button className="secondary-button" onClick={loadLiveGrid}>
                Refresh grid data
              </button>
            </>
          ) : (
            <EmptyState icon="⚡" title="Live grid data unavailable">
              {liveGrid?.reason || 'VoltBuddy could not retrieve EIA grid data.'}
            </EmptyState>
          )}
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">GENERATION MIX</p>
              <h2>Carbon-awareness signal</h2>
            </div>
          </div>

          {carbonLoading ? (
            <p className="muted">Loading generation mix...</p>
          ) : carbonData?.available ? (
            <>
              <div className="carbon-highlight">
                <div className="large-metric">
                  {carbonData.low_carbon_share_percent}<small>% lower-carbon</small>
                </div>
                <div className={`signal-pill ${carbonData.signal}`}>{getCarbonLabel(carbonData.signal)}</div>
              </div>

              <p className="muted">{carbonData.message}</p>

              <div className="carbon-track">
                <div className="carbon-fill" style={{ width: `${carbonData.low_carbon_share_percent}%` }} />
              </div>

              <div className="carbon-labels">
                <span>Low-carbon {carbonData.low_carbon_share_percent}%</span>
                <span>Fossil {carbonData.fossil_share_percent}%</span>
              </div>

              <div className="generation-list">
                {carbonData.generation_mix
                  .filter((item) => item.generation_mwh > 0)
                  .slice(0, 5)
                  .map((item) => (
                    <div key={item.fuel_code}>
                      <span>{item.fuel_name}</span>
                      <strong>{Number(item.generation_mwh).toLocaleString()} MWh</strong>
                    </div>
                  ))}
              </div>

              <p className="method-note">Generation-mix signal only — not a direct hourly CO₂ intensity measurement.</p>

              <button className="secondary-button" onClick={loadCarbonData}>
                Refresh carbon data
              </button>
            </>
          ) : (
            <EmptyState icon="🌱" title="Carbon-awareness data unavailable">
              {carbonData?.reason || 'VoltBuddy could not retrieve generation-mix data.'}
            </EmptyState>
          )}
        </section>
      </div>
    </div>
  )
}
