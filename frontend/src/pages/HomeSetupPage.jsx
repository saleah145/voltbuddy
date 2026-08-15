import { NavLink } from 'react-router-dom'
import { EmptyState, PageHeader } from '../components/Shared'
import { useVoltBuddy } from '../context/VoltBuddyContext'
import { getApplianceIcon, getApplianceType } from '../utils/format'

export default function HomeSetupPage() {
  const {
    appliances,
    selectedAppliances,
    toggleAppliance,
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
    homes,
    homeName,
    setHomeName,
    homeMessage,
    homeSaving,
    loadingHomeId,
    activeHomeId,
    activeHomeName,
    saveHome,
    loadSavedHome,
    deleteSavedHome,
    customName,
    setCustomName,
    customKw,
    setCustomKw,
    customInterruptible,
    setCustomInterruptible,
    customPriority,
    setCustomPriority,
    customMessage,
    customLoading,
    createCustomAppliance,
    appliancesLoaded,
  } = useVoltBuddy()

  return (
    <div className="home-page page-identity-home">
      <PageHeader
        eyebrow="YOUR HOME"
        title={activeHomeName ? `Managing ${activeHomeName}` : 'Set up your home'}
        description="Name your home, review saved appliances, and manage the setups you use most."
      />

      <section className="home-workspace-intro">
        <div>
          <span className="workspace-step">HOME PROFILE</span>
          <h2>Manage your space and what belongs in it.</h2>
          <p>Keep home setup separate from optimization. This page is only for your household and saved appliances.</p>
        </div>
        <NavLink className="primary-button" to="/appliances">Add appliances →</NavLink>
      </section>

      <section className="panel">
        <div className="panel-heading simplified-heading">
          <div>
            <p className="eyebrow">HOME INFORMATION</p>
            <h2>Name &amp; save this setup</h2>
            <p className="muted">Give this home a name so you can reload it later.</p>
          </div>
        </div>

        <form className="save-home-row" onSubmit={saveHome}>
          <input
            type="text"
            placeholder="My Apartment"
            maxLength={80}
            value={homeName}
            onChange={(event) => setHomeName(event.target.value)}
          />
          <button type="submit" className="secondary-button" disabled={homeSaving}>
            {homeSaving ? 'Saving...' : 'Save current setup'}
          </button>
        </form>
        {homeMessage && <p className="form-message">{homeMessage}</p>}

        {homes.length > 0 ? (
          <div className="saved-home-list">
            {homes.map((home) => (
              <div className="saved-home-item" key={home.id}>
                <span>
                  <strong>
                    {home.name}
                    {activeHomeId === home.id ? ' (current)' : ''}
                  </strong>
                  <small>{home.appliances.length} appliance{home.appliances.length === 1 ? '' : 's'}</small>
                </span>
                <div className="saved-home-actions">
                  <button
                    type="button"
                    className="small-action-button"
                    onClick={() => loadSavedHome(home.id)}
                    disabled={loadingHomeId !== null}
                  >
                    {loadingHomeId === home.id ? 'Loading...' : 'Load'}
                  </button>
                  <button
                    type="button"
                    className="small-action-button danger"
                    onClick={() => deleteSavedHome(home.id, home.name)}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="setup-note">No saved homes yet. Save your first setup above.</p>
        )}
      </section>

      <section className="panel appliance-setup-panel">
        <div className="panel-heading simplified-heading">
          <div>
            <p className="eyebrow">SAVED APPLIANCES</p>
            <h2>What VoltBuddy knows about your home</h2>
            <p className="muted">Tap an appliance to include or exclude it from your next simulation.</p>
          </div>
          <span className="count-badge">{selectedAppliances.length} selected</span>
        </div>

        {!appliancesLoaded ? (
          <p className="muted">Loading your saved appliances...</p>
        ) : appliances.length === 0 ? (
          <EmptyState
            icon="⚡"
            title="No appliances yet"
            action={
              <NavLink className="primary-button" to="/appliances">
                Find your first appliance →
              </NavLink>
            }
          >
            Search the catalog, use a photo, or add an estimate to get started.
          </EmptyState>
        ) : (
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
        )}

        {editingApplianceId && (
          <section className="inline-edit-panel" aria-label="Edit appliance">
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

        <div className="setup-next-row">
          <div>
            <strong>
              {selectedAppliances.length === 0
                ? 'Choose at least one appliance to continue'
                : `${selectedAppliances.length} appliance${selectedAppliances.length === 1 ? '' : 's'} ready`}
            </strong>
            <span>Add more anytime, or head straight to optimizing.</span>
          </div>
          <div className="setup-next-actions">
            <NavLink className="secondary-button" to="/appliances">
              Add appliance
            </NavLink>
            <NavLink
              className={`primary-button ${selectedAppliances.length === 0 ? 'disabled-link' : ''}`}
              to={selectedAppliances.length === 0 ? '/home' : '/simulate'}
              aria-disabled={selectedAppliances.length === 0}
            >
              Continue
            </NavLink>
          </div>
        </div>
      </section>

      <section className="setup-options" aria-label="Optional home setup tools">
        <details className="setup-disclosure">
          <summary>
            <span>
              <strong>Add manually</strong>
              <small>Use this only when search, photo, and estimates are not enough</small>
            </span>
            <span className="disclosure-plus">+</span>
          </summary>
          <div className="disclosure-content">
            <form className="form-grid simple-manual-form" onSubmit={createCustomAppliance}>
              <label>
                <span>What appliance is it?</span>
                <input type="text" placeholder="Dishwasher" maxLength={80} value={customName} onChange={(event) => setCustomName(event.target.value)} />
              </label>
              <label>
                <span>Approximate power use</span>
                <input type="number" min="0.01" max="50" step="0.01" placeholder="1.8 kW" value={customKw} onChange={(event) => setCustomKw(event.target.value)} />
              </label>
              <label>
                <span>How important is keeping its normal schedule?</span>
                <select value={customPriority} onChange={(event) => setCustomPriority(event.target.value)}>
                  <option value="low">Easy to move to another time</option>
                  <option value="medium">Prefer to keep its usual time</option>
                  <option value="critical">Needs to stay on schedule</option>
                </select>
              </label>
              <label className="checkbox-row">
                <input type="checkbox" checked={customInterruptible} onChange={(event) => setCustomInterruptible(event.target.checked)} />
                <span>VoltBuddy can suggest using this at another time</span>
              </label>
              <button type="submit" className="primary-button" disabled={customLoading}>
                {customLoading ? 'Adding...' : 'Add appliance'}
              </button>
            </form>
            {customMessage && <p className="form-message">{customMessage}</p>}
          </div>
        </details>
      </section>
    </div>
  )
}
