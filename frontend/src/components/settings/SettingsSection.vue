<script setup lang="ts">
defineProps<{ title: string; hint?: string }>()
</script>

<template>
  <section class="space-y-3">
    <div>
      <h2 class="font-semibold">{{ title }}</h2>
      <p v-if="hint" class="text-xs text-ink-3">{{ hint }}</p>
    </div>
    <slot />
  </section>
</template>
