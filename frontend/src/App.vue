<script setup lang="ts">
import { onMounted } from 'vue'
import AppShell from '@/layouts/AppShell.vue'
import { useAppStore } from '@/stores/app'
import { useDeviceStore } from '@/stores/device'

const app = useAppStore()
const device = useDeviceStore()

onMounted(async () => {
  await app.refreshHealth()
  await device.ensureRegistered()
  await app.refreshSettings()
})
</script>

<template>
  <AppShell />
</template>
