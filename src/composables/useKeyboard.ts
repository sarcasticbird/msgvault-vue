import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'

export const helpVisible = ref(false)
export const activeRow = ref(-1)

export function useKeyboard() {
  const router = useRouter()
  const route = useRoute()

  watch(() => route.fullPath, () => { activeRow.value = -1 })

  function isInputFocused(): boolean {
    const el = document.activeElement
    if (!el) return false
    const tag = el.tagName.toLowerCase()
    return tag === 'input' || tag === 'textarea' || tag === 'select' || (el as HTMLElement).isContentEditable
  }

  function getRows(): NodeListOf<HTMLTableRowElement> {
    const table = document.querySelector('.data-table tbody')
    return table ? table.querySelectorAll('tr') : document.querySelectorAll('.noop-sentinel')
  }

  function clearActive() {
    getRows().forEach(r => r.classList.remove('kb-active'))
  }

  function setActive(index: number) {
    const rows = getRows()
    if (rows.length === 0) return
    if (index < 0) index = 0
    if (index >= rows.length) index = rows.length - 1
    clearActive()
    activeRow.value = index
    rows[activeRow.value].classList.add('kb-active')
    rows[activeRow.value].scrollIntoView({ block: 'nearest' })
  }

  function openActiveRow(linkIndex = 0) {
    const rows = getRows()
    if (activeRow.value < 0 || activeRow.value >= rows.length) return
    const links = rows[activeRow.value].querySelectorAll('a')
    if (links.length === 0) return
    const idx = linkIndex < links.length ? linkIndex : 0
    const href = links[idx].getAttribute('href')
    if (href) router.push(href)
  }

  function onKeyDown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      if (helpVisible.value) { helpVisible.value = false; e.preventDefault(); return }
      if (isInputFocused()) { (document.activeElement as HTMLElement).blur(); e.preventDefault(); return }
    }
    if (isInputFocused()) return

    switch (e.key) {
      case '/': {
        e.preventDefault()
        const input = document.querySelector('.search-input') as HTMLInputElement
        if (input) { input.focus(); input.select() }
        else router.push('/search')
        break
      }
      case '?':
        e.preventDefault()
        helpVisible.value = !helpVisible.value
        break
      case 'j':
      case 'ArrowDown':
        e.preventDefault()
        setActive(activeRow.value + 1)
        break
      case 'k':
      case 'ArrowUp':
        e.preventDefault()
        setActive(activeRow.value - 1)
        break
      case 'Enter':
        if (activeRow.value >= 0) { e.preventDefault(); openActiveRow(0) }
        break
      case 'o':
        if (activeRow.value >= 0) { e.preventDefault(); openActiveRow(1) }
        break
      case 'g':
        e.preventDefault()
        setActive(0)
        break
      case 'G':
        e.preventDefault()
        setActive(getRows().length - 1)
        break
      case 'H':
        router.push('/')
        break
      case 'B':
        router.push('/browse')
        break
      case 'Backspace':
        e.preventDefault()
        if (window.history.state?.back) {
          router.back()
        } else {
          router.push('/')
        }
        break
      case 'n': {
        const next = document.querySelector('.pagination a:last-of-type') as HTMLAnchorElement
        if (next?.textContent?.trim() === 'Next') {
          next.click()
        }
        break
      }
      case 'p': {
        const prev = document.querySelector('.pagination a:first-of-type') as HTMLAnchorElement
        if (prev?.textContent?.trim() === 'Prev') {
          prev.click()
        }
        break
      }
      case 'ArrowLeft': {
        const prevMsg = document.getElementById('msg-prev') as HTMLAnchorElement
        if (prevMsg) { prevMsg.click(); e.preventDefault() }
        break
      }
      case 'ArrowRight': {
        const nextMsg = document.getElementById('msg-next') as HTMLAnchorElement
        if (nextMsg) { nextMsg.click(); e.preventDefault() }
        break
      }
    }
  }

  onMounted(() => {
    document.addEventListener('keydown', onKeyDown)
  })

  onUnmounted(() => {
    document.removeEventListener('keydown', onKeyDown)
  })

  return { helpVisible, activeRow, setActive }
}
