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
const remaining = computed(() => Math.max(queue.value.length - index.value, 0))
const progress = computed(() => {
  const total = done.value + remaining.value
  return total ? Math.round((done.value / total) * 100) : 0
})
const deviceLabel = computed(() => (device.kind === 'mobile' ? '手机' : '电脑'))

async function load() {
  loading.value = true
  try {
    await device.ensureRegistered()
    const params = device.device ? `device_id=${device.device.id}` : `device_kind=${device.kind}`
    const r = await api.get<{ cards: CardFaceT[] }>(`/api/reviews/queue?${params}&limit=50`)
    queue.value = r.cards
    index.value = 0
    revealed.value = false
    shownAt.value = Date.now()
    if (!r.cards.length) {
      forecast.value = (
        await api.get<{ days: { date: string; count: number }[] }>('/api/reviews/forecast')
      ).days
    }
  } catch (e) {
    app.fail(e)
  } finally {
    loading.value = false
  }
}

async function rate(rating: 1 | 2 | 3 | 4) {
  const card = current.value
  if (!card) return
  try {
    await api.post('/api/reviews', {
      card_id: card.id,
      rating,
      mode: 'scheduled',
      device_id: device.device?.id ?? null,
      duration_ms: Date.now() - shownAt.value,
    })
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

const maxForecast = computed(() => Math.max(1, ...forecast.value.map((d) => d.count)))
</script>

<template>
  <div class="flex min-h-[calc(100dvh-160px)] flex-col md:min-h-0">
    <header class="flex items-baseline justify-between gap-3">
      <h1 class="page-title text-[27px] md:text-[32px]">复习</h1>
      <span class="num text-[12px] text-ink-50 md:text-[13px]">
        本设备（{{ deviceLabel }}）· 剩余 {{ remaining }} · 已复习 {{ done }}
      </span>
    </header>
    <div class="mt-2.5 h-0.5 bg-rule">
      <div class="h-0.5 bg-accent transition-[width]" :style="{ width: `${progress}%` }" />
    </div>

    <p v-if="loading" class="mt-10 text-center text-[13px] text-ink-35">加载中…</p>

    <template v-else-if="current">
      <div class="flex flex-1 flex-col justify-center py-5">
        <CardFaceView :face="current" :revealed="revealed" />
      </div>

      <div class="flex items-end gap-[18px]">
        <div class="flex-1">
          <button
            v-if="!revealed"
            type="button"
            class="flex h-[58px] w-full items-center justify-center gap-2.5 rounded-ui border border-accent font-head text-[19px] text-accent hover:bg-accent-100"
            @click="revealed = true"
          >
            显示答案<span class="text-[12px] tracking-wider text-ink-50">空格</span>
          </button>
          <RatingBar v-else :preview="current.preview" @rate="rate" />
        </div>
        <div
          class="hidden w-[190px] shrink-0 border-l border-divider pl-4 text-[11px] leading-[1.9] text-ink-35 md:block"
        >
          <p class="kicker mb-0.5 text-ink-50">键盘</p>
          <p class="m-0">空格 显示答案</p>
          <p class="num m-0">1／2／3／4 评分</p>
        </div>
      </div>
      <p class="mt-2.5 mb-0 text-center text-[11px] text-ink-35">
        评分交给 FSRS 安排下次复习；会后短测不影响这里的进度。
      </p>
    </template>

    <div v-else class="mt-8">
      <p class="m-0 font-head text-[25px] leading-snug">
        {{ done ? `今天的复习完成了，共 ${done} 张。` : '这个设备上没有到期的卡片。' }}
      </p>
      <p class="mt-2 mb-0 text-[13px] leading-relaxed text-ink-50">
        卡片按归属端分配：只有归属于本设备（或"任意"）的卡片会出现在这里。可在词条详情或设置中调整。
      </p>

      <section v-if="forecast.length" class="mt-7">
        <p class="kicker">记忆日历 · 未来一周到期</p>
        <div class="mt-3.5 flex h-[74px] items-end gap-2.5 border-b border-divider">
          <div
            v-for="(d, i) in forecast"
            :key="d.date"
            class="flex flex-1 flex-col items-center justify-end gap-1.5"
          >
            <span
              class="num text-[11px]"
              :class="
                i === 0 ? 'font-semibold text-accent' : d.count ? 'text-ink-50' : 'text-ink-35'
              "
              >{{ d.count || '·' }}</span
            >
            <div
              class="w-full"
              :style="{
                height: `${d.count ? Math.max(4, Math.round((d.count / maxForecast) * 56)) : 1}px`,
                background: d.count
                  ? i === 0
                    ? 'var(--accent)'
                    : 'transparent'
                  : 'var(--divider)',
                border: d.count && i > 0 ? '1px solid var(--accent)' : 'none',
              }"
            />
          </div>
        </div>
        <div class="mt-1.5 flex gap-2.5">
          <span
            v-for="(d, i) in forecast"
            :key="d.date"
            class="num flex-1 text-center text-[10px]"
            :class="i === 0 ? 'font-semibold text-accent' : 'text-ink-35'"
            >{{ Number(d.date.slice(8, 10)) }}</span
          >
        </div>
      </section>

      <div class="mt-7 flex gap-2.5">
        <RouterLink to="/inbox" class="btn btn-primary">去收件箱建卡</RouterLink>
        <RouterLink to="/" class="btn btn-secondary">返回首页</RouterLink>
      </div>
    </div>
  </div>
</template>
