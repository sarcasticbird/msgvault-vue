<script setup lang="ts">
import type { MessageSummary } from '../api/client'
import { formatBytes, formatMessageDate } from '../utils/format'

defineProps<{
  messages: MessageSummary[]
  sortField?: string
  sortDir?: string
  sortable?: boolean
}>()

defineEmits<{ sort: [field: string] }>()

function sortIndicator(field: string, currentField?: string, dir?: string): string {
  if (currentField !== field) return ''
  return dir === 'asc' ? ' \u2191' : ' \u2193'
}
</script>

<template>
  <table class="data-table">
    <thead>
      <tr>
        <th>
          <a v-if="sortable" href="#" @click.prevent="$emit('sort', 'date')">
            Date{{ sortIndicator('date', sortField, sortDir) }}
          </a>
          <template v-else>Date</template>
        </th>
        <th>From</th>
        <th>
          <a v-if="sortable" href="#" @click.prevent="$emit('sort', 'subject')">
            Subject{{ sortIndicator('subject', sortField, sortDir) }}
          </a>
          <template v-else>Subject</template>
        </th>
        <th class="num">
          <a v-if="sortable" href="#" @click.prevent="$emit('sort', 'size')">
            Size{{ sortIndicator('size', sortField, sortDir) }}
          </a>
          <template v-else>Size</template>
        </th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="msg in messages" :key="msg.id">
        <td class="date-cell">{{ formatMessageDate(msg.sent_at) }}</td>
        <td class="from-cell">{{ msg.from }}</td>
        <td>
          <router-link :to="`/messages/${msg.id}`">
            <template v-if="msg.subject">{{ msg.subject }}</template>
            <em v-else>(no subject)</em>
          </router-link>
          <span v-if="msg.has_attachments" class="attachment-badge" title="attachments">
            📎
          </span>
        </td>
        <td class="num">{{ formatBytes(msg.size_bytes) }}</td>
      </tr>
    </tbody>
  </table>
</template>
