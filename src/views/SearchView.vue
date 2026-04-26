<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type MessageSummary, type TotalStats } from '../api/client'
import { formatCount } from '../utils/format'
import StatsBar from '../components/StatsBar.vue'
import MessageTable from '../components/MessageTable.vue'
import Pagination from '../components/Pagination.vue'
import { useMessageNav } from '../composables/useMessageNav'

const route = useRoute()
const router = useRouter()
const { storeMessageList } = useMessageNav()

const messages = ref<MessageSummary[]>([])
const stats = ref<TotalStats | null>(null)
const hasMore = ref(false)
const loading = ref(false)
const error = ref('')
const pageSize = 100

function qstr(key: string, fallback: string): string {
  const v = route.query[key]
  if (Array.isArray(v)) return String(v[0] ?? fallback)
  return v != null ? String(v) : fallback
}

const query = computed(() => qstr('q', ''))
const mode = computed(() => qstr('mode', 'fast'))
const page = computed(() => Math.max(1, parseInt(qstr('page', '1')) || 1))
const sortField = computed(() => qstr('sort', 'date'))
const sortDir = computed(() => qstr('dir', 'desc'))
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

let fetchId = 0

async function fetchData() {
  const currentFetchId = ++fetchId
  if (!query.value) {
    loading.value = true
    try {
      const res = await api.getFilteredMessages({
        sort: 'date',
        direction: 'desc',
        limit: '100',
      })
      if (currentFetchId !== fetchId) return
      messages.value = res.messages
      hasMore.value = false

      const statsRes = await api.getStats()
      if (currentFetchId !== fetchId) return
      stats.value = statsRes
    } catch (e: unknown) {
      if (currentFetchId !== fetchId) return
      error.value = e instanceof Error ? e.message : String(e)
      messages.value = []
    } finally {
      if (currentFetchId === fetchId) {
        loading.value = false
      }
    }
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
      if (currentFetchId !== fetchId) return
      messages.value = res.messages
      hasMore.value = res.has_more
    } else {
      const res = await api.searchFast(params)
      if (currentFetchId !== fetchId) return
      const allMessages = res.messages
      hasMore.value = res.total_count > offset + allMessages.length
      messages.value = allMessages.length > pageSize ? allMessages.slice(0, pageSize) : allMessages
      stats.value = res.stats ?? null
    }

    storeMessageList(messages.value.map(m => m.id))

    if (!stats.value) {
      const statsRes = await api.getStats()
      if (currentFetchId !== fetchId) return
      stats.value = statsRes
    }
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
        <button type="button" :class="['pill-sm', { active: mode === 'fast' }]" :disabled="mode === 'fast'" @click="toggleMode()">Fast</button>
        <button type="button" :class="['pill-sm', { active: mode === 'deep' }]" :disabled="mode === 'deep'" @click="toggleMode()">Deep</button>
        <span class="search-hint">
          {{ mode === 'fast' ? 'Searches subject and sender (faster)' : 'Searches full message body (slower)' }}
        </span>
        <span class="search-divider"></span>
        <button type="button" :class="['pill-sm', { active: hideDeleted }]" @click="toggleFilter('hide_deleted')">
          Hide Deleted
        </button>
        <button type="button" :class="['pill-sm', { active: attachments }]" @click="toggleFilter('attachments')">
          Attachments Only
        </button>
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
