<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type AggregateRow, type TotalStats } from '../api/client'
import { formatCount, formatBytes } from '../utils/format'
import StatsBar from '../components/StatsBar.vue'
import PillGroup from '../components/PillGroup.vue'

const route = useRoute()
const router = useRouter()

const stats = ref<TotalStats | null>(null)
const rows = ref<AggregateRow[]>([])
const loading = ref(true)

const viewTypes = [
  { label: 'Senders', value: 'senders' },
  { label: 'Names', value: 'sender_names' },
  { label: 'Recipients', value: 'recipients' },
  { label: 'Rcpt Names', value: 'recipient_names' },
  { label: 'Domains', value: 'domains' },
  { label: 'Labels', value: 'labels' },
  { label: 'Time', value: 'time' },
]

const granularities = [
  { label: 'Year', value: 'year' },
  { label: 'Month', value: 'month' },
  { label: 'Day', value: 'day' },
]

const viewType = computed(() => (route.query.view as string) || 'senders')
const sortField = computed(() => (route.query.sort as string) || 'count')
const sortDir = computed(() => (route.query.dir as string) || 'desc')
const granularity = computed(() => (route.query.granularity as string) || 'year')
const accountId = computed(() => (route.query.account as string) || '')
const attachments = computed(() => route.query.attachments === '1')
const hideDeleted = computed(() => route.query.hide_deleted === '1')

const drillFilters = computed(() => {
  const keys = ['sender', 'sender_name', 'recipient', 'recipient_name', 'domain', 'label', 'time_period']
  const filters: Record<string, string> = {}
  for (const k of keys) {
    if (route.query[k] !== undefined) filters[k] = (route.query[k] as string) ?? ''
  }
  return filters
})

const isDrill = computed(() => Object.keys(drillFilters.value).length > 0)

function updateQuery(updates: Record<string, string | undefined>) {
  const q = { ...route.query, ...updates }
  for (const [k, v] of Object.entries(q)) {
    if (v === undefined || v === '') delete q[k]
  }
  router.push({ path: '/browse', query: q })
}

function setView(v: string) { updateQuery({ view: v, sort: undefined, dir: undefined }) }
function setGranularity(g: string) { updateQuery({ granularity: g }) }
function toggleSort(field: string) {
  const dir = sortField.value === field && sortDir.value === 'desc' ? 'asc' : 'desc'
  updateQuery({ sort: field, dir })
}
function toggleFilter(key: string) {
  if (route.query[key]) updateQuery({ [key]: undefined })
  else updateQuery({ [key]: '1' })
}

function drillUrl(key: string) {
  const filterKey = viewTypeToFilterParam(viewType.value)
  const q: Record<string, string> = {
    view: viewType.value,
    sort: sortField.value,
    dir: sortDir.value,
    [filterKey]: key,
    ...drillFilters.value,
  }
  if (viewType.value === 'time') q.granularity = granularity.value
  if (accountId.value) q.account = accountId.value
  if (attachments.value) q.attachments = '1'
  if (hideDeleted.value) q.hide_deleted = '1'
  return { path: '/browse', query: q }
}

function messagesUrl(key: string) {
  const filterKey = viewTypeToFilterParam(viewType.value)
  const q: Record<string, string> = {
    [filterKey]: key,
    ...drillFilters.value,
  }
  if (viewType.value === 'time' && granularity.value) q.granularity = granularity.value
  if (accountId.value) q.account = accountId.value
  if (attachments.value) q.attachments = '1'
  if (hideDeleted.value) q.hide_deleted = '1'
  return { path: '/messages', query: q }
}

function viewTypeToFilterParam(vt: string): string {
  const map: Record<string, string> = {
    senders: 'sender', sender_names: 'sender_name', recipients: 'recipient',
    recipient_names: 'recipient_name', domains: 'domain', labels: 'label', time: 'time_period',
  }
  return map[vt] || 'sender'
}

function sortIndicator(field: string): string {
  if (sortField.value !== field) return ''
  return sortDir.value === 'asc' ? ' \u2191' : ' \u2193'
}

