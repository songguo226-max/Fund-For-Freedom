import { describe, expect, it } from 'vitest'
import { fmtPct, money, pctState } from './format'

describe('format helpers', () => {
  it('formats percentages with a plus sign for gains', () => {
    expect(fmtPct(1.234)).toBe('+1.23%')
    expect(fmtPct(-0.5)).toBe('-0.50%')
  })

  it('classifies pct state', () => {
    expect(pctState(1)).toBe('rise')
    expect(pctState(-1)).toBe('fall')
    expect(pctState(0)).toBe('flat')
  })

  it('formats nav values', () => {
    expect(money(1.23456)).toBe('1.2346')
  })
})
