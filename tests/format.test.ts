import { describe, it, expect, vi, afterEach } from 'vitest'
import { formatBytes, formatCount, formatMessageDate, formatSyncTime } from '../src/utils/format'

describe('formatBytes', () => {
  it('formats bytes', () => {
    expect(formatBytes(500)).toBe('500 B')
  })
  it('formats zero', () => {
    expect(formatBytes(0)).toBe('0 B')
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
  it('formats exact boundary (1 KB)', () => {
    expect(formatBytes(1024)).toBe('1.0 KB')
  })
})

describe('formatCount', () => {
  it('formats zero', () => {
    expect(formatCount(0)).toBe('0')
  })
  it('formats small numbers', () => {
    expect(formatCount(42)).toBe('42')
  })
  it('formats 999 (no comma)', () => {
    expect(formatCount(999)).toBe('999')
  })
  it('formats thousands', () => {
    expect(formatCount(1234)).toBe('1,234')
  })
  it('formats millions', () => {
    expect(formatCount(1234567)).toBe('1,234,567')
  })
  it('formats negative numbers', () => {
    expect(formatCount(-1234)).toBe('-1,234')
  })
})

describe('formatMessageDate', () => {
  it('formats same-year date with time', () => {
    const now = new Date()
    const d = new Date(now.getFullYear(), 2, 15, 14, 30)
    const result = formatMessageDate(d.toISOString())
    expect(result).toBe('Mar 15 14:30')
  })

  it('formats different-year date without time', () => {
    const d = new Date(2020, 11, 25, 10, 0)
    const result = formatMessageDate(d.toISOString())
    expect(result).toBe('Dec 25, 2020')
  })

  it('zero-pads day and time', () => {
    const now = new Date()
    const d = new Date(now.getFullYear(), 0, 5, 3, 7)
    const result = formatMessageDate(d.toISOString())
    expect(result).toBe('Jan 05 03:07')
  })
})

describe('formatSyncTime', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns "never" for null', () => {
    expect(formatSyncTime(null)).toBe('never')
  })

  it('returns "never" for empty string', () => {
    expect(formatSyncTime('')).toBe('never')
  })

  it('returns "just now" for < 1 minute ago', () => {
    const d = new Date(Date.now() - 30_000)
    expect(formatSyncTime(d.toISOString())).toBe('just now')
  })

  it('returns minutes ago', () => {
    const d = new Date(Date.now() - 5 * 60_000)
    expect(formatSyncTime(d.toISOString())).toBe('5m ago')
  })

  it('returns hours ago', () => {
    const d = new Date(Date.now() - 3 * 3_600_000)
    expect(formatSyncTime(d.toISOString())).toBe('3h ago')
  })

  it('returns days ago', () => {
    const d = new Date(Date.now() - 7 * 86_400_000)
    expect(formatSyncTime(d.toISOString())).toBe('7d ago')
  })

  it('returns full date for 30+ days ago', () => {
    const d = new Date(2023, 5, 15)
    expect(formatSyncTime(d.toISOString())).toBe('Jun 15, 2023')
  })
})