let fetchId = 0

async function fetchData() {
  const currentFetchId = ++fetchId
  loading.value = true
  try {
    const params: Record<string, string> = {
      view_type: viewType.value,
      sort: sortField.value,
      direction: sortDir.value,
      limit: '500',
    }
    if (viewType.value === 'time') params.time_granularity = granularity.value
    if (accountId.value) params.source_id = accountId.value
    if (attachments.value) params.attachments_only = 'true'
    if (hideDeleted.value) params.hide_deleted = 'true'

    for (const [k, v] of Object.entries(drillFilters.value)) {
      params[k] = v
    }

    const [aggRes, statsRes] = await Promise.all([
      isDrill.value ? api.getSubAggregates(params) : api.getAggregates(params),
      api.getStats(),
    ])
    if (currentFetchId !== fetchId) return
    rows.value = aggRes.rows
    stats.value = statsRes
  } catch (e) {
    if (currentFetchId !== fetchId) return
    rows.value = []
  } finally {
    if (currentFetchId === fetchId) {
      loading.value = false
    }
  }
}

watch(() => route.query, fetchData, { deep: true, immediate: true })
</script>

<template>
  <div>
    <StatsBar v-if="stats" :stats="stats" />

    <div class="toolbar">
      <div class="toolbar-left">
        <PillGroup :options="viewTypes" :model-value="viewType" @update:model-value="setView" />
        <PillGroup v-if="viewType === 'time'" :options="granularities" :model-value="granularity"
          size="small" @update:model-value="setGranularity" />
      </div>
      <div class="toolbar-right">
        <a href="#" :class="['pill-sm', { active: attachments }]" @click.prevent="toggleFilter('attachments')">
          Attachments Only
        </a>
        <a href="#" :class="['pill-sm', { active: hideDeleted }]" @click.prevent="toggleFilter('hide_deleted')">
          Hide Deleted
        </a>
      </div>
    </div>

    <nav v-if="isDrill" class="breadcrumb">
      <router-link :to="{ path: '/browse', query: { view: viewType } }">Browse</router-link>
      <span v-for="(v, k) in drillFilters" :key="k">
        <span> / </span>
        <strong style="color: var(--fg);">{{ k }}: {{ v || '(empty)' }}</strong>
      </span>
    </nav>

    <div v-if="rows.length === 0 && !loading" class="empty-state">
      <div class="empty-state-title">No data</div>
      <p>No messages match the current filters.</p>
    </div>

    <table v-else class="data-table">
      <thead>
        <tr>
          <th><a href="#" @click.prevent="toggleSort('name')">Name{{ sortIndicator('name') }}</a></th>
          <th class="num"><a href="#" @click.prevent="toggleSort('count')">Count{{ sortIndicator('count') }}</a></th>
          <th class="num"><a href="#" @click.prevent="toggleSort('size')">Size{{ sortIndicator('size') }}</a></th>
          <th class="num"><a href="#" @click.prevent="toggleSort('attachment_size')">Attachments{{ sortIndicator('attachment_size') }}</a></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row.key">
          <td>
            <router-link :to="drillUrl(row.key)">
              <em v-if="!row.key">(empty)</em>
              <template v-else>{{ row.key }}</template>
            </router-link>
          </td>
          <td class="num">
            <router-link :to="messagesUrl(row.key)">{{ formatCount(row.count) }}</router-link>
          </td>
          <td class="num">{{ formatBytes(row.total_size) }}</td>
          <td class="num">
            <template v-if="row.attachment_count > 0">
              {{ formatCount(row.attachment_count) }} ({{ formatBytes(row.attachment_size) }})
            </template>
            <template v-else>-</template>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-if="rows.length > 0" class="result-count" style="margin-top: 8px;">
      Showing {{ formatCount(rows.length) }} of {{ formatCount(rows[0]?.total_unique ?? rows.length) }} unique entries
    </div>
  </div>
</template>
