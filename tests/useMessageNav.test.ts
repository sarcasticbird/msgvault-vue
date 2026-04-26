import { describe, it, expect, beforeEach } from 'vitest'
import { useMessageNav } from '../src/composables/useMessageNav'

describe('useMessageNav', () => {
  let nav: ReturnType<typeof useMessageNav>

  beforeEach(() => {
    nav = useMessageNav()
    nav.storeMessageList([])
  })

  it('returns empty navigation for empty list', () => {
    const result = nav.getNavigation(1)
    expect(result).toEqual({ prev: null, next: null, position: '', total: 0 })
  })

  it('returns empty navigation when id not found', () => {
    nav.storeMessageList([10, 20, 30])
    const result = nav.getNavigation(99)
    expect(result).toEqual({ prev: null, next: null, position: '', total: 0 })
  })

  it('returns correct navigation for first item', () => {
    nav.storeMessageList([10, 20, 30])
    const result = nav.getNavigation(10)
    expect(result.prev).toBeNull()
    expect(result.next).toBe(20)
    expect(result.position).toBe('1 / 3')
    expect(result.total).toBe(3)
  })

  it('returns correct navigation for middle item', () => {
    nav.storeMessageList([10, 20, 30])
    const result = nav.getNavigation(20)
    expect(result.prev).toBe(10)
    expect(result.next).toBe(30)
    expect(result.position).toBe('2 / 3')
  })

  it('returns correct navigation for last item', () => {
    nav.storeMessageList([10, 20, 30])
    const result = nav.getNavigation(30)
    expect(result.prev).toBe(20)
    expect(result.next).toBeNull()
    expect(result.position).toBe('3 / 3')
  })

  it('handles single-item list', () => {
    nav.storeMessageList([42])
    const result = nav.getNavigation(42)
    expect(result.prev).toBeNull()
    expect(result.next).toBeNull()
    expect(result.position).toBe('1 / 1')
    expect(result.total).toBe(1)
  })

  it('updates when list is replaced', () => {
    nav.storeMessageList([10, 20, 30])
    expect(nav.getNavigation(20).total).toBe(3)

    nav.storeMessageList([100, 200])
    expect(nav.getNavigation(20).total).toBe(0)
    expect(nav.getNavigation(100).position).toBe('1 / 2')
  })
})
