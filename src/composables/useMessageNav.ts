import { ref } from 'vue'

const messageIds = ref<number[]>([])

export function useMessageNav() {
  function storeMessageList(ids: number[]) {
    messageIds.value = ids
  }

  function getNavigation(currentId: number) {
    const idx = messageIds.value.indexOf(currentId)
    if (idx < 0) return { prev: null, next: null, position: '', total: 0 }
    return {
      prev: idx > 0 ? messageIds.value[idx - 1] : null,
      next: idx < messageIds.value.length - 1 ? messageIds.value[idx + 1] : null,
      position: `${idx + 1} / ${messageIds.value.length}`,
      total: messageIds.value.length,
    }
  }

  return { storeMessageList, getNavigation }
}
