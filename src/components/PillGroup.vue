<script setup lang="ts">
defineProps<{
  options: { label: string; value: string }[]
  modelValue: string
  size?: 'normal' | 'small'
}>()

defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<template>
  <div class="pill-group">
    <button
      v-for="opt in options"
      :key="opt.value"
      type="button"
      :class="[size === 'small' ? 'pill-sm' : 'pill', { active: modelValue === opt.value }]"
      @click="$emit('update:modelValue', opt.value)"
    >
      {{ opt.label }}
    </button>
  </div>
</template>
