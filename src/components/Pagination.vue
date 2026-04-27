<script setup lang="ts">
defineProps<{
  page: number
  hasMore: boolean
}>()

defineEmits<{
  prev: []
  next: []
}>()
</script>

<template>
  <div v-if="page > 1 || hasMore" class="pagination">
    <button v-if="page > 1" type="button" class="pagination-btn" @click="$emit('prev')">Prev</button>
    <span class="page-info">Page {{ page }}</span>
    <button v-if="hasMore" type="button" class="pagination-btn" @click="$emit('next')">Next</button>
  </div>
</template>
