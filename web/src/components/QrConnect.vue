<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '@/api/client'
import type { ConnectInfo } from '@/api/types'

const info = ref<ConnectInfo | null>(null)
const error = ref('')
onMounted(async () => {
  try {
    info.value = await api.get<ConnectInfo>('/api/connect-info')
  } catch (e) {
    error.value = (e as Error).message
  }
})
</script>

<template>
  <div class="flex flex-col gap-4 md:flex-row md:items-start">
    <div v-if="info" class="w-40 shrink-0 rounded-xl bg-white p-2" v-html="info.qr_svg" />
    <div class="text-sm">
      <p class="font-semibold">用手机扫码打开，然后"添加到主屏幕"即可作为 App 使用。</p>
      <ul v-if="info" class="mt-2 space-y-1">
        <li v-for="u in info.urls" :key="u" class="font-mono text-ink-2">{{ u }}</li>
        <li v-if="!info.urls.length" class="text-ink-3">未检测到局域网地址</li>
      </ul>
      <p v-if="info?.hint" class="mt-2 rounded-lg bg-accent/10 p-2 text-accent-2">{{ info.hint }}</p>
      <p v-if="error" class="text-red-600">{{ error }}</p>
    </div>
  </div>
</template>
