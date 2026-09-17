<script setup lang="ts">
withDefaults(
  defineProps<{
    width?: string
    height?: string
    rounded?: string
    count?: number
  }>(),
  {
    width: '100%',
    height: '1.25rem',
    rounded: 'var(--radius-chip)',
    count: 1,
  },
)
</script>

<template>
  <div v-if="count > 1" class="flex flex-col gap-2.5">
    <div
      v-for="i in count"
      :key="i"
      class="skeleton-block"
      :style="{ width, height, borderRadius: rounded }"
    />
  </div>
  <div v-else class="skeleton-block" :style="{ width, height, borderRadius: rounded }" />
</template>

<style scoped>
.skeleton-block {
  background-color: var(--surface);
  animation: skeleton-breathe 2.4s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes skeleton-breathe {
  0%,
  100% {
    opacity: 0.6;
  }
  50% {
    opacity: 0.95;
  }
}
</style>
