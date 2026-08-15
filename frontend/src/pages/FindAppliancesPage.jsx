import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { CATALOG_PAGE_SIZE } from '../api'
import { PageHeader } from '../components/Shared'
import { useVoltBuddy } from '../context/VoltBuddyContext'
import { getCatalogVisualPath } from '../utils/format'

const API_BASE =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

  
function smartTitleCase(value) {
  if (!value) return ''

  const keepUpper = new Set(['LG', 'GE', 'HP', 'IBM', 'TCL', 'RCA', 'AOC', 'ASUS', 'MSI', 'Acer'])

  return String(value)
    .trim()
    .split(/\s+/)
    .map((word) => {
      const cleaned = word.replace(/[^A-Za-z0-9&'+.-]/g, '')
      if (keepUpper.has(cleaned.toUpperCase())) return cleaned.toUpperCase()
      if (/^[A-Z0-9]{2,4}$/.test(cleaned) && /\d/.test(cleaned)) return cleaned
      if (/^[A-Z]{2,4}$/.test(cleaned) && cleaned.length <= 3) return cleaned
      return cleaned.charAt(0).toUpperCase() + cleaned.slice(1).toLowerCase()
    })
    .join(' ')
}

function getPrimaryBrand(brand) {
  if (!brand) return 'Certified model'

  const parts = String(brand)
    .split(/[;,|]/)
    .map((part) => part.trim())
    .filter(Boolean)

  return smartTitleCase(parts[0] || 'Certified model')
}

function cleanProductType(value, category) {
  const raw = String(value || '').trim()
  if (!raw) {
    const defaults = {
      refrigerator: 'Refrigerator',
      washer: 'Washer',
      dryer: 'Dryer',
      dishwasher: 'Dishwasher',
      tv: 'Television',
      'air conditioner': 'Room Air Conditioner',
      'ev charger': 'EV Charger',
      computer: 'Computer',
      display: 'Monitor',
      'air purifier': 'Air Purifier',
      dehumidifier: 'Dehumidifier',
      freezer: 'Freezer',
    }
    return defaults[category] || 'Appliance'
  }

  const lower = raw.toLowerCase()
  if (category === 'computer' && lower === 'desktop') return 'Desktop Computer'
  if (category === 'computer' && lower.includes('notebook')) return 'Laptop'
  if (category === 'display' && !lower.includes('monitor')) return `${smartTitleCase(raw)} Monitor`
  if (category === 'air purifier' && lower.includes('air cleaner')) return 'Air Purifier'

  return smartTitleCase(raw)
}

function getCleanCatalogTitle(item) {
  const brand = getPrimaryBrand(item.brand)
  const modelName = String(item.model_name || '').trim()
  const productType = cleanProductType(item.product_type, item.category)
  const capacity = item.capacity != null && item.capacity_unit
    ? `${item.capacity} ${item.capacity_unit}`
    : ''

  // Real consumer-facing model names are preferable when present.
  if (modelName && modelName.toLowerCase() !== String(item.model_number || '').toLowerCase()) {
    const cleanedModelName = modelName
      .replace(new RegExp(`^${brand.replace(/[.*+?^${}()|[\\]\\]/g, '\\$&')}\\s+`, 'i'), '')
      .trim()

    if (cleanedModelName && cleanedModelName.length <= 90) {
      return `${brand} ${cleanedModelName}`.replace(/\s+/g, ' ').trim()
    }
  }

  return [brand, capacity, productType]
    .filter(Boolean)
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function getCatalogFallbackSymbol(category) {
  const symbols = {
    refrigerator: '▥',
    freezer: '❄',
    washer: '◉',
    dryer: '◌',
    dishwasher: '▤',
    tv: '▰',
    display: '▣',
    computer: '⌨',
    'air conditioner': '❄',
    'air purifier': '✦',
    dehumidifier: '◒',
    'ev charger': '⚡',
  }

  return symbols[category] || '⌂'
}

function CatalogProductCard({ item, appliances, addCatalogProduct, onAdded, compact = false, exactModel = false }) {
  const added = appliances.find((appliance) => appliance.catalog_product_id === item.id)

  async function handleAdd() {
    const created = await addCatalogProduct(item.id)
    if (created) onAdded(created.name)
  }

  return (
    <article className={compact ? 'catalog-product-card compact' : 'catalog-product-card'}>
      {item.image_url && item.image_verified ? (
        <div className="catalog-product-visual exact-product-visual">
          <img
            src={item.image_url}
            alt={`${getCleanCatalogTitle(item)} product photo`}
            loading="lazy"
            onError={(event) => {
              event.currentTarget.style.display = 'none'
              event.currentTarget
                .closest('.catalog-product-visual')
                ?.classList.add('catalog-product-visual-fallback')
            }}
          />
          <span className="catalog-visual-note verified-photo-note">
            {item.image_match_type === 'family' ? 'Verified family photo' : 'Verified model photo'}
          </span>
        </div>
      ) : (
        <div className="catalog-product-visual catalog-product-visual-fallback" aria-label={`${item.category || 'Appliance'} category`}>
          <div className="catalog-fallback-icon catalog-fallback-symbol" aria-hidden="true">
            {getCatalogFallbackSymbol(item.category)}
          </div>
          <span className="catalog-visual-note">No verified model photo</span>
        </div>
      )}
      <div className="catalog-product-body">
        <div className="catalog-product-topline">
          <span className="energy-star-chip">ENERGY STAR</span>
          {exactModel ? <span className="match-kind">Model match</span> : <span className="catalog-category">{item.category}</span>}
        </div>
        <div className="catalog-product-identity">
          <p className="catalog-brand">{getPrimaryBrand(item.brand)}</p>
          <h3>{getCleanCatalogTitle(item)}</h3>
          {item.model_number && <p className="catalog-model-number"><span>Model</span> {item.model_number}</p>}
        </div>
        <div className="catalog-key-details compact-key-details">
          <div className="catalog-energy-inline">
            <span>Annual energy</span>
            <strong>{item.annual_kwh != null ? Math.round(item.annual_kwh).toLocaleString() : '—'} <small>kWh/yr</small></strong>
          </div>
          {!compact && (
            <div className="catalog-spec-row">
              {item.product_type && <span>{item.product_type}</span>}
              {item.capacity != null && <span>{item.capacity} {item.capacity_unit}</span>}
            </div>
          )}
        </div>
      </div>
      <div className="catalog-product-footer">
        {!compact && (
          <div className="catalog-source-stack">
            <span className="catalog-source">EPA product data</span>
            {item.product_url && (
              <a className="catalog-product-link" href={item.product_url} target="_blank" rel="noreferrer">
                View exact model ↗
              </a>
            )}
          </div>
        )}
        <button type="button" className={added ? 'secondary-button catalog-added-button' : 'primary-button'} disabled={Boolean(added)} onClick={handleAdd}>
          {added ? '✓ In my appliances' : 'Add to my home'}
        </button>
      </div>
    </article>
  )
}

export default function FindAppliancesPage() {
  const {
    appliances,
    applianceSearch,
    setApplianceSearch,
    searchResults,
    searchLoading,
    searchMessage,
    searchApplianceCatalog,
    catalogCategory,
    setCatalogCategory,
    catalogSort,
    setCatalogSort,
    catalogOffset,
    catalogHasMore,
    addCatalogProduct,
    estimateCategory,
    setEstimateCategory,
    estimateLoading,
    addEstimatedAppliance,
    photoLoading,
    photoResult,
    photoMessage,
    identifyAppliancePhoto,
    selectedAppliances,
  } = useVoltBuddy()

  const [mode, setMode] = useState('search')
  const [justAdded, setJustAdded] = useState(null)
  const [manualForm, setManualForm] = useState({
    name: '',
    category: '',
    brand: '',
    model_number: '',
    watts: '',
    annual_kwh: '',
    typical_runtime_hours: '',
    interruptible: true,
    priority: 'medium',
    preferred_start_hour: 18,
    schedule_flexibility: 'auto',
    earliest_start_hour: 18,
    latest_finish_hour: 7,
  })
  const [manualLoading, setManualLoading] = useState(false)
  const [manualMessage, setManualMessage] = useState('')
  const [aiSearchLoading, setAiSearchLoading] = useState(false)
  const [aiSearchMessage, setAiSearchMessage] = useState('')
  const [aiSearchResult, setAiSearchResult] = useState(null)
  const [retailSearchLoading, setRetailSearchLoading] = useState(false)
  const [retailSearchMessage, setRetailSearchMessage] = useState('')
  const [selectedRetailProduct, setSelectedRetailProduct] = useState(null)
  const [selectedRetailEnergy, setSelectedRetailEnergy] = useState(null)
  const [retailEstimateLoading, setRetailEstimateLoading] = useState(false)
  const [retailEstimateMessage, setRetailEstimateMessage] = useState('')
  const [retailAddLoading, setRetailAddLoading] = useState(false)
  const [retailSearchResult, setRetailSearchResult] = useState(null)

  async function runRetailSearch(queryOverride = null) {
    const query = (queryOverride || applianceSearch).trim()

    if (!query) {
      setRetailSearchMessage('Type what you remember about the appliance first.')
      return
    }

    setRetailSearchLoading(true)
    setRetailSearchMessage('')
    setRetailSearchResult(null)
    setAiSearchMessage('')
    setSelectedRetailProduct(null)
    setSelectedRetailEnergy(null)
    setRetailEstimateMessage('')

    try {
      const response = await fetch(`${API_BASE}/retail/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          q: query,
          category: catalogCategory || null,
          limit: 8,
        }),
      })
      const data = await response.json()

      if (!response.ok) {
        setRetailSearchMessage(
          typeof data?.detail === 'string'
            ? data.detail
            : data?.detail?.message || 'Retail product search could not run.'
        )
        return
      }

      setRetailSearchResult(data)

      if (!data.products?.length) {
        setRetailSearchMessage(
          'No matching retail products were found. You can still use the ENERGY STAR catalog, Estimate, or Manual.'
        )
      }
    } catch (error) {
      console.error('Retail product search failed:', error)
      setRetailSearchMessage('Could not connect to retail product search.')
    } finally {
      setRetailSearchLoading(false)
    }
  }

  async function runAiSearch() {
    const query = applianceSearch.trim()

    if (!query) {
      setAiSearchMessage('Type what you remember about the appliance first.')
      return
    }

    setAiSearchLoading(true)
    setAiSearchMessage('')
    setAiSearchResult(null)

    try {
      const response = await fetch(`${API_BASE}/catalog/ai-search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          q: query,
          category: catalogCategory || null,
          limit: 8,
        }),
      })
      const data = await response.json()

      if (!response.ok) {
        setAiSearchMessage(
          typeof data?.detail === 'string'
            ? data.detail
            : data?.detail?.message || 'AI search could not run.'
        )
        return
      }

      setAiSearchResult(data)

      if (!data.items?.length) {
        setAiSearchMessage(
          'AI understood the description, but no matching product is in the current catalog. Try Manual or an Estimate.'
        )
      }
    } catch (error) {
      console.error('AI catalog search failed:', error)
      setAiSearchMessage('Could not connect to AI search.')
    } finally {
      setAiSearchLoading(false)
    }
  }

  async function selectRetailProduct(product) {
    setSelectedRetailProduct(product)
    setSelectedRetailEnergy(null)
    setRetailEstimateMessage('')

    setRetailEstimateLoading(true)
    try {
      const response = await fetch(`${API_BASE}/retail/estimate-energy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product,
          category: catalogCategory || product.voltbuddy_category || null,
        }),
      })
      const data = await response.json()

      if (!response.ok) {
        setRetailEstimateMessage(
          typeof data?.detail === 'string'
            ? data.detail
            : data?.detail?.message || 'Could not estimate this product’s energy use.'
        )
        return
      }

      setSelectedRetailEnergy(data)
    } catch (error) {
      console.error('Retail energy estimate failed:', error)
      setRetailEstimateMessage('Could not connect to AI energy estimation.')
    } finally {
      setRetailEstimateLoading(false)
    }
  }

  async function addSelectedRetailProduct() {
    if (!selectedRetailEnergy?.appliance_profile) return

    setRetailAddLoading(true)
    setRetailEstimateMessage('')

    try {
      const response = await fetch(`${API_BASE}/appliances`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(selectedRetailEnergy.appliance_profile),
      })
      const data = await response.json()

      if (!response.ok) {
        setRetailEstimateMessage(
          typeof data?.detail === 'string'
            ? data.detail
            : data?.detail?.message || 'Could not add this appliance.'
        )
        return
      }

      setJustAdded(data.name)
    } catch (error) {
      console.error('Retail appliance creation failed:', error)
      setRetailEstimateMessage('Could not connect to the VoltBuddy backend.')
    } finally {
      setRetailAddLoading(false)
    }
  }

  function updateManualField(field, value) {
    setManualForm((current) => ({ ...current, [field]: value }))
  }

  async function handleManualSubmit(event) {
    event.preventDefault()
    setManualMessage('')

    const watts = Number(manualForm.watts)
    const runtime = manualForm.typical_runtime_hours ? Number(manualForm.typical_runtime_hours) : null
    const annualKwh = manualForm.annual_kwh ? Number(manualForm.annual_kwh) : null

    if (!manualForm.name.trim()) {
      setManualMessage('Give this appliance a name.')
      return
    }
    if (!Number.isFinite(watts) || watts <= 0) {
      setManualMessage('Enter a valid wattage.')
      return
    }

    setManualLoading(true)
    const payload = {
      name: manualForm.name.trim(),
      kw: watts / 1000,
      interruptible: Boolean(manualForm.interruptible),
      priority: manualForm.priority,
      category: manualForm.category.trim() || null,
      brand: manualForm.brand.trim() || null,
      model_number: manualForm.model_number.trim() || null,
      annual_kwh: Number.isFinite(annualKwh) && annualKwh > 0 ? annualKwh : null,
      typical_runtime_hours: Number.isFinite(runtime) && runtime > 0 ? runtime : null,
      preferred_start_hour: Number(manualForm.preferred_start_hour),
      earliest_start_hour: manualForm.schedule_flexibility === 'window' ? Number(manualForm.earliest_start_hour) : null,
      latest_finish_hour: manualForm.schedule_flexibility === 'window' ? Number(manualForm.latest_finish_hour) : null,
      schedule_flexibility: manualForm.schedule_flexibility,
      source: 'manual user entry',
      is_estimate: false,
    }

    try {
      const response = await fetch(`${API_BASE}/appliances`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await response.json()
      if (!response.ok) {
        setManualMessage(
          typeof data?.detail === 'string'
            ? data.detail
            : data?.detail?.message || 'Could not add this appliance.'
        )
        return
      }
      setJustAdded(data.name)
    } catch (error) {
      console.error('Manual appliance creation failed:', error)
      setManualMessage('Could not connect to the VoltBuddy backend.')
    } finally {
      setManualLoading(false)
    }
  }

  const manualHourOptions = Array.from({ length: 24 }, (_, hour) => (
    <option value={hour} key={hour}>
      {hour === 0 ? '12 AM' : hour < 12 ? `${hour} AM` : hour === 12 ? '12 PM' : `${hour - 12} PM`}
    </option>
  ))

  function handleAdded(name) {
    setJustAdded(name)
  }

  async function handleAddEstimate() {
    const created = await addEstimatedAppliance()
    if (created) setJustAdded(created.name)
  }

  if (justAdded) {
    return (
      <>
        <PageHeader eyebrow="APPLIANCE ADDED" title={`${justAdded} was added`} description="What would you like to do next?" />
        <section className="panel">
          <div className="setup-next-actions" style={{ flexWrap: 'wrap', gap: '0.75rem' }}>
            <button type="button" className="secondary-button" onClick={() => setJustAdded(null)}>
              Add another appliance
            </button>
            <NavLink className="secondary-button" to="/home">
              Return to Home
            </NavLink>
            <NavLink
              className={`primary-button ${selectedAppliances.length === 0 ? 'disabled-link' : ''}`}
              to="/simulate"
              aria-disabled={selectedAppliances.length === 0}
            >
              Continue to Simulation
            </NavLink>
          </div>
        </section>
      </>
    )
  }

  return (
    <>
      <PageHeader
        eyebrow="FIND APPLIANCES"
        title="Tell VoltBuddy what you use"
        description="Search by name or model, identify an appliance from a photo, or use a simple estimate when you do not know the details."
      />

      <section className="panel smart-add-panel catalog-panel">
        <div className="panel-heading simplified-heading catalog-heading">
          <div>
            <p className="eyebrow">APPLIANCE CATALOG</p>
            <h2>Find the exact model. See its kWh.</h2>
            <p className="muted">Search by brand, size, appliance type, or model number. VoltBuddy will show verified energy data when it has it.</p>
          </div>
          <span className="catalog-source-badge">ENERGY STAR data</span>
        </div>

        <div className="smart-add-tabs" role="tablist" aria-label="Ways to find an appliance">
          <button type="button" role="tab" aria-selected={mode === 'search'} className={mode === 'search' ? 'smart-add-tab active' : 'smart-add-tab'} onClick={() => setMode('search')}>
            <span>⌕</span> Search
          </button>
          <button type="button" role="tab" aria-selected={mode === 'photo'} className={mode === 'photo' ? 'smart-add-tab active' : 'smart-add-tab'} onClick={() => setMode('photo')}>
            <span>▣</span> Photo
          </button>
          <button type="button" role="tab" aria-selected={mode === 'estimate'} className={mode === 'estimate' ? 'smart-add-tab active' : 'smart-add-tab'} onClick={() => setMode('estimate')}>
            <span>≈</span> I Don't Know My Model
          </button>
          <button type="button" role="tab" aria-selected={mode === 'manual'} className={mode === 'manual' ? 'smart-add-tab active' : 'smart-add-tab'} onClick={() => setMode('manual')}>
            <span>✎</span> Manual
          </button>
        </div>

        <div className="smart-add-active-panel">
          {mode === 'search' && (
          <div className="catalog-search-shell">
            <div className="catalog-search-primary">
              <div className="catalog-search-input-wrap">
                <span className="catalog-search-leading" aria-hidden="true">⌕</span>
                <input
                  className="catalog-search-input"
                  value={applianceSearch}
                  onChange={(event) => {
                    setApplianceSearch(event.target.value)
                    setAiSearchResult(null)
                    setAiSearchMessage('')
                    setRetailSearchResult(null)
                    setRetailSearchMessage('')
                    setSelectedRetailProduct(null)
                    setSelectedRetailEnergy(null)
                    setRetailEstimateMessage('')
                  }}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') {
                      event.preventDefault()
                      searchApplianceCatalog()
                    }
                  }}
                  placeholder="Try “Frigidaire 24 inch dishwasher” or a model number"
                />
                <button
                  type="button"
                  className="primary-button catalog-search-submit"
                  onClick={() => searchApplianceCatalog()}
                  disabled={searchLoading || !applianceSearch.trim()}
                >
                  {searchLoading ? 'Searching…' : 'Search'}
                </button>
              </div>

              <div className="catalog-search-hint-row">
                <span>Search the ENERGY STAR-backed catalog first.</span>
                <button
                  type="button"
                  className="catalog-filter-toggle"
                  onClick={(event) => {
                    const details = event.currentTarget
                      .closest('.catalog-search-shell')
                      ?.querySelector('.catalog-filter-drawer')
                    if (details) details.open = !details.open
                  }}
                >
                  Filters
                </button>
              </div>
            </div>

            <details className="catalog-filter-drawer">
              <summary>Filters</summary>
              <div className="catalog-filter-grid">
                <label>
                  <span>Category</span>
                  <select
                    value={catalogCategory}
                    onChange={(event) => setCatalogCategory(event.target.value)}
                  >
                    <option value="">All supported</option>
                    <option value="refrigerator">Refrigerators</option>
                    <option value="washer">Washers</option>
                    <option value="dryer">Dryers</option>
                    <option value="dishwasher">Dishwashers</option>
                    <option value="tv">Televisions</option>
                    <option value="computer">Computers</option>
                    <option value="display">Computer monitors</option>
                    <option value="air purifier">Air purifiers</option>
                    <option value="dehumidifier">Dehumidifiers</option>
                    <option value="freezer">Freezers</option>
                    <option value="air conditioner">Room air conditioners</option>
                    <option value="ev charger">EV chargers</option>
                  </select>
                </label>

                <label>
                  <span>Sort</span>
                  <select
                    value={catalogSort}
                    onChange={(event) => setCatalogSort(event.target.value)}
                  >
                    <option value="best">Best match</option>
                    <option value="energy_low">Lowest kWh/year</option>
                    <option value="energy_high">Highest kWh/year</option>
                    <option value="brand">Brand A–Z</option>
                  </select>
                </label>

                <button
                  type="button"
                  className="secondary-button catalog-filter-apply"
                  onClick={() => searchApplianceCatalog()}
                  disabled={searchLoading}
                >
                  Apply filters
                </button>
              </div>
            </details>

            {(searchMessage || searchResults.length === 0) && applianceSearch.trim() && !searchLoading && (
              <div className="catalog-search-fallback-card">
                <div className="catalog-search-fallback-copy">
                  <span className="eyebrow">DIDN’T FIND IT?</span>
                  <strong>Try a broader product search or let AI interpret what you meant.</strong>
                  <p>
                    Wider search looks across public product databases. AI only translates your wording into product clues.
                  </p>
                </div>

                <div className="catalog-search-fallback-actions">
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => runRetailSearch()}
                    disabled={retailSearchLoading}
                  >
                    {retailSearchLoading ? 'Searching products…' : 'Search wider products'}
                  </button>

                  <button
                    type="button"
                    className="text-action-button ai-simple-action"
                    onClick={runAiSearch}
                    disabled={aiSearchLoading}
                  >
                    {aiSearchLoading ? 'Interpreting…' : 'Try AI search →'}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {mode === 'manual' && (
          <form className="manual-appliance-form" onSubmit={handleManualSubmit}>
            <div className="manual-form-intro">
              <div>
                <p className="eyebrow">FULL CONTROL</p>
                <h3>Enter the appliance yourself</h3>
                <p className="muted">Use this when you know the specs or want to override VoltBuddy’s assumptions completely.</p>
              </div>
              <span className="manual-badge">Manual entry</span>
            </div>

            <div className="manual-form-grid">
              <label><span>Appliance name *</span><input value={manualForm.name} onChange={(e) => updateManualField('name', e.target.value)} placeholder="Gaming PC" maxLength={80} /></label>
              <label><span>Category</span><input value={manualForm.category} onChange={(e) => updateManualField('category', e.target.value)} placeholder="Computer" maxLength={80} /></label>
              <label><span>Brand</span><input value={manualForm.brand} onChange={(e) => updateManualField('brand', e.target.value)} placeholder="Custom / Dell / Samsung" maxLength={80} /></label>
              <label><span>Model number</span><input value={manualForm.model_number} onChange={(e) => updateManualField('model_number', e.target.value)} placeholder="Optional" maxLength={120} /></label>
              <label><span>Power draw (watts) *</span><input type="number" min="1" step="1" value={manualForm.watts} onChange={(e) => updateManualField('watts', e.target.value)} placeholder="500" /></label>
              <label><span>Annual energy (kWh/year)</span><input type="number" min="0" step="0.1" value={manualForm.annual_kwh} onChange={(e) => updateManualField('annual_kwh', e.target.value)} placeholder="Optional" /></label>
              <label><span>Typical runtime (hours)</span><input type="number" min="0.1" max="24" step="0.1" value={manualForm.typical_runtime_hours} onChange={(e) => updateManualField('typical_runtime_hours', e.target.value)} placeholder="3" /></label>
              <label><span>Priority</span><select value={manualForm.priority} onChange={(e) => updateManualField('priority', e.target.value)}><option value="low">Low</option><option value="medium">Medium</option><option value="critical">Critical</option></select></label>
              <label><span>Can VoltBuddy shift it?</span><select value={manualForm.interruptible ? 'yes' : 'no'} onChange={(e) => updateManualField('interruptible', e.target.value === 'yes')}><option value="yes">Yes</option><option value="no">No</option></select></label>
              <label><span>Usually starts</span><select value={manualForm.preferred_start_hour} onChange={(e) => updateManualField('preferred_start_hour', Number(e.target.value))}>{manualHourOptions}</select></label>
              <label><span>Scheduling flexibility</span><select value={manualForm.schedule_flexibility} onChange={(e) => updateManualField('schedule_flexibility', e.target.value)}><option value="auto">Use VoltBuddy’s normal rules</option><option value="fixed">Fixed time</option><option value="window">Within a time window</option><option value="anytime">Anytime today</option></select></label>
              {manualForm.schedule_flexibility === 'window' && (
                <>
                  <label><span>Earliest start</span><select value={manualForm.earliest_start_hour} onChange={(e) => updateManualField('earliest_start_hour', Number(e.target.value))}>{manualHourOptions}</select></label>
                  <label><span>Finish by</span><select value={manualForm.latest_finish_hour} onChange={(e) => updateManualField('latest_finish_hour', Number(e.target.value))}>{manualHourOptions}</select></label>
                </>
              )}
            </div>

            <div className="manual-form-footer">
              <div><strong>You control these values.</strong><small>VoltBuddy keeps manual specs separate from catalog estimates.</small></div>
              <button type="submit" className="primary-button" disabled={manualLoading}>{manualLoading ? 'Adding…' : 'Add manual appliance'}</button>
            </div>

            {manualMessage && <p className="form-message error">{manualMessage}</p>}
          </form>
        )}

        {mode === 'search' && searchMessage && <p className="form-message">{searchMessage}</p>}
        {mode === 'photo' && photoMessage && <p className="form-message error">{photoMessage}</p>}

        {mode === 'search' && retailSearchMessage && (
          <p className="form-message">{retailSearchMessage}</p>
        )}

        {mode === 'search' && retailSearchResult?.products?.length > 0 && (
          <section className="wider-results-view selectable-wider-results">
            {aiSearchResult?.interpretation?.clean_query && (
              <div className="wider-ai-context">
                <span>AI interpreted your search as</span>
                <strong>{aiSearchResult.interpretation.clean_query}</strong>
              </div>
            )}

            <div className="wider-results-header">
              <div>
                <p className="eyebrow">WIDER PRODUCT SEARCH</p>
                <h3>Choose the product that looks like yours</h3>
                <p className="muted">
                  Product identity comes from public UPC databases. Select one and VoltBuddy will estimate its annual energy use if there is no exact ENERGY STAR match.
                </p>
              </div>

              {retailSearchResult.exact_energy_matches > 0 && (
                <span className="energy-legend exact">
                  {retailSearchResult.exact_energy_matches} ENERGY STAR match{retailSearchResult.exact_energy_matches === 1 ? '' : 'es'}
                </span>
              )}
            </div>

            <div className="wider-product-list">
              {retailSearchResult.products.map((product) => {
                const exactEnergy = product.energy
                const isSelected =
                  selectedRetailProduct?.sku === product.sku &&
                  selectedRetailProduct?.retail_source === product.retail_source

                return (
                  <article
                    className={isSelected ? 'wider-product-row selected' : 'wider-product-row'}
                    key={`retail-${product.retail_source}-${product.sku}`}
                  >
                    <div className="wider-product-thumb">
                      {product.image_url ? (
                        <img src={product.image_url} alt="" loading="lazy" />
                      ) : (
                        <span aria-hidden="true">⌂</span>
                      )}
                    </div>

                    <div className="wider-product-main">
                      <div className="wider-product-meta">
                        <span>{product.brand || 'Product'}</span>
                        <span className="dot-separator">·</span>
                        <span>{product.retail_source}</span>
                      </div>

                      <h4>{product.name}</h4>

                      <div className="wider-product-submeta">
                        {product.model_number && <span>Model {product.model_number}</span>}
                        {product.upc && <span>UPC {product.upc}</span>}
                      </div>
                    </div>

                    <div className="wider-energy-column">
                      {exactEnergy?.annual_kwh != null ? (
                        <div className="wider-energy-status exact">
                          <span>ENERGY STAR</span>
                          <strong>{Math.round(exactEnergy.annual_kwh).toLocaleString()} kWh/yr</strong>
                          <small>Verified match available</small>
                        </div>
                      ) : (
                        <div className="wider-energy-status ai-ready">
                          <span>Annual energy</span>
                          <strong>AI estimate available</strong>
                          <small>Select this product to calculate it</small>
                        </div>
                      )}
                    </div>

                    <div className="wider-product-actions">
                      <button
                        type="button"
                        className={isSelected ? 'primary-button wider-select-button selected' : 'secondary-button wider-select-button'}
                        onClick={() => selectRetailProduct(product)}
                        disabled={retailEstimateLoading && isSelected}
                      >
                        {retailEstimateLoading && isSelected
                          ? 'Estimating…'
                          : isSelected
                            ? '✓ Selected'
                            : 'Select'}
                      </button>

                      {product.product_url && (
                        <a
                          className="text-action-button"
                          href={product.product_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Source ↗
                        </a>
                      )}
                    </div>
                  </article>
                )
              })}
            </div>

            {selectedRetailProduct && (
              <div className="selected-retail-panel">
                <div className="selected-retail-heading">
                  <div>
                    <span className="eyebrow">SELECTED PRODUCT</span>
                    <h3>{selectedRetailProduct.name}</h3>
                    <p>
                      {[selectedRetailProduct.brand, selectedRetailProduct.model_number]
                        .filter(Boolean)
                        .join(' · ')}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="text-action-button"
                    onClick={() => {
                      setSelectedRetailProduct(null)
                      setSelectedRetailEnergy(null)
                      setRetailEstimateMessage('')
                    }}
                  >
                    Change
                  </button>
                </div>

                {retailEstimateLoading && (
                  <div className="selected-energy-loading">
                    <strong>Estimating annual energy…</strong>
                    <span>VoltBuddy is using this product’s identity and available ENERGY STAR context.</span>
                  </div>
                )}

                {retailEstimateMessage && (
                  <p className="form-message">{retailEstimateMessage}</p>
                )}

                {selectedRetailEnergy && (
                  <div className="selected-energy-result">
                    <div className={selectedRetailEnergy.status === 'verified' ? 'selected-energy-number verified' : 'selected-energy-number ai-estimated'}>
                      <span>
                        {selectedRetailEnergy.status === 'verified'
                          ? 'Verified annual energy'
                          : 'AI-estimated annual energy'}
                      </span>
                      <strong>
                        {Math.round(selectedRetailEnergy.annual_kwh).toLocaleString()}
                        <small> kWh/yr</small>
                      </strong>
                      <em>
                        {selectedRetailEnergy.status === 'verified'
                          ? 'ENERGY STAR exact match'
                          : `${selectedRetailEnergy.confidence} confidence · estimate`}
                      </em>
                    </div>

                    <div className="selected-energy-explanation">
                      <strong>
                        {selectedRetailEnergy.status === 'verified'
                          ? 'Verified source'
                          : 'How AI estimated it'}
                      </strong>
                      <p>{selectedRetailEnergy.basis}</p>

                      {selectedRetailEnergy.status === 'ai_estimated' &&
                        selectedRetailEnergy.reference_context?.comparable_count > 0 && (
                          <span>
                            Reference context: {selectedRetailEnergy.reference_context.comparable_count} comparable ENERGY STAR models
                            {selectedRetailEnergy.reference_context.comparable_range_low_kwh != null &&
                              selectedRetailEnergy.reference_context.comparable_range_high_kwh != null
                              ? ` · ${Math.round(selectedRetailEnergy.reference_context.comparable_range_low_kwh)}–${Math.round(selectedRetailEnergy.reference_context.comparable_range_high_kwh)} kWh/yr`
                              : ''}
                          </span>
                        )}
                    </div>

                    <button
                      type="button"
                      className="primary-button selected-retail-add"
                      onClick={addSelectedRetailProduct}
                      disabled={retailAddLoading}
                    >
                      {retailAddLoading ? 'Adding…' : 'Add this appliance'}
                    </button>
                  </div>
                )}
              </div>
            )}

            <div className="wider-results-note">
              <strong>Verified and estimated energy stay separate.</strong>
              <span>
                ENERGY STAR values are labeled verified. Anything calculated by AI is labeled AI-estimated.
              </span>
            </div>
          </section>
        )}

        {mode === 'search' && aiSearchMessage && (
          <p className="form-message">{aiSearchMessage}</p>
        )}

        {mode === 'search' && aiSearchResult && !retailSearchResult?.products?.length && (
          <section className="ai-search-results">
            <div className="ai-interpretation-card">
              <div>
                <span className="ai-search-kicker">AI INTERPRETATION</span>
                <h3>{aiSearchResult.interpretation?.clean_query || applianceSearch}</h3>
                <p>{aiSearchResult.interpretation?.interpretation}</p>
              </div>

              <div className="ai-clue-row">
                {aiSearchResult.interpretation?.category && (
                  <span>{aiSearchResult.interpretation.category}</span>
                )}
                {aiSearchResult.interpretation?.brand && (
                  <span>{aiSearchResult.interpretation.brand}</span>
                )}
                {aiSearchResult.interpretation?.model_number && (
                  <span>Model {aiSearchResult.interpretation.model_number}</span>
                )}
                {aiSearchResult.interpretation?.capacity != null && (
                  <span>
                    {aiSearchResult.interpretation.capacity}
                    {aiSearchResult.interpretation.capacity_unit
                      ? ` ${aiSearchResult.interpretation.capacity_unit}`
                      : ''}
                  </span>
                )}
              </div>

              <small className="ai-source-note">
                AI interpreted the request · Energy and model data below come from the catalog
              </small>

              <button
                type="button"
                className="text-action-button ai-to-retail-button"
                onClick={() =>
                  runRetailSearch(
                    aiSearchResult.interpretation?.clean_query || applianceSearch
                  )
                }
                disabled={retailSearchLoading}
              >
                Search real products using this interpretation →
              </button>
            </div>

            {aiSearchResult.items?.length > 0 && (
              <div className="catalog-results-block ai-catalog-results">
                <div className="catalog-results-meta">
                  <strong>AI-assisted catalog matches</strong>
                  <span>{aiSearchResult.items.length} result{aiSearchResult.items.length === 1 ? '' : 's'}</span>
                </div>

                <div className="catalog-product-grid">
                  {aiSearchResult.items.map((item) => (
                    <CatalogProductCard
                      key={`ai-${item.id}`}
                      item={item}
                      appliances={appliances}
                      addCatalogProduct={addCatalogProduct}
                      onAdded={handleAdded}
                    />
                  ))}
                </div>
              </div>
            )}
          </section>
        )}

        {mode === 'search' && searchResults.length > 0 && (
          <div className="catalog-results-block">
            <div className="catalog-results-meta">
              <strong>Matching models</strong>
              <span>
                Showing {catalogOffset + 1}–{catalogOffset + searchResults.length}
                {catalogHasMore ? '+' : ''}
              </span>
            </div>
            <div className="catalog-product-grid">
              {searchResults.map((item) => (
                <CatalogProductCard key={item.id} item={item} appliances={appliances} addCatalogProduct={addCatalogProduct} onAdded={handleAdded} />
              ))}
            </div>

            <div className="catalog-pagination" aria-label="Catalog result pages">
              <button
                type="button"
                className="secondary-button"
                disabled={catalogOffset === 0 || searchLoading}
                onClick={() => searchApplianceCatalog(catalogOffset - CATALOG_PAGE_SIZE)}
              >
                ← Previous
              </button>
              <span>
                {catalogOffset + 1}–{catalogOffset + searchResults.length}
              </span>
              <button
                type="button"
                className="secondary-button"
                disabled={!catalogHasMore || searchLoading}
                onClick={() => searchApplianceCatalog(catalogOffset + CATALOG_PAGE_SIZE)}
              >
                Next →
              </button>
            </div>
          </div>
        )}

        {mode === 'photo' && photoResult && (
          <div className="photo-result-card catalog-photo-result">
            <div>
              <p className="eyebrow">PHOTO SEARCH</p>
              <h3>{photoResult.identification?.description || photoResult.identification?.category || 'Appliance identified'}</h3>
              <p className="muted">
                {[photoResult.identification?.brand, photoResult.identification?.model_number, photoResult.identification?.category].filter(Boolean).join(' · ')}
              </p>
              <span className="confidence-chip">{photoResult.identification?.confidence || 'low'} confidence</span>
            </div>

            {photoResult.matches?.length > 0 ? (
              <div className="catalog-product-grid photo-match-grid">
                {photoResult.matches.map((item) => {
                  const exactModel =
                    photoResult.identification?.model_number &&
                    item.model_number?.toLowerCase() === photoResult.identification.model_number?.toLowerCase()
                  return (
                    <CatalogProductCard
                      key={item.id}
                      item={item}
                      appliances={appliances}
                      addCatalogProduct={addCatalogProduct}
                      onAdded={handleAdded}
                      compact
                      exactModel={exactModel}
                    />
                  )
                })}
              </div>
            ) : photoResult.estimate ? (
              <button
                type="button"
                className="secondary-button"
                onClick={async () => {
                  const created = await addEstimatedAppliance(photoResult.estimate.category)
                  if (created) setJustAdded(created.name)
                }}
              >
                No exact catalog match — use a {photoResult.estimate.category} estimate
              </button>
            ) : (
              <p className="muted">No matching catalog product was found yet.</p>
            )}
          </div>
        )}
        </div>
      </section>
    </>
  )
}
