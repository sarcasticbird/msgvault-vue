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
    <a v-if="page > 1" href="#" @click.prevent="$emit('prev')">Prev</a>
    <span class="page-info">Page {{ page }}</span>
    <a v-if="hasMore" href="#" @click.prevent="$emit('next')">Next</a>
  </div>
</template>
