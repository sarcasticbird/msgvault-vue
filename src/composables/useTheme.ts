import { ref, onMounted } from 'vue'

type Theme = 'auto' | 'dark' | 'light'

const theme = ref<Theme>('auto')
const themeIcon = ref('\u25D1') // half circle (auto)

function applyTheme(t: Theme) {
  theme.value = t
  const root = document.documentElement
  if (t === 'dark') {
    root.setAttribute('data-theme', 'dark')
    themeIcon.value = '\u263E' // moon
  } else if (t === 'light') {
    root.setAttribute('data-theme', 'light')
    themeIcon.value = '\u2600' // sun
  } else {
    root.removeAttribute('data-theme')
    themeIcon.value = '\u25D1' // half circle
  }
}

export function useTheme() {
  onMounted(() => {
    const saved = (localStorage.getItem('msgvault-theme') || 'auto') as Theme
    applyTheme(saved)
  })

  function toggleTheme() {
    const next: Theme = theme.value === 'auto' ? 'dark' : theme.value === 'dark' ? 'light' : 'auto'
    localStorage.setItem('msgvault-theme', next)
    applyTheme(next)
  }

  return { theme, themeIcon, toggleTheme }
}
