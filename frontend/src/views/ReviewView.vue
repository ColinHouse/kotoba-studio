<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '@/api/client'
import type { CardFace as CardFaceT } from '@/api/types'
import CardFaceView from '@/components/review/CardFace.vue'
import RatingBar from '@/components/review/RatingBar.vue'
import { useAppStore } from '@/stores/app'
import { useDeviceStore } from '@/stores/device'

const app = useAppStore()
const device = useDeviceStore()
const queue = ref<CardFaceT[]>([])
const index = ref(0)
const revealed = ref(false)
const done = ref(0)
const loading = ref(true)
const shownAt = ref(Date.now())
const forecast = ref<{ date: string; count: number }[]>([])

const current = computed(() => queue.value[index.value] ?? null)

async function load() {
  loading.value = true
  try {
    const params = device.device ? `device_id=${device.device.id}` : `device_kind=${device.kind}`
    const r = await api.get<{ cards: CardFaceT[] }>(`/api/reviews/queue?${params}&limit=50`)
    queue.value = r.cards
    index.value = 0
    revealed.value = false
    shownAt.value = Date.now()
    if (!r.cards.length) forecast.value = (await api.get<{ days: { date: string; count: number }[] }>('/api/reviews/forecast')).days
  } catch (e) {
    app.fail(e)
  } finally {
    loading.value = false
  }
}

async function rate(rating: 1 | 2 | 3 | 4) {
  if (!current.value) return
  const card = current.value
  try {
    await api.post('/api/reviews', { card_id: card.id, rating, mode: 'scheduled', device_id: device.device?.id ?? null, duration_ms: Date.now() - shownAt.value })
    done.value += 1
    if (rating === 1) queue.value.push({ ...card })
    index.value += 1
    revealed.value = false
    shownAt.value = Date.now()
    if (!current.value) await load()
  } catch (e) {
    app.fail(e)
  }
}

function onKey(e: KeyboardEvent) {
  if (!current.value) return
  if (e.key === ' ' || e.code === 'Space' || e.key === 'Enter') {
    e.preventDefault()
    revealed.value = true
  } else if (revealed.value && ['1', '2', '3', '4'].includes(e.key)) {
    rate(Number(e.key) as 1 | 2 | 3 | 4)
  }
}

onMounted(() => {
  load()
  window.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-4">
    <header class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold">复习</h1>
      <span class="text-sm text-ink-3">本设备（{{ device.kind === 'mobile' ? '手机' : '电脑' }}）· 剩余 {{ Math.max(queue.length - index, 0) }} · 已复习 {{ done }}</span>
    </header>

    <div v-if="loading" class="card p-8 text-center text-sm text-ink-2">加载中…</div>

    <template v-else-if="current">
      <CardFaceView :face="current" :revealed="revealed" />
      <button v-if="!revealed" class="btn-primary w-full py-3 text-base" @click="revealed = true">显示答案（空格）</button>
      <RatingBar v-else :preview="current.preview" @rate="rate" />
      <p class="text-center text-xs text-ink-3">评分会交给 FSRS 安排下次复习；会后短测不影响这里的进度。</p>
    </template>

    <div v-else class="card space-y-3 p-8 text-center">
      <p class="text-lg font-semibold">{{ done ? `今天的复习完成了，共 ${done} 张。` : '这个设备上没有到期的卡片。' }}</p>
      <p class="text-sm text-ink-2">卡片按归属端分配：只有归属于本设备（或"任意"）的卡片会出现在这里。可在词条详情或设置中调整。</p>
      <ul v-if="forecast.length" class="mx-auto grid max-w-sm grid-cols-7 gap-1 text-xs">
        <li v-for="d in forecast" :key="d.date" class="rounded-lg bg-paper-2 p-1"><span class="block text-ink-3">{{ d.date.slice(5) }}</span><span class="font-semibold">{{ d.count }}</span></li>
      </ul>
      <div class="flex justify-center gap-2">
        <RouterLink to="/inbox" class="btn-outline">去收件箱建卡</RouterLink>
        <RouterLink to="/" class="btn-ghost">返回首页</RouterLink>
      </div>
    </div>
  </div>
</template>
