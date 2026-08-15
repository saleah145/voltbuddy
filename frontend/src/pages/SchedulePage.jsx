import { NavLink } from 'react-router-dom'
import { EmptyState, PageHeader, ScheduleTimelineBar } from '../components/Shared'
import { useVoltBuddy } from '../context/VoltBuddyContext'
import { formatScheduleWindow } from '../utils/format'

export default function SchedulePage() {
  const { simulation } = useVoltBuddy()

  if (!simulation?.daily_plan) {
    return (
      <div className="schedule-page page-identity-schedule">
        <PageHeader eyebrow="SCHEDULE" title="Full 24-hour schedule" description="Run a simulation to see your detailed schedule here." />
        <EmptyState
          icon="🗓"
          title="No schedule yet"
          action={
            <NavLink className="primary-button" to="/simulate">
              Run a simulation →
            </NavLink>
          }
        >
          Once VoltBuddy builds a 24-hour plan, the full timeline for each appliance will show up here.
        </EmptyState>
      </div>
    )
  }

  const { schedule } = simulation.daily_plan

  return (
    <div className="schedule-page page-identity-schedule">
      <PageHeader
        eyebrow="SCHEDULE"
        title="Original vs VoltBuddy, hour by hour"
        description="Each appliance's original and optimized window, including runs that cross midnight."
        action={<NavLink className="secondary-button" to="/results">Back to results</NavLink>}
      />

      <section className="schedule-canvas">
        <div className="schedule-timeline" aria-label="Original and optimized 24-hour appliance schedule">
          <div className="schedule-timeline-axis">
            <span>12 AM</span>
            <span>6 AM</span>
            <span>12 PM</span>
            <span>6 PM</span>
            <span>12 AM</span>
          </div>

          <div className="schedule-timeline-rows">
            {schedule.map((item) => (
              <div className="schedule-timeline-appliance" key={`timeline-${item.id}`}>
                <div className="schedule-timeline-heading">
                  <div>
                    <strong>{item.name}</strong>
                    <span>{item.runtime_hours} hr{item.runtime_hours === 1 ? '' : 's'}</span>
                  </div>
                  <span className={`schedule-status ${item.shifted ? 'shifted' : 'unchanged'}`}>
                    {item.shifted ? 'Shifted' : 'Unchanged'}
                  </span>
                </div>

                <div className="schedule-timeline-line">
                  <span className="schedule-timeline-label">Original</span>
                  <ScheduleTimelineBar startHour={item.original_start_hour} runtimeHours={item.runtime_hours} variant="original" />
                  <small>{formatScheduleWindow(item.original_start_hour, item.runtime_hours)}</small>
                </div>

                <div className="schedule-timeline-line">
                  <span className="schedule-timeline-label">VoltBuddy</span>
                  <ScheduleTimelineBar
                    startHour={item.optimized_start_hour}
                    runtimeHours={item.runtime_hours}
                    variant={item.shifted ? 'optimized shifted' : 'optimized unchanged'}
                  />
                  <small>{formatScheduleWindow(item.optimized_start_hour, item.runtime_hours)}</small>
                </div>
              </div>
            ))}
          </div>

          <div className="schedule-timeline-legend">
            <span><i className="original" />Original schedule</span>
            <span><i className="optimized" />VoltBuddy schedule</span>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">DETAILED SAVINGS</p>
            <h2>Per-appliance breakdown</h2>
          </div>
        </div>

        <div className="schedule-list">
          {schedule.map((item) => (
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

              <div className="schedule-comparison">
                <div>
                  <span>Original</span>
                  <strong>{formatScheduleWindow(item.original_start_hour, item.runtime_hours)}</strong>
                  <small>${item.original_cost.toFixed(2)}</small>
                </div>
                <div className="schedule-arrow">→</div>
                <div>
                  <span>VoltBuddy</span>
                  <strong>{formatScheduleWindow(item.optimized_start_hour, item.runtime_hours)}</strong>
                  <small>${item.optimized_cost.toFixed(2)}</small>
                </div>
              </div>

              <p>{item.reason}</p>

              {item.savings > 0 && (
                <div className="schedule-savings">
                  <span>Estimated savings</span>
                  <strong>${item.savings.toFixed(2)}/day</strong>
                </div>
              )}

              {item.runtime_source === 'estimated' && (
                <small className="runtime-estimate-note">Runtime currently uses a VoltBuddy estimate.</small>
              )}
            </div>
          ))}
        </div>

        <p className="runtime-plan-note">{simulation.daily_plan.runtime_note}</p>
      </section>
    </div>
  )
}
