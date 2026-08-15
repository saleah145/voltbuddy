import { NavLink } from 'react-router-dom'
import { EmptyState, PageHeader } from '../components/Shared'
import { useVoltBuddy } from '../context/VoltBuddyContext'
import { formatHour, getApplianceIcon, getApplianceType } from '../utils/format'

export default function SimulatePage() {
  const {
    hour,
    setHour,
    selectedAppliances,
    appliances,
    appliancesLoaded,
    toggleAppliance,
    simulationMessage,
    simulationLoading,
    runSimulation,
    editingApplianceId,
    editName,
    setEditName,
    editKw,
    setEditKw,
    editInterruptible,
    setEditInterruptible,
    editPriority,
    setEditPriority,
    editMessage,
    editLoading,
    startEditingAppliance,
    cancelEditingAppliance,
    updateAppliance,
    deleteAppliance,
  } = useVoltBuddy()

  const selectedNames = appliances.filter((item) => selectedAppliances.includes(item.id))

  return (
    <div className="optimize-page page-identity-optimize">
      <PageHeader
        eyebrow="OPTIMIZE"
        title="Build your VoltBuddy plan"
        description="Choose when you normally start these appliances. VoltBuddy will compare that schedule against all 24 hours and find cheaper valid windows."
      />

      <section className="optimize-stepper" aria-label="Optimization steps">
        <div className="optimize-step active">
          <span>1</span>
          <strong>Select</strong>
          <small>Choose appliances</small>
        </div>
        <div className="optimize-step">
          <span>2</span>
          <strong>Routine</strong>
          <small>Set normal timing</small>
        </div>
        <div className="optimize-step">
          <span>3</span>
          <strong>Optimize</strong>
          <small>Build your plan</small>
        </div>
      </section>

      {!appliancesLoaded ? (
        <p className="muted">Loading your appliances...</p>
      ) : appliances.length === 0 ? (
        <EmptyState
          icon="⚡"
          title="No appliances saved yet"
          action={
            <NavLink className="primary-button" to="/appliances">
              Find appliances →
            </NavLink>
          }
        >
          Add at least one appliance before running a simulation.
        </EmptyState>
      ) : (
        <>
          <section className="panel appliance-setup-panel">
            <div className="panel-heading simplified-heading">
              <div>
                <p className="eyebrow">INCLUDE IN THIS RUN</p>
                <h2>Which appliances should VoltBuddy optimize?</h2>
              </div>
              <span className="count-badge">{selectedAppliances.length} selected</span>
            </div>

            <div className="appliance-selector simplified-selector">
              {appliances.map((appliance) => {
                const selected = selectedAppliances.includes(appliance.id)
                return (
                  <div
                    key={appliance.id}
                    className={selected ? 'selector-card selected' : 'selector-card'}
                    role="checkbox"
                    aria-checked={selected}
                    tabIndex={0}
                    onClick={() => toggleAppliance(appliance.id)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        toggleAppliance(appliance.id)
                      }
                    }}
                  >
                    <input type="checkbox" checked={selected} readOnly tabIndex={-1} aria-hidden="true" />
                    <span className="selector-icon">{getApplianceIcon(appliance.id)}</span>
                    <div className="selector-content">
                      <strong>{appliance.name}</strong>
                      <p>
                        {appliance.is_estimate ? 'Estimated profile' : appliance.is_catalog ? 'Catalog profile' : getApplianceType(appliance)}
                        {appliance.category ? ` · ${appliance.category}` : ''}
                      </p>
                      <div className="appliance-card-actions" onClick={(event) => event.stopPropagation()}>
                        <button
                          type="button"
                          className="text-action-button"
                          onClick={() => startEditingAppliance(appliance)}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="text-danger-button"
                          onClick={() => deleteAppliance(appliance.id, appliance.name)}
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                    <span className="selection-check" aria-hidden="true">{selected ? '✓' : '+'}</span>
                  </div>
                )
              })}
            </div>
          </section>

          {editingApplianceId && (
            <section className="panel inline-edit-panel" aria-label="Edit appliance">
              <div className="inline-edit-heading">
                <div>
                  <p className="eyebrow">EDIT APPLIANCE</p>
                  <h3>Update this appliance</h3>
                </div>
                <button type="button" className="small-action-button" onClick={cancelEditingAppliance} disabled={editLoading}>
                  Cancel
                </button>
              </div>
              <form className="form-grid edit-appliance-form" onSubmit={updateAppliance}>
                <label>
                  <span>Appliance name</span>
                  <input type="text" maxLength={80} value={editName} onChange={(event) => setEditName(event.target.value)} />
                </label>
                <label>
                  <span>Approximate power use</span>
                  <input type="number" min="0.01" max="50" step="0.01" value={editKw} onChange={(event) => setEditKw(event.target.value)} />
                  <small className="field-help">Measured in kW.</small>
                </label>
                <label>
                  <span>How important is keeping its normal schedule?</span>
                  <select value={editPriority} onChange={(event) => setEditPriority(event.target.value)}>
                    <option value="low">Easy to move to another time</option>
                    <option value="medium">Prefer to keep its usual time</option>
                    <option value="critical">Needs to stay on schedule</option>
                  </select>
                </label>
                <label className="checkbox-row">
                  <input type="checkbox" checked={editInterruptible} onChange={(event) => setEditInterruptible(event.target.checked)} />
                  <span>
                    VoltBuddy can suggest using this at another time
                    <small>Turn this off for appliances that should not be shifted.</small>
                  </span>
                </label>
                <div className="edit-form-actions">
                  <button type="submit" className="primary-button" disabled={editLoading}>
                    {editLoading ? 'Saving...' : 'Save changes'}
                  </button>
                  <button type="button" className="secondary-button" onClick={cancelEditingAppliance} disabled={editLoading}>
                    Cancel
                  </button>
                </div>
              </form>
              {editMessage && <p className="form-message error">{editMessage}</p>}
            </section>
          )}

          <section className="panel simulator-controls">
            <div className="selected-time-row">
              <div>
                <p className="eyebrow">USUAL START TIME</p>
                <div className="selected-time">{formatHour(hour)}</div>
              </div>
              <div className="time-icon">🕒</div>
            </div>

            <input
              className="time-slider"
              type="range"
              min="0"
              max="23"
              value={hour}
              onChange={(event) => setHour(Number(event.target.value))}
            />

            <div className="time-labels">
              <span>12 AM</span>
              <span>12 PM</span>
              <span>11 PM</span>
            </div>

            <div className="simulator-selection">
              <span>Included appliances</span>
              <div className="chip-row">
                {selectedNames.map((item) => (
                  <span className="chip" key={item.id}>
                    {getApplianceIcon(item.id)} {item.name}
                  </span>
                ))}
              </div>
            </div>

            <button className="primary-button large-button" onClick={runSimulation} disabled={simulationLoading}>
              {simulationLoading ? 'Building your plan...' : 'Optimize My Schedule'}
            </button>

            {simulationMessage && <p className="form-message error">{simulationMessage}</p>}
          </section>
        </>
      )}
    </div>
  )
}
