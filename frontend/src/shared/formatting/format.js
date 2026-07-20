export function fmtPct(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '暂无'
  const n = Number(value)
  return `${n > 0 ? '+' : ''}${n.toFixed(2)}%`
}

export function pctState(value) {
  const n = Number(value)
  if (n > 0) return 'rise'
  if (n < 0) return 'fall'
  return 'flat'
}

export function money(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '暂无'
  return Number(value).toFixed(4)
}

export function compactDate(value) {
  if (!value) return ''
  return String(value).slice(5)
}
