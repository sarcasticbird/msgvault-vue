<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type MessageSummary, type TotalStats } from '../api/client'
import { formatCount } from '../utils/format'
import StatsBar from '../components/StatsBar.vue'
import MessageTable from '../components/MessageTable.vue'
import Pagination from '../components/Pagination.vue'

const route = useRoute()
const router = useRouter()

const messages = ref<MessageSummary[]>([])
const stats = ref<TotalStats | null>(null)
const hasMore = ref(false)
const loading = ref(false)
const pageSize = 100

const query = computed(() => (route.query.q as string) || '')
const mode = computed(() => (route.query.mode as string) || 'fast')
const page = computed(() => parseInt(route.query.page as string) || 1)
const sortField = computed(() => (route.query.sort as string) || 'date')
const sortDir = computed(() => (route.query.dir as string) || 'desc')
const hideDeleted = computed(() => route.query.hide_deleted === '1')
const attachments = computed(() => route.query.attachments === '1')

function updateQuery(updates: Record<string, string | undefined>) {
  const q = { ...route.query, ...updates }
  for (const [k, v] of Object.entries(q)) {
    if (v === undefined || v === '') delete q[k]
  }
  router.push({ path: '/search', query: q })
}

function submitSearch(e: Event) {
  const form = e.target as HTMLFormElement
  const input = form.querySelector('input[name="q"]') as HTMLInputElement
  updateQuery({ q: input.value, page: undefined })
}

function toggleMode() {
  updateQuery({ mode: mode.value === 'fast' ? 'deep' : 'fast', page: undefined })
}

function toggleFilter(key: string) {
  if (route.query[key]) updateQuery({ [key]: undefined, page: undefined })
  else updateQuery({ [key]: '1', page: undefined })
}

function toggleSort(field: string) {
  const dir = sortField.value === field && sortDir.value === 'desc' ? 'asc' : 'desc'
  updateQuery({ sort: field, dir, page: undefined })
}

function goPage(p: number) {
  updateQuery({ page: p > 1 ? String(p) : undefined })
}

async function fetchData() {
  if (!query.value) {
    loading.value = true
    try {
      const res = await api.getFilteredMessages({
        sort: 'date',
        direction: 'desc',
        limit: '100',
      })
      messages.value = res.messages
      hasMore.value = false

      const statsRes = await api.getStats()
      stats.value = statsRes
    } catch { messages.value = [] }
    finally { loading.value = false }
    return
  }

  loading.value = true
  try {
    const offset = (page.value - 1) * pageSize
    const params: Record<string, string> = {
      q: query.value,
      offset: String(offset),
      limit: String(pageSize + 1),
    }
    if (hideDeleted.value) params.hide_deleted = 'true'
    if (attachments.value) params.attachments_only = 'true'
    if (sortField.value !== 'date') params.sort = sortField.value
    if (sortDir.value !== 'desc') params.direction = sortDir.value

    if (mode.value === 'deep') {
      const res = await api.searchDeep(params)
      messages.value = res.messages
      hasMore.value = res.has_more
    } else {
      const res = await api.searchFast(params)
      messages.value = res.messages
      stats.value = res.stats ?? null
      hasMore.value = messages.value.length > pageSize
      if (hasMore.value) messages.value = messages.value.slice(0, pageSize)
    }

    if (!stats.value) {
      stats.value = await api.getStats()
    }
  } catch { messages.value = [] }
  finally { loading.value = false }
}

watch(() => route.query, fetchData, { deep: true })
onMounted(fetchData)
</script>

<template>
  <div>
    <StatsBar v-if="stats" :stats="stats" />

    <form class="search-form" @submit.prevent="submitSearch">
      <div class="search-row">
        <input
          type="text"
          name="q"
          :value="query"
          placeholder="Search messages... (e.g. from:user@example.com invoice)"
          aria-label="Search messages"
          autofocus
          class="search-input"
        />
        <button type="submit" class="search-btn">Search</button>
      </div>
      <div class="search-controls">
        <span :class="['pill-sm', { active: mode === 'fast' }]" @click="mode !== 'fast' && toggleMode()">Fast</span>
        <span :class="['pill-sm', { active: mode === 'deep' }]" @click="mode !== 'deep' && toggleMode()">Deep</span>
        <span class="search-hint">
          {{ mode === 'fast' ? 'Searches subject and sender (faster)' : 'Searches full message body (slower)' }}
        </span>
        <span class="search-divider"></span>
        <a href="#" :class="['pill-sm', { active: hideDeleted }]" @click.prevent="toggleFilter('hide_deleted')">
          Hide Deleted
        </a>
        <a href="#" :class="['pill-sm', { active: attachments }]" @click.prevent="toggleFilter('attachments')">
          Attachments Only
        </a>
      </div>
    </form>

    <div v-if="!query && !loading && messages.length > 0" class="result-count">Recent messages</div>

    <div v-if="query && !loading && messages.length === 0" class="empty-state">
      <div class="empty-state-title">No results</div>
      <p>
        No messages match "{{ query }}"
        <template v-if="mode === 'fast'">
          — try <a href="#" @click.prevent="toggleMode()">deep search</a> to include message bodies
        </template>
      </p>
    </div>

    <div v-if="!query && !loading && messages.length === 0" class="empty-state">
      <div class="empty-state-title">Search your archive</div>
      <p>Use Gmail-like syntax: from:user@example.com, subject:invoice, has:attachment, before:2024/01/01</p>
    </div>

    <template v-if="messages.length > 0">
      <div v-if="query" class="result-count">
        Showing {{ formatCount(messages.length) }} results
        <template v-if="page > 1">(page {{ page }})</template>
      </div>

      <MessageTable
        :messages="messages"
        :sort-field="sortField"
        :sort-dir="sortDir"
        :sortable="mode === 'fast' && !!query"
        @sort="toggleSort"
      />

      <Pagination v-if="query"
        :page="page"
        :has-more="hasMore"
        @prev="goPage(page - 1)"
        @next="goPage(page + 1)"
      />
    </template>
  </div>
</template>
