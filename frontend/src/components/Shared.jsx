import { getTimelineSegments } from '../utils/format'

export function PageHeader({ eyebrow, title, description, action }) {
  return (
    <div className="page-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="page-description">{description}</p>
      </div>
      {action}
    </div>
  )
}

export function EmptyState({ icon, title, children, action }) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">{icon}</div>
      <h3>{title}</h3>
      <p>{children}</p>
      {action}
    </div>
  )
}

export function StatCard({ label, value, note }) {
  return (
    <div className="stat-card">
      <span>{label}</span>
      <strong>{value}</strong>
      {note && <small>{note}</small>}
    </div>
  )
}

export function ScheduleTimelineBar({ startHour, runtimeHours, variant }) {
  const segments = getTimelineSegments(startHour, runtimeHours)

  return (
    <div className="schedule-timeline-track">
      <div className="schedule-timeline-grid" aria-hidden="true">
        {Array.from({ length: 24 }, (_, index) => (
          <span key={index} />
        ))}
      </div>

      {segments.map((segment, index) => (
        <span
          className={`schedule-timeline-block ${variant}`}
          key={`${variant}-${index}`}
          style={{
            left: `${segment.left}%`,
            width: `${Math.max(segment.width, 0.8)}%`,
          }}
        />
      ))}
    </div>
  )
}
