<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type MessageSummary } from '../api/client'
import { formatCount } from '../utils/format'
import MessageTable from '../components/MessageTable.vue'
import Pagination from '../components/Pagination.vue'
import { useMessageNav } from '../composables/useMessageNav'

const route = useRoute()
const router = useRouter()
const { storeMessageList } = useMessageNav()

const messages = ref<MessageSummary[]>([])
const hasMore = ref(false)
const loading = ref(true)
const error = ref('')
const pageSize = 100

function qstr(key: string, fallback: string): string {
  const v = route.query[key]
  if (Array.isArray(v)) return String(v[0] ?? fallback)
  return v != null ? String(v) : fallback
}

const page = computed(() => Math.max(1, parseInt(qstr('page', '1')) || 1))
const sortField = computed(() => qstr('sort', 'date'))
const sortDir = computed(() => qstr('dir', 'desc'))

const filterSummary = computed(() => {
  const order = [
    { key: 'sender', label: 'Sender' },
    { key: 'sender_name', label: 'Name' },
    { key: 'recipient', label: 'Recipient' },
    { key: 'recipient_name', label: 'Recipient Name' },
    { key: 'domain', label: 'Domain' },
    { key: 'label', label: 'Label' },
    { key: 'time_period', label: 'Period' },
  ]
  const parts: string[] = []
  for (const item of order) {
    if (route.query[item.key] != null) {
      const v = qstr(item.key, '') || '(empty)'
      parts.push(`${item.label}: ${v}`)
    }
  }
  return parts.length > 0 ? parts.join(' / ') : 'All Messages'
})

function updateQuery(updates: Record<string, string | undefined>) {
  const q = { ...route.query, ...updates }
  for (const [k, v] of Object.entries(q)) {
    if (v === undefined || v === '') delete q[k]
  }
  router.push({ path: '/messages', query: q })
}

function toggleSort(field: string) {
  const dir = sortField.value === field && sortDir.value === 'desc' ? 'asc' : 'desc'
  updateQuery({ sort: field, dir, page: undefined })
}

function goPage(p: number) {
  updateQuery({ page: p > 1 ? String(p) : undefined })
}

let fetchId = 0

async function fetchData() {
  const currentFetchId = ++fetchId
  loading.value = true
  try {
    const params: Record<string, string> = {
      offset: String((page.value - 1) * pageSize),
      limit: String(pageSize + 1),
      sort: sortField.value,
      direction: sortDir.value === 'asc' ? 'asc' : 'desc',
    }

    const filterKeys = ['sender', 'sender_name', 'recipient', 'recipient_name', 'domain', 'label', 'time_period', 'granularity', 'conversation_id']
    for (const k of filterKeys) {
      if (route.query[k] != null) params[k] = qstr(k, '')
    }
    if (route.query.account) params.source_id = qstr('account', '')
    if (route.query.attachments === '1') params.attachments_only = 'true'
    if (route.query.hide_deleted === '1') params.hide_deleted = 'true'

    const res = await api.getFilteredMessages(params)
    if (currentFetchId !== fetchId) return
    hasMore.value = res.messages.length > pageSize
    messages.value = hasMore.value ? res.messages.slice(0, pageSize) : res.messages

    storeMessageList(messages.value.map(m => m.id))
  } catch (e: unknown) {
    if (currentFetchId !== fetchId) return
    error.value = e instanceof Error ? e.message : String(e)
    messages.value = []
  } finally {
    if (currentFetchId === fetchId) {
      loading.value = false
    }
  }
}

watch(() => route.query, () => { error.value = ''; fetchData() }, { deep: true, immediate: true })
</script>

<template>
  <div>
    <div v-if="error" class="flash-notice">{{ error }}</div>
    <nav class="breadcrumb">
      <router-link to="/browse">Browse</router-link>
      <span> / </span>
      <strong class="text-fg">{{ filterSummary }}</strong>
    </nav>

    <div v-if="messages.length === 0 && !loading" class="empty-state">
      <div class="empty-state-title">No messages</div>
      <p>No messages match the current filters.</p>
    </div>

    <template v-else>
      <div class="result-count">
        Showing {{ formatCount(messages.length) }} messages
        <template v-if="page > 1">(page {{ page }})</template>
      </div>

      <MessageTable
        :messages="messages"
        :sort-field="sortField"
        :sort-dir="sortDir"
        :sortable="true"
        @sort="toggleSort"
      />

      <Pagination
        :page="page"
        :has-more="hasMore"
        @prev="goPage(page - 1)"
        @next="goPage(page + 1)"
      />
    </template>
  </div>
</template>
