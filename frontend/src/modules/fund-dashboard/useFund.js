import { reactive } from 'vue'
import { api } from '../../integrations/fund-api'
import { useWatchlist } from '../watchlist/useWatchlist'

function block() {
  return reactive({ data: null, loading: false, error: '' })
}

export function useFund(codeRef) {
  const { addRecent } = useWatchlist()
  const meta = block()
  const calendar = block()
  const monthly = block()
  const trend = block()
  const state = reactive({ source: '', range: '1y' })

  const code = () => (typeof codeRef === 'function' ? codeRef() : codeRef)

  async function run(target, fn) {
    target.loading = true
    target.error = ''
    try {
      target.data = await fn()
    } catch (err) {
      target.error = err.message || '请求失败'
      target.data = null
    } finally {
      target.loading = false
    }
  }

  async function loadMeta() {
    await run(meta, () => api.meta(code(), state.source))
    if (meta.data) addRecent({ code: meta.data.code, name: meta.data.name, type: meta.data.type })
  }

  function load(range = state.range) {
    state.range = range
    loadMeta()
    run(calendar, () => api.calendar(code(), 3, state.source))
    run(monthly, () => api.monthly(code(), state.source))
    run(trend, () => api.trend(code(), state.range, state.source))
  }

  function setSource(source) {
    state.source = source || ''
    load()
  }

  return { meta, calendar, monthly, trend, state, load, setSource }
}
