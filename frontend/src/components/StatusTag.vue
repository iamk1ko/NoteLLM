<script setup lang="ts">
type StatusType = 'success' | 'waiting' | 'error'

defineProps<{ label: string; type: StatusType }>()
</script>

<template>
  <span class="status-pill" :class="type">
    <span>{{ label }}</span>
  </span>
</template>
