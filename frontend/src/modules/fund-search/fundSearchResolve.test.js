import { describe, expect, it } from 'vitest'
import { resolveFundTarget } from './fundSearchResolve'

describe('resolveFundTarget', () => {
  const hits = [
    { code: '000218', name: '国泰黄金ETF联接A', type: '基金' },
    { code: '518800', name: '黄金ETF国泰', type: '基金' },
  ]

  it('keeps six digit fund codes as the target', () => {
    expect(resolveFundTarget('000218', hits)).toBe('000218')
  })

  it('resolves an exact fund name to its code', () => {
    expect(resolveFundTarget('国泰黄金ETF联接A', hits)).toBe('000218')
  })

  it('falls back to the first search hit for non-exact names', () => {
    expect(resolveFundTarget('黄金', hits)).toBe('000218')
  })
})
