import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { EmptyState, PageHeader, StatCard } from '../components/Shared'
import { useVoltBuddy } from '../context/VoltBuddyContext'
import { formatHour } from '../utils/format'

export default function InsightsPage() {
  const { hour, history, savingsChartData, electricityRates, totalHistorySavings, averageSavings } = useVoltBuddy()

  return (
    <div className="insights-page page-identity-insights">
      <PageHeader
        eyebrow="INSIGHTS"
        title="Prices and savings"
        description="Understand the daily tariff pattern and how VoltBuddy's estimated savings change across your recent simulations."
      />

      <section className="panel chart-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">PRICE CURVE</p>
            <h2>Electricity prices throughout the day</h2>
          </div>
          <span className="count-badge">Selected: {formatHour(hour)}</span>
        </div>

        <div className="chart-wrapper">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={electricityRates}>
              <XAxis dataKey="label" interval={3} tickLine={false} axisLine={false} />
              <YAxis tickFormatter={(value) => `$${value}`} tickLine={false} axisLine={false} />
              <Tooltip formatter={(value) => [`$${value}/kWh`, 'Rate']} />
              <Bar dataKey="rate" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="legend-row">
          <span>🌙 Super off-peak: $0.021859/kWh</span>
          <span>🌿 Off-peak: $0.101676/kWh</span>
          <span>⚡ On-peak: $0.297868/kWh</span>
        </div>
      </section>

      <section className="panel chart-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">SAVINGS TREND</p>
            <h2>Savings over time</h2>
          </div>
        </div>

        {history.length === 0 ? (
          <EmptyState icon="📈" title="No savings data yet">
            Run a few simulations and your savings trend will appear here.
          </EmptyState>
        ) : (
          <>
            <div className="stats-grid compact">
              <StatCard label="Total" value={`$${totalHistorySavings.toFixed(2)}`} />
              <StatCard label="Average" value={`$${averageSavings.toFixed(2)}`} />
              <StatCard label="Runs" value={history.length} />
            </div>

            <div className="chart-wrapper">
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={savingsChartData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="simulation" tickLine={false} axisLine={false} />
                  <YAxis tickFormatter={(value) => `$${value}`} tickLine={false} axisLine={false} />
                  <Tooltip
                    formatter={(value) => [`$${value}/hr`, 'Estimated savings']}
                    labelFormatter={(label, payload) => {
                      const item = payload?.[0]?.payload
                      return item ? `${label} · ${item.time}` : label
                    }}
                  />
                  <Line type="monotone" dataKey="savings" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
      </section>
    </div>
  )
}
