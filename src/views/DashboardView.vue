<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, type TotalStats, type AccountInfo } from '../api/client'
import { formatCount, formatBytes, formatSyncTime } from '../utils/format'
import StatsBar from '../components/StatsBar.vue'

const stats = ref<TotalStats | null>(null)
const accounts = ref<AccountInfo[]>([])
const syncingAccounts = ref<Set<string>>(new Set())
const error = ref('')

onMounted(async () => {
  try {
    const [statsRes, accountsRes] = await Promise.all([
      api.getStats(),
      api.getAccounts(),
    ])
    stats.value = statsRes
    accounts.value = accountsRes.accounts
  } catch (e: any) {
    error.value = e.message
  }
})

async function triggerSync(email: string) {
  syncingAccounts.value.add(email)
  try {
    await api.triggerSync(email)
    pollSync(email)
  } catch (e: any) {
    syncingAccounts.value.delete(email)
  }
}

async function pollSync(email: string) {
  const poll = setInterval(async () => {
    try {
      const status = await api.getSchedulerStatus()
      const acct = status.accounts.find(a => a.email === email)
      if (!acct || !acct.running) {
        clearInterval(poll)
        syncingAccounts.value.delete(email)
        const accountsRes = await api.getAccounts()
        accounts.value = accountsRes.accounts
      }
    } catch {
      clearInterval(poll)
      syncingAccounts.value.delete(email)
    }
  }, 2000)
}
</script>

<template>
  <div>
    <StatsBar v-if="stats" :stats="stats" />
    <div v-if="stats" class="dashboard-stats">
      <div class="stat-card">
        <div class="stat-card-value">{{ formatCount(stats.message_count) }}</div>
        <div class="stat-card-label">Messages</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-value">{{ formatBytes(stats.total_size) }}</div>
        <div class="stat-card-label">Total Size</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-value">{{ formatCount(stats.attachment_count) }}</div>
        <div class="stat-card-label">Attachments</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-value">{{ formatBytes(stats.attachment_size) }}</div>
        <div class="stat-card-label">Attachment Size</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-value">{{ formatCount(stats.label_count) }}</div>
        <div class="stat-card-label">Labels</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-value">{{ formatCount(stats.account_count) }}</div>
        <div class="stat-card-label">Accounts</div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">Accounts</div>
      <div v-if="accounts.length === 0" class="empty-state">
        <div class="empty-state-title">No accounts configured</div>
        <p>Run <code>msgvault add-account you@gmail.com</code> to get started.</p>
      </div>
      <ul v-else class="account-list">
        <li v-for="acct in accounts" :key="acct.email" class="account-item">
          <span class="account-email">{{ acct.email }}</span>
          <span class="account-sync-group">
            <span class="account-sync">last sync: {{ formatSyncTime(acct.last_sync_with_data_at ?? null) }}</span>
            <template v-if="syncingAccounts.has(acct.email)">
              <span class="sync-running"><span class="sync-spinner"></span> syncing</span>
            </template>
            <button v-else class="btn-sync" @click="triggerSync(acct.email)">sync</button>
          </span>
        </li>
      </ul>
    </div>

    <div class="card">
      <div class="card-title">Quick Links</div>
      <ul class="account-list">
        <li class="account-item"><router-link to="/browse?view=senders">Top Senders</router-link></li>
        <li class="account-item"><router-link to="/browse?view=domains">Top Domains</router-link></li>
        <li class="account-item"><router-link to="/browse?view=labels">Labels</router-link></li>
        <li class="account-item"><router-link to="/browse?view=time">Timeline</router-link></li>
      </ul>
    </div>

    <div v-if="error" class="flash-notice">{{ error }}</div>
  </div>
</template>
