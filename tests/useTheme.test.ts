// @vitest-environment jsdom
import { describe, it, expect, beforeEach, vi } from 'vitest'

// useTheme uses onMounted internally, so we test the exported API
// through a dynamic import with resetModules to get fresh state.
// The Vue "onMounted outside setup" warning is expected in unit tests.

describe('useTheme', () => {
  beforeEach(() => {
    document.documentElement.removeAttribute('data-theme')
    localStorage.clear()
    vi.resetModules()
  })

  async function loadTheme() {
    const mod = await import('../src/composables/useTheme')
    return mod.useTheme()
  }

  it('toggleTheme cycles auto -> dark -> light -> auto', async () => {
    const { theme, themeIcon, toggleTheme } = await loadTheme()

    // First toggle: auto -> dark
    toggleTheme()
    expect(theme.value).toBe('dark')
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
    expect(themeIcon.value).toBe('\u263E') // moon

    // Second toggle: dark -> light
    toggleTheme()
    expect(theme.value).toBe('light')
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
    expect(themeIcon.value).toBe('\u2600') // sun

    // Third toggle: light -> auto
    toggleTheme()
    expect(theme.value).toBe('auto')
    expect(document.documentElement.getAttribute('data-theme')).toBeNull()
    expect(themeIcon.value).toBe('\u25D1') // half circle
  })

  it('persists theme to localStorage on toggle', async () => {
    const { toggleTheme } = await loadTheme()

    toggleTheme()
    expect(localStorage.getItem('msgvault-theme')).toBe('dark')

    toggleTheme()
    expect(localStorage.getItem('msgvault-theme')).toBe('light')

    toggleTheme()
    expect(localStorage.getItem('msgvault-theme')).toBe('auto')
  })

  it('auto theme removes data-theme attribute from DOM', async () => {
    document.documentElement.setAttribute('data-theme', 'dark')
    const { toggleTheme } = await loadTheme()

    // Cycle through: auto -> dark -> light -> auto
    toggleTheme()
    toggleTheme()
    toggleTheme()
    expect(document.documentElement.getAttribute('data-theme')).toBeNull()
  })
})
