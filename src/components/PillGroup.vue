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
    <a
      v-for="opt in options"
      :key="opt.value"
      href="#"
      :class="[size === 'small' ? 'pill-sm' : 'pill', { active: modelValue === opt.value }]"
      @click.prevent="$emit('update:modelValue', opt.value)"
    >
      {{ opt.label }}
    </a>
  </div>
</template>
