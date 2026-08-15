export const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
export const CATALOG_PAGE_SIZE = 4

export function getApiErrorMessage(data, fallback) {
  if (!data) return fallback
  if (typeof data.detail === 'string') return data.detail
  if (data.detail?.message) return data.detail.message

  if (Array.isArray(data.detail) && data.detail.length > 0) {
    return data.detail
      .map((item) => item.msg)
      .filter(Boolean)
      .join(' ')
  }

  return fallback
}
