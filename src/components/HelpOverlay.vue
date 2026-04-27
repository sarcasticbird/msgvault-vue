<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const emit = defineEmits<{ close: [] }>()

const dialogRef = ref<HTMLElement | null>(null)
let previousFocus: Element | null = null

function trapFocus(e: KeyboardEvent) {
  if (e.key !== 'Tab' || !dialogRef.value) return
  const focusable = dialogRef.value.querySelectorAll<HTMLElement>(
    'a[href], button, [tabindex]:not([tabindex="-1"])'
  )
  if (focusable.length === 0) {
    e.preventDefault()
    return
  }
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault()
    last.focus()
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault()
    first.focus()
  }
}

onMounted(() => {
  previousFocus = document.activeElement
  dialogRef.value?.focus()
  document.addEventListener('keydown', trapFocus)
})

onUnmounted(() => {
  document.removeEventListener('keydown', trapFocus)
  if (previousFocus instanceof HTMLElement) previousFocus.focus()
})
</script>

<template>
  <div class="help-overlay visible" role="dialog" aria-labelledby="help-title" aria-modal="true" @click.self="emit('close')">
    <div ref="dialogRef" class="help-dialog" tabindex="-1">
      <h3 id="help-title">Keyboard Shortcuts</h3>
      <table>
        <tbody>
          <tr><td><kbd>j</kbd> <kbd>k</kbd></td><td>Navigate rows up / down</td></tr>
          <tr><td><kbd>Enter</kbd></td><td>Drill into selected row</td></tr>
          <tr><td><kbd>o</kbd></td><td>Open messages for row</td></tr>
          <tr><td><kbd>g</kbd> <kbd>G</kbd></td><td>Jump to first / last row</td></tr>
          <tr><td><kbd>n</kbd> <kbd>p</kbd></td><td>Next / previous page</td></tr>
          <tr><td><kbd>/</kbd></td><td>Focus search (or go to search)</td></tr>
          <tr><td><kbd>Esc</kbd></td><td>Blur search / close help</td></tr>
          <tr><td><kbd>&larr;</kbd> <kbd>&rarr;</kbd></td><td>Previous / next message</td></tr>
          <tr><td><kbd>Bksp</kbd></td><td>Go back</td></tr>
          <tr><td><kbd>H</kbd></td><td>Go to Dashboard</td></tr>
          <tr><td><kbd>B</kbd></td><td>Go to Browse</td></tr>
          <tr><td><kbd>?</kbd></td><td>Toggle this help</td></tr>
        </tbody>
      </table>
      <div class="help-close">Press <kbd>?</kbd> or <kbd>Esc</kbd> to close</div>
    </div>
  </div>
</template>
