<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
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
const pageSize = 100

const page = computed(() => parseInt(route.query.page as string) || 1)
const sortField = computed(() => (route.query.sort as string) || 'date')
const sortDir = computed(() => (route.query.dir as string) || 'desc')

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
    if (route.query[item.key] !== undefined) {
      const v = (route.query[item.key] as string) || '(empty)'
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

async function fetchData() {
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
      if (route.query[k] !== undefined) params[k] = route.query[k] as string
    }
    if (route.query.account) params.source_id = route.query.account as string
    if (route.query.attachments === '1') params.attachments_only = 'true'
    if (route.query.hide_deleted === '1') params.hide_deleted = 'true'

    const res = await api.getFilteredMessages(params)
    hasMore.value = res.has_more
    messages.value = res.messages

    storeMessageList(messages.value.map(m => m.id))
  } catch {
    messages.value = []
  } finally {
    loading.value = false
  }
}

watch(() => route.query, fetchData, { deep: true })
onMounted(fetchData)
</script>

<template>
  <div>
    <nav class="breadcrumb">
      <router-link to="/browse">Browse</router-link>
      <span> / </span>
      <strong style="color: var(--fg);">{{ filterSummary }}</strong>
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
