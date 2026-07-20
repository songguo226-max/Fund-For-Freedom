const CODE_RE = /^\d{6}$/

function normalize(value) {
  return String(value || '').trim().toLowerCase()
}

export function resolveFundTarget(query, hits = []) {
  const q = String(query || '').trim()
  if (!q) return ''
  if (CODE_RE.test(q)) return q

  const normalized = normalize(q)
  const exact = hits.find((hit) => normalize(hit.code) === normalized || normalize(hit.name) === normalized)
  if (exact) return exact.code

  const contains = hits.find((hit) => normalize(hit.name).includes(normalized))
  if (contains) return contains.code

  return hits[0]?.code || ''
}
