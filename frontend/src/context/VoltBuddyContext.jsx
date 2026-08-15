import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { API_BASE, CATALOG_PAGE_SIZE, getApiErrorMessage } from '../api'
import { ELECTRICITY_RATES, formatHour } from '../utils/format'

const VoltBuddyContext = createContext(null)

export function useVoltBuddy() {
  const context = useContext(VoltBuddyContext)
  if (!context) {
    throw new Error('useVoltBuddy must be used within a VoltBuddyProvider')
  }
  return context
}

export function VoltBuddyProvider({ children }) {
  const navigate = useNavigate()

  const [hour, setHour] = useState(12)
  const [appliances, setAppliances] = useState([])
  const [selectedAppliances, setSelectedAppliances] = useState([
    'ev_charger',
    'gaming_pc',
    'refrigerator',
  ])

  const [simulation, setSimulation] = useState(null)
  const [simulationMessage, setSimulationMessage] = useState('')
  const [simulationLoading, setSimulationLoading] = useState(false)
  const [history, setHistory] = useState([])

  const [customName, setCustomName] = useState('')
  const [customKw, setCustomKw] = useState('')
  const [customInterruptible, setCustomInterruptible] = useState(true)
  const [customPriority, setCustomPriority] = useState('low')
  const [customMessage, setCustomMessage] = useState('')
  const [customLoading, setCustomLoading] = useState(false)

  const [editingApplianceId, setEditingApplianceId] = useState(null)
  const [editName, setEditName] = useState('')
  const [editKw, setEditKw] = useState('')
  const [editInterruptible, setEditInterruptible] = useState(true)
  const [editPriority, setEditPriority] = useState('low')
  const [editMessage, setEditMessage] = useState('')
  const [editLoading, setEditLoading] = useState(false)

  const [applianceSearch, setApplianceSearch] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchMessage, setSearchMessage] = useState('')
  const [catalogCategory, setCatalogCategory] = useState('')
  const [catalogSort, setCatalogSort] = useState('relevance')
  const [catalogTotal, setCatalogTotal] = useState(0)
  const [catalogHasMore, setCatalogHasMore] = useState(false)
  const [catalogOffset, setCatalogOffset] = useState(0)
  const [estimateCategory, setEstimateCategory] = useState('refrigerator')
  const [estimateLoading, setEstimateLoading] = useState(false)
  const [photoLoading, setPhotoLoading] = useState(false)
  const [photoResult, setPhotoResult] = useState(null)
  const [photoMessage, setPhotoMessage] = useState('')

  const [homes, setHomes] = useState([])
  const [homeName, setHomeName] = useState('')
  const [homeMessage, setHomeMessage] = useState('')
  const [homeSaving, setHomeSaving] = useState(false)
  const [loadingHomeId, setLoadingHomeId] = useState(null)
  const [activeHomeId, setActiveHomeId] = useState(null)
  const [activeHomeName, setActiveHomeName] = useState('')

  const [appliancesLoaded, setAppliancesLoaded] = useState(false)
  const [homesLoaded, setHomesLoaded] = useState(false)
  const [backendError, setBackendError] = useState(false)

  const [liveGrid, setLiveGrid] = useState(null)
  const [liveGridLoading, setLiveGridLoading] = useState(true)

  const [carbonData, setCarbonData] = useState(null)
  const [carbonLoading, setCarbonLoading] = useState(true)

  const totalHistorySavings = useMemo(
    () => history.reduce((total, item) => total + Number(item.savings || 0), 0),
    [history]
  )

  const averageSavings =
    history.length > 0 ? totalHistorySavings / history.length : 0

  const savingsChartData = useMemo(
    () =>
      [...history]
        .reverse()
        .map((item, index) => ({
          simulation: `Run ${index + 1}`,
          time: formatHour(item.hour),
          savings: item.savings,
        })),
    [history]
  )

  const electricityRates = ELECTRICITY_RATES

  async function loadHistory() {
    try {
      const response = await fetch(`${API_BASE}/simulations`)
      const data = await response.json()
      setHistory(data)
    } catch (error) {
      console.error('Failed to load simulation history:', error)
    }
  }

  async function loadAppliances() {
    try {
      const response = await fetch(`${API_BASE}/appliances`)
      const data = await response.json()
      setAppliances(data)
      setBackendError(false)
    } catch (error) {
      console.error('Failed to load appliances:', error)
      setBackendError(true)
    } finally {
      setAppliancesLoaded(true)
    }
  }

  async function loadHomes() {
    try {
      const response = await fetch(`${API_BASE}/homes`)
      const data = await response.json()
      setHomes(data)
      setBackendError(false)
    } catch (error) {
      console.error('Failed to load saved homes:', error)
      setBackendError(true)
    } finally {
      setHomesLoaded(true)
    }
  }

  async function loadLiveGrid() {
    setLiveGridLoading(true)

    try {
      const response = await fetch(`${API_BASE}/grid/live`)
      const data = await response.json()
      setLiveGrid(data)
    } catch (error) {
      console.error('Failed to load live grid data:', error)
      setLiveGrid({
        available: false,
        reason: 'Could not connect to live grid data.',
      })
    } finally {
      setLiveGridLoading(false)
    }
  }

  async function loadCarbonData() {
    setCarbonLoading(true)

    try {
      const response = await fetch(`${API_BASE}/grid/carbon`)
      const data = await response.json()
      setCarbonData(data)
    } catch (error) {
      console.error('Failed to load carbon-awareness data:', error)
      setCarbonData({
        available: false,
        reason: 'Could not connect to carbon-awareness data.',
      })
    } finally {
      setCarbonLoading(false)
    }
  }

  useEffect(() => {
    loadAppliances()
    loadHistory()
    loadHomes()
    loadLiveGrid()
    loadCarbonData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function toggleAppliance(id) {
    setSelectedAppliances((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id]
    )
  }

  async function createCustomAppliance(event) {
    event.preventDefault()
    setCustomMessage('')

    const cleanedName = customName.trim()
    const numericKw = Number(customKw)

    if (!cleanedName) {
      setCustomMessage('Enter an appliance name.')
      return
    }

    if (cleanedName.length > 80) {
      setCustomMessage('Appliance name must be 80 characters or fewer.')
      return
    }

    if (!customKw || Number.isNaN(numericKw)) {
      setCustomMessage('Enter a valid power usage.')
      return
    }

    if (numericKw <= 0 || numericKw > 50) {
      setCustomMessage('Power usage must be greater than 0 and no more than 50 kW.')
      return
    }

    setCustomLoading(true)

    try {
      const response = await fetch(`${API_BASE}/appliances`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: cleanedName,
          kw: numericKw,
          interruptible: customInterruptible,
          priority: customPriority,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        setCustomMessage(getApiErrorMessage(data, 'Could not add appliance.'))
        return
      }

      await loadAppliances()

      setSelectedAppliances((current) =>
        current.includes(data.id) ? current : [...current, data.id]
      )

      setCustomName('')
      setCustomKw('')
      setCustomInterruptible(true)
      setCustomPriority('low')
      setCustomMessage(`${data.name} added to your home.`)
      return data
    } catch (error) {
      console.error('Failed to create appliance:', error)
      setCustomMessage('Could not connect to the VoltBuddy backend.')
    } finally {
      setCustomLoading(false)
    }
  }

  async function saveHome(event) {
    event.preventDefault()
    setHomeMessage('')

    const cleanedName = homeName.trim()

    if (!cleanedName) {
      setHomeMessage('Enter a name for this home.')
      return
    }

    if (selectedAppliances.length === 0) {
      setHomeMessage('Select at least one appliance before saving a home.')
      return
    }

    setHomeSaving(true)

    try {
      const response = await fetch(`${API_BASE}/homes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: cleanedName,
          appliances: selectedAppliances,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        setHomeMessage(getApiErrorMessage(data, 'Could not save this home.'))
        return
      }

      await loadHomes()
      setHomeName('')
      setHomeMessage(`${data.name} saved.`)
      setActiveHomeId(data.id)
      setActiveHomeName(data.name)
    } catch (error) {
      console.error('Failed to save home:', error)
      setHomeMessage('Could not connect to the VoltBuddy backend.')
    } finally {
      setHomeSaving(false)
    }
  }

  async function loadSavedHome(homeId) {
    setHomeMessage('')
    setLoadingHomeId(homeId)

    try {
      const response = await fetch(`${API_BASE}/homes/${homeId}`)
      const data = await response.json()

      if (!response.ok) {
        setHomeMessage(data.detail || 'Could not load this home.')
        return
      }

      setSelectedAppliances(data.appliances.map((appliance) => appliance.id))
      setHomeMessage(`${data.name} loaded.`)
      setActiveHomeId(data.id)
      setActiveHomeName(data.name)
    } catch (error) {
      console.error('Failed to load home:', error)
      setHomeMessage('Could not connect to the VoltBuddy backend.')
    } finally {
      setLoadingHomeId(null)
    }
  }

  function startEditingAppliance(appliance) {
    setEditingApplianceId(appliance.id)
    setEditName(appliance.name)
    setEditKw(String(appliance.kw))
    setEditInterruptible(appliance.interruptible)
    setEditPriority(appliance.priority)
    setEditMessage('')
  }

  function cancelEditingAppliance() {
    setEditingApplianceId(null)
    setEditMessage('')
  }

  async function updateAppliance(event) {
    event.preventDefault()
    setEditMessage('')

    const cleanedName = editName.trim()
    const numericKw = Number(editKw)

    if (!cleanedName) {
      setEditMessage('Enter an appliance name.')
      return
    }

    if (cleanedName.length > 80) {
      setEditMessage('Appliance name must be 80 characters or fewer.')
      return
    }

    if (!editKw || Number.isNaN(numericKw) || numericKw <= 0 || numericKw > 50) {
      setEditMessage('Enter a power use greater than 0 and no more than 50 kW.')
      return
    }

    setEditLoading(true)

    try {
      const response = await fetch(`${API_BASE}/appliances/${editingApplianceId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: cleanedName,
          kw: numericKw,
          interruptible: editInterruptible,
          priority: editPriority,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        setEditMessage(getApiErrorMessage(data, 'Could not save appliance changes.'))
        return
      }

      await Promise.all([loadAppliances(), loadHomes()])
      setCustomMessage(`${data.name} updated.`)
      setEditingApplianceId(null)
      setEditMessage('')
    } catch (error) {
      console.error('Failed to update appliance:', error)
      setEditMessage('Could not connect to the VoltBuddy backend.')
    } finally {
      setEditLoading(false)
    }
  }

  async function searchApplianceCatalog(eventOrOffset = null) {
    let pageOffset = 0

    if (typeof eventOrOffset === 'number') {
      pageOffset = Math.max(0, eventOrOffset)
    } else {
      eventOrOffset?.preventDefault?.()
    }

    const query = applianceSearch.trim()

    if (!query && !catalogCategory) {
      setSearchResults([])
      setCatalogTotal(0)
      setCatalogHasMore(false)
      setCatalogOffset(0)
      setSearchMessage('Type a brand, model, or appliance — or choose a category.')
      return
    }

    setSearchLoading(true)
    setSearchMessage('')

    try {
      const params = new URLSearchParams({
        q: query,
        sort: catalogSort,
        limit: String(CATALOG_PAGE_SIZE),
        offset: String(pageOffset),
      })

      if (catalogCategory) params.set('category', catalogCategory)

      const response = await fetch(`${API_BASE}/catalog/search?${params.toString()}`)
      const data = await response.json()

      if (!response.ok) {
        setSearchMessage(getApiErrorMessage(data, 'Could not search the ENERGY STAR catalog.'))
        return
      }

      const items = data.items || []

      setSearchResults(items)
      setCatalogHasMore(Boolean(data.has_more))
      setCatalogOffset(pageOffset)
      setCatalogTotal(typeof data.total === 'number' ? data.total : 0)

      if (items.length === 0) {
        if (pageOffset > 0) {
          setSearchMessage('No more matching models.')
          setCatalogOffset(Math.max(0, pageOffset - CATALOG_PAGE_SIZE))
        } else {
          setSearchMessage('No matching certified models yet. Try a broader search or use an estimate.')
        }
      }
    } catch (error) {
      console.error('Failed to search appliance catalog:', error)
      setSearchMessage('Could not connect to the VoltBuddy backend.')
    } finally {
      setSearchLoading(false)
    }
  }

  async function addCatalogProduct(catalogProductId) {
    setSearchMessage('')
    try {
      const response = await fetch(`${API_BASE}/catalog/${catalogProductId}/add`, { method: 'POST' })
      const data = await response.json()
      if (!response.ok) {
        setSearchMessage(getApiErrorMessage(data, 'Could not add that appliance.'))
        return
      }

      await loadAppliances()
      setSelectedAppliances((current) =>
        current.includes(data.id) ? current : [...current, data.id]
      )
      setSearchMessage(`${data.name} added to your home.`)
      return data
    } catch (error) {
      console.error('Failed to add catalog product:', error)
      setSearchMessage('Could not connect to the VoltBuddy backend.')
    }
  }

  async function addEstimatedAppliance(category = estimateCategory) {
    setEstimateLoading(true)
    setSearchMessage('')
    try {
      const estimateResponse = await fetch(`${API_BASE}/appliances/estimate?category=${encodeURIComponent(category)}`)
      const estimate = await estimateResponse.json()
      if (!estimateResponse.ok) {
        setSearchMessage(getApiErrorMessage(estimate, 'No estimate is available for that appliance yet.'))
        return
      }

      const createResponse = await fetch(`${API_BASE}/appliances`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: estimate.name,
          kw: estimate.kw,
          interruptible: estimate.interruptible,
          priority: estimate.priority,
          category: estimate.category,
          annual_kwh: estimate.annual_kwh,
          typical_runtime_hours: estimate.typical_runtime_hours,
          source: estimate.source,
          is_estimate: true,
        }),
      })
      const created = await createResponse.json()
      if (!createResponse.ok) {
        setSearchMessage(getApiErrorMessage(created, 'Could not add the estimate.'))
        return
      }

      await loadAppliances()
      setSelectedAppliances((current) => (current.includes(created.id) ? current : [...current, created.id]))
      setSearchMessage(`${created.name} added using a category estimate. You can edit it anytime.`)
      return created
    } catch (error) {
      console.error('Failed to add estimated appliance:', error)
      setSearchMessage('Could not connect to the VoltBuddy backend.')
    } finally {
      setEstimateLoading(false)
    }
  }

  async function identifyAppliancePhoto(file) {
    if (!file) return
    setPhotoLoading(true)
    setPhotoMessage('')
    setPhotoResult(null)
    const formData = new FormData()
    formData.append('image', file)

    try {
      const response = await fetch(`${API_BASE}/appliances/identify-image`, { method: 'POST', body: formData })
      const data = await response.json()
      if (!response.ok) {
        setPhotoMessage(getApiErrorMessage(data, 'Could not identify that photo.'))
        return
      }
      setPhotoResult(data)
    } catch (error) {
      console.error('Failed to identify appliance photo:', error)
      setPhotoMessage('Could not connect to the VoltBuddy backend.')
    } finally {
      setPhotoLoading(false)
    }
  }

  async function deleteAppliance(applianceId, applianceName) {
    const confirmed = window.confirm(
      `Delete ${applianceName}? This will also remove it from any saved home that uses it.`
    )

    if (!confirmed) return

    setCustomMessage('')

    try {
      const response = await fetch(`${API_BASE}/appliances/${applianceId}`, { method: 'DELETE' })
      const data = await response.json()

      if (!response.ok) {
        setCustomMessage(getApiErrorMessage(data, 'Could not delete appliance.'))
        return
      }

      setSelectedAppliances((current) => current.filter((id) => id !== applianceId))

      await Promise.all([loadAppliances(), loadHomes()])
      setCustomMessage(`${applianceName} deleted.`)
    } catch (error) {
      console.error('Failed to delete appliance:', error)
      setCustomMessage('Could not connect to the VoltBuddy backend.')
    }
  }

  async function deleteSavedHome(homeId, homeNameToDelete) {
    const confirmed = window.confirm(`Delete ${homeNameToDelete}? This cannot be undone.`)

    if (!confirmed) return

    setHomeMessage('')

    try {
      const response = await fetch(`${API_BASE}/homes/${homeId}`, { method: 'DELETE' })
      const data = await response.json()

      if (!response.ok) {
        setHomeMessage(getApiErrorMessage(data, 'Could not delete this home.'))
        return
      }

      await loadHomes()
      setHomeMessage(`${homeNameToDelete} deleted.`)
      if (activeHomeId === homeId) {
        setActiveHomeId(null)
        setActiveHomeName('')
      }
    } catch (error) {
      console.error('Failed to delete home:', error)
      setHomeMessage('Could not connect to the VoltBuddy backend.')
    }
  }

  async function clearHistory() {
    if (history.length === 0) return

    const confirmed = window.confirm('Clear all VoltBuddy simulation history? This cannot be undone.')

    if (!confirmed) return

    try {
      const response = await fetch(`${API_BASE}/simulations`, { method: 'DELETE' })

      if (!response.ok) {
        throw new Error('Could not clear history.')
      }

      setHistory([])
      setSimulation(null)
    } catch (error) {
      console.error('Failed to clear simulation history:', error)
      window.alert('Could not clear simulation history.')
    }
  }

  async function runSimulation() {
    setSimulationMessage('')

    if (selectedAppliances.length === 0) {
      setSimulation(null)
      setSimulationMessage('Select at least one appliance before running a VoltBuddy plan.')
      return
    }

    setSimulationLoading(true)

    try {
      const response = await fetch(`${API_BASE}/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          hour,
          appliances: selectedAppliances,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        setSimulation(null)
        setSimulationMessage(getApiErrorMessage(data, 'VoltBuddy could not run this simulation.'))
        return
      }

      setSimulation(data)
      setSimulationMessage('')
      await loadHistory()
      navigate('/results')
    } catch (error) {
      console.error('Failed to run simulation:', error)
      setSimulation(null)
      setSimulationMessage('Could not connect to the VoltBuddy backend. Make sure FastAPI is running.')
    } finally {
      setSimulationLoading(false)
    }
  }

  const initialLoading = !appliancesLoaded || !homesLoaded
  const hasHome = homes.length > 0 || appliances.length > 0
  const estimatedSavings = simulation?.daily_plan?.estimated_daily_savings ?? null
  const appliancesShifted = simulation?.daily_plan?.shifted_appliances ?? null

  const value = {
    navigate,
    hour,
    setHour,
    appliances,
    selectedAppliances,
    toggleAppliance,
    simulation,
    simulationMessage,
    simulationLoading,
    runSimulation,
    history,
    totalHistorySavings,
    averageSavings,
    savingsChartData,
    electricityRates,
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
    applianceSearch,
    setApplianceSearch,
    searchResults,
    searchLoading,
    searchMessage,
    setSearchMessage,
    searchApplianceCatalog,
    catalogCategory,
    setCatalogCategory,
    catalogSort,
    setCatalogSort,
    catalogTotal,
    catalogHasMore,
    catalogOffset,
    addCatalogProduct,
    estimateCategory,
    setEstimateCategory,
    estimateLoading,
    addEstimatedAppliance,
    photoLoading,
    photoResult,
    photoMessage,
    identifyAppliancePhoto,
    homes,
    homeName,
    setHomeName,
    homeMessage,
    homeSaving,
    loadingHomeId,
    activeHomeId,
    activeHomeName,
    appliancesLoaded,
    homesLoaded,
    initialLoading,
    backendError,
    retryInitialLoad: () => {
      loadAppliances()
      loadHomes()
    },
    saveHome,
    loadSavedHome,
    deleteAppliance,
    deleteSavedHome,
    clearHistory,
    liveGrid,
    liveGridLoading,
    loadLiveGrid,
    carbonData,
    carbonLoading,
    loadCarbonData,
    hasHome,
    estimatedSavings,
    appliancesShifted,
  }

  return <VoltBuddyContext.Provider value={value}>{children}</VoltBuddyContext.Provider>
}
