<script setup lang="ts">
defineProps<{ title: string; hint?: string }>()
</script>

<template>
  <div class="card flex flex-col items-center gap-2 px-6 py-10 text-center">
    <p class="text-base font-semibold">{{ title }}</p>
    <p v-if="hint" class="max-w-md text-sm text-ink-2">{{ hint }}</p>
    <div class="mt-2"><slot /></div>
  </div>
</template>
