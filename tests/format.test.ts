import { describe, it, expect } from 'vitest'
import { formatBytes, formatCount } from '../src/utils/format'

describe('formatBytes', () => {
  it('formats bytes', () => {
    expect(formatBytes(500)).toBe('500 B')
  })
  it('formats kilobytes', () => {
    expect(formatBytes(1536)).toBe('1.5 KB')
  })
  it('formats megabytes', () => {
    expect(formatBytes(2621440)).toBe('2.5 MB')
  })
  it('formats gigabytes', () => {
    expect(formatBytes(1610612736)).toBe('1.5 GB')
  })
})

describe('formatCount', () => {
  it('formats small numbers', () => {
    expect(formatCount(42)).toBe('42')
  })
  it('formats thousands', () => {
    expect(formatCount(1234)).toBe('1,234')
  })
  it('formats millions', () => {
    expect(formatCount(1234567)).toBe('1,234,567')
  })
})
