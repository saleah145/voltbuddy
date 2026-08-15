export function formatHour(hourValue) {
  if (hourValue === 0) return '12:00 AM'
  if (hourValue === 12) return '12:00 PM'
  if (hourValue < 12) return `${hourValue}:00 AM`
  return `${hourValue - 12}:00 PM`
}

export function formatScheduleTime(hourValue) {
  const wrapped = ((Number(hourValue) % 24) + 24) % 24
  const wholeHour = Math.floor(wrapped)
  const minutes = Math.round((wrapped - wholeHour) * 60)
  const displayHour = wholeHour % 12 === 0 ? 12 : wholeHour % 12
  const suffix = wholeHour < 12 ? 'AM' : 'PM'
  return `${displayHour}:${String(minutes).padStart(2, '0')} ${suffix}`
}

export function formatScheduleWindow(startHour, runtimeHours) {
  return `${formatScheduleTime(startHour)} → ${formatScheduleTime(Number(startHour) + Number(runtimeHours))}`
}

export function getTimelineSegments(startHour, runtimeHours) {
  const start = ((Number(startHour) % 24) + 24) % 24
  const runtime = Math.max(0, Math.min(Number(runtimeHours) || 0, 24))

  if (runtime >= 24) {
    return [{ left: 0, width: 100 }]
  }

  const end = start + runtime

  if (end <= 24) {
    return [
      {
        left: (start / 24) * 100,
        width: (runtime / 24) * 100,
      },
    ]
  }

  return [
    {
      left: (start / 24) * 100,
      width: ((24 - start) / 24) * 100,
    },
    {
      left: 0,
      width: ((end - 24) / 24) * 100,
    },
  ]
}

export function formatSimulationTimestamp(value) {
  if (!value) return { date: 'Date unavailable', time: '' }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return { date: 'Date unavailable', time: '' }
  }

  return {
    date: parsed.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }),
    time: parsed.toLocaleTimeString(undefined, {
      hour: 'numeric',
      minute: '2-digit',
    }),
  }
}

export function getApplianceIcon(id) {
  if (id === 'ev_charger') return '🚗'
  if (id === 'gaming_pc') return '🖥️'
  if (id === 'space_heater') return '♨️'
  if (id === 'refrigerator') return '❄️'
  return '⚡'
}

export function getCatalogIcon(category) {
  const value = (category || '').toLowerCase()
  if (value === 'refrigerator') return '❄️'
  if (value === 'washer') return '🫧'
  if (value === 'dryer') return '♨️'
  if (value === 'dishwasher') return '🍽️'
  if (value === 'tv') return '📺'
  if (value === 'air conditioner') return '❄️'
  if (value === 'ev charger') return '🔌'
  return '⚡'
}

export function getCatalogVisualPath(category) {
  const normalized = (category || '').trim().toLowerCase()

  if (normalized.includes('refrigerator')) return '/catalog-visuals/refrigerator.svg'
  if (normalized.includes('washer')) return '/catalog-visuals/washer.svg'
  if (normalized.includes('dryer')) return '/catalog-visuals/dryer.svg'
  if (normalized.includes('dishwasher')) return '/catalog-visuals/dishwasher.svg'
  if (normalized === 'tv' || normalized.includes('television')) return '/catalog-visuals/tv.svg'
  if (normalized.includes('air conditioner')) return '/catalog-visuals/air-conditioner.svg'
  if (normalized.includes('ev charger')) return '/catalog-visuals/ev-charger.svg'

  return '/catalog-visuals/refrigerator.svg'
}

export function getCatalogDisplayName(item) {
  const brand = (item?.brand || '').trim()
  const productType = (item?.product_type || '').trim()
  const category = (item?.category || '').trim().toLowerCase()

  const categoryLabels = {
    refrigerator: 'Refrigerator',
    washer: 'Clothes Washer',
    dryer: 'Clothes Dryer',
    dishwasher: 'Dishwasher',
    tv: 'Television',
    'air conditioner': 'Room Air Conditioner',
    'ev charger': 'EV Charger',
  }

  const categoryLabel =
    categoryLabels[category] ||
    (item?.category
      ? item.category.charAt(0).toUpperCase() + item.category.slice(1)
      : 'Appliance')

  const capacity =
    item?.capacity != null
      ? `${Number(item.capacity).toLocaleString(undefined, {
          maximumFractionDigits: 1,
        })}${item.capacity_unit ? ` ${item.capacity_unit}` : ''}`
      : ''

  const typeAlreadyNamesCategory =
    productType &&
    (
      productType.toLowerCase().includes(categoryLabel.toLowerCase()) ||
      categoryLabel.toLowerCase().includes(productType.toLowerCase())
    )

  const parts = [
    brand,
    capacity,
    productType,
    typeAlreadyNamesCategory ? '' : categoryLabel,
  ].filter(Boolean)

  return parts.join(' ') || item?.model_name || item?.model_number || 'Certified appliance'
}

export function getApplianceType(appliance) {
  if (appliance.priority === 'critical') return 'Essential appliance'
  if (appliance.interruptible) return 'Flexible appliance'
  return 'User-controlled'
}

export function getRateMessage(grid) {
  if (grid.tier === 'on_peak') {
    return 'Georgia Power is in its summer on-peak window. VoltBuddy may pause flexible appliances to reduce energy costs.'
  }

  if (grid.tier === 'super_off_peak') {
    return 'This is Georgia Power’s lowest-cost overnight period, so flexible appliances can run at the cheapest energy rate.'
  }

  return 'This is an off-peak period, so electricity is cheaper than the summer on-peak window.'
}

export function getCarbonLabel(signal) {
  if (signal === 'lower_carbon_mix') return 'Lower-carbon mix'
  if (signal === 'fossil_heavy_mix') return 'Fossil-heavy mix'
  return 'Mixed generation'
}

export function getDecisionLabel(decision) {
  if (decision === 'pause') return 'Pause now'
  if (decision === 'recommend_shift') return 'Shift if practical'
  return 'Keep running'
}

export function getRecommendationIcon(type) {
  if (type === 'pause_now') return '⏸'
  if (type === 'shift_load') return '🕒'
  if (type === 'good_time_to_run') return '✓'
  if (type === 'grid_context') return '⚡'
  if (type === 'carbon_context') return '🌱'
  return 'i'
}

export const ELECTRICITY_RATES = Array.from({ length: 24 }, (_, hourValue) => {
  let rate = 0.101676
  let tier = 'Off-peak'

  if (hourValue >= 23 || hourValue < 7) {
    rate = 0.021859
    tier = 'Super off-peak'
  } else if (hourValue >= 14 && hourValue < 19) {
    rate = 0.297868
    tier = 'On-peak'
  }

  return {
    hour: hourValue,
    label:
      hourValue === 0
        ? '12 AM'
        : hourValue === 12
          ? '12 PM'
          : hourValue > 12
            ? `${hourValue - 12} PM`
            : `${hourValue} AM`,
    rate,
    tier,
  }
})
