const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'

async function request(path, params = {}) {
  const url = new URL(`${API_BASE}${path}`, window.location.origin)
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, value)
  }
  const resp = await fetch(url)
  if (!resp.ok) {
    let detail = `请求失败 (${resp.status})`
    try {
      const payload = await resp.json()
      detail = payload.detail || detail
    } catch {
      detail = resp.statusText || detail
    }
    throw new Error(detail)
  }
  return resp.json()
}

async function post(path, body = {}) {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!resp.ok) {
    let detail = `请求失败 (${resp.status})`
    try {
      const payload = await resp.json()
      detail = payload.detail || detail
    } catch {
      detail = resp.statusText || detail
    }
    throw new Error(detail)
  }
  return resp.json()
}

export const api = {
  dataSources(filters = {}) {
    return request('/data-sources', filters)
  },
  indexTrends(params = {}) {
    return request('/index-trends', params)
  },
  fedEconomyAtGlance() {
    return request('/fed/economy-at-a-glance')
  },
  search(q, source) {
    return request('/search', { q, source })
  },
  meta(code, source) {
    return request(`/fund/${code}/meta`, { source })
  },
  calendar(code, months = 3, source) {
    return request(`/fund/${code}/calendar`, { months, source })
  },
  monthly(code, source) {
    return request(`/fund/${code}/monthly`, { source })
  },
  trend(code, range = '1y', source) {
    return request(`/fund/${code}/trend`, { range, source })
  },
  exportUrl(code, type, source) {
    const url = new URL(`${API_BASE}/fund/${code}/export.csv`, window.location.origin)
    url.searchParams.set('type', type)
    if (source) url.searchParams.set('source', source)
    return url.toString()
  },
  newsBootstrap() {
    return request('/news/bootstrap')
  },
  syncNewsWatchlist(payload) {
    return post('/news/watchlist', payload)
  },
  newsRefresh(params = {}) {
    return request('/news/refresh', params)
  },
}
