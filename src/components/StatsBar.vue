<script setup lang="ts">
import type { TotalStats } from '../api/client'
import { formatCount, formatBytes } from '../utils/format'

defineProps<{ stats: TotalStats }>()
</script>

<template>
  <div class="stats-bar">
    <div class="stat-item">
      <span class="stat-value">{{ formatCount(stats.message_count) }}</span> msgs
    </div>
    <div class="stat-item">
      <span class="stat-value">{{ formatBytes(stats.total_size) }}</span> total
    </div>
    <div class="stat-item">
      <span class="stat-value">{{ formatCount(stats.attachment_count) }}</span> attachments
    </div>
  </div>
</template>
