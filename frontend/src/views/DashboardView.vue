<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { api } from '@/api/client'
import type { CardStats, DictStatus, Line, Session, Source } from '@/api/types'
import MemoryCalendar from '@/components/common/MemoryCalendar.vue'
import SetupChecklist from '@/components/common/SetupChecklist.vue'
import { useAppStore } from '@/stores/app'
import { useDeviceStore } from '@/stores/device'
import { relTime } from '@/utils/format'
import { checklistVisible, setupProgress } from '@/utils/setup'

const DISMISSED_KEY = 'kotoba.setup_dismissed'

const app = useAppStore()
const device = useDeviceStore()
const router = useRouter()

const stats = ref<CardStats | null>(null)
const inbox = ref<Line[]>([])
const sources = ref<Source[]>([])
const sessions = ref<Session[]>([])
const forecast = ref<{ date: string; count: number }[]>([])
const queueCount = ref<number | null>(null)
const dictInstalled = ref(false)
const hookConnected = ref(false)
const setupDismissed = ref(readDismissed())

function readDismissed(): boolean {
  try {
    return localStorage.getItem(DISMISSED_KEY) === '1'
  } catch {
    return false // private mode: show it; the button will just not persist
  }
}

const days = computed(() => (device.kind === 'mobile' ? 7 : 14))

const progress = computed(() =>
  setupProgress(dictInstalled.value, sources.value, stats.value?.total ?? 0, hookConnected.value),
)
const showChecklist = computed(() => checklistVisible(progress.value, setupDismissed.value))

onMounted(async () => {
  try {
    await device.ensureRegistered()
    const [s, i, src, ses, fc, q, dict, hooks] = await Promise.all([
      api.get<CardStats>('/api/cards/stats'),
      api.get<Line[]>('/api/lines?status=inbox&limit=200'),
      api.get<Source[]>('/api/sources'),
      api.get<Session[]>('/api/sessions?limit=5'),
      api.get<{ days: { date: string; count: number }[] }>(
        `/api/reviews/forecast?days=${days.value}`,
      ),
      api.get<{ cards: unknown[] }>(`/api/reviews/queue?device_kind=${device.kind}&limit=200`),
      api.get<DictStatus>('/api/dict/status'),
      api.get<{ connected: boolean }[]>('/api/hooks'),
    ])
    stats.value = s
    inbox.value = i
    sources.value = src
    sessions.value = ses
    forecast.value = fc.days
    queueCount.value = q.cards.length
    dictInstalled.value = dict.installed
    hookConnected.value = hooks.some((hook) => hook.connected)
  } catch (e) {
    app.fail(e)
  }
})

function dismissChecklist() {
  setupDismissed.value = true
  try {
    localStorage.setItem(DISMISSED_KEY, '1')
  } catch {
    /* the in-memory flag already hid it for this visit */
  }
}

const today = computed(() => {
  const d = new Date()
  const cn = ['日', '一', '二', '三', '四', '五', '六'][d.getDay()]
  return `${d.getMonth() + 1} 月 ${d.getDate()} 日 · 星期${cn}`
})

/** 首页只回答一个问题：现在该做什么。 */
const headline = computed(() => {
  const due = queueCount.value ?? 0
  const pending = inbox.value.length
  if (due && pending) return `先复习 ${due} 张，再整理 ${pending} 句。`
  if (due)
    return device.kind === 'mobile' ? `通勤路上把 ${due} 张过一遍。` : `把到期的 ${due} 张过一遍。`
  if (pending) return `没有到期的卡，整理 ${pending} 句就好。`
  return '没有到期的卡，也没有待整理的句子——去玩吧。'
})

const forecastTotal = computed(() => forecast.value.reduce((n, d) => n + d.count, 0))

async function startSession(source: Source) {
  try {
    app.activeSession = await api.post<Session>('/api/sessions', {
      source_id: source.id,
      mode: 'companion',
    })
    router.push(device.kind === 'desktop' ? '/capture' : '/inbox')
  } catch (e) {
    app.fail(e)
  }
}
</script>

<template>
  <div>
    <header class="flex flex-wrap items-end justify-between gap-4 border-b border-divider pb-3.5">
      <div>
        <p class="kicker text-accent">{{ today }}</p>
        <h1 class="page-title mt-1 text-[32px] md:text-[38px]">今天</h1>
      </div>
      <div class="text-[12px] leading-[1.8] text-ink-50 md:text-right">
        <p class="m-0">
          {{
            device.kind === 'desktop'
              ? '桌面端负责采集，手机负责浏览与复习。'
              : '采集请在电脑上进行。'
          }}
        </p>
        <p v-if="stats?.streak_days" class="num m-0">
          连续第 <b class="font-semibold text-ink">{{ stats.streak_days }}</b> 天
        </p>
      </div>
    </header>

    <SetupChecklist
      v-if="showChecklist"
      :progress="progress"
      class="mt-5"
      @dismiss="dismissChecklist"
    />

    <section class="flex flex-wrap items-center gap-5 border-b border-rule py-[18px]">
      <Transition name="fade" mode="out-in">
        <p :key="headline" class="m-0 font-head text-[21px] leading-snug md:text-[25px]">
          {{ headline }}
        </p>
      </Transition>
      <div class="flex flex-wrap gap-2.5 md:ml-auto">
        <RouterLink v-if="queueCount" to="/review" class="btn btn-primary">
          开始复习 {{ queueCount }} 张
        </RouterLink>
        <RouterLink v-if="inbox.length" to="/inbox" class="btn btn-secondary">
          整理 {{ inbox.length }} 句
        </RouterLink>
        <RouterLink v-if="!queueCount && !inbox.length" to="/library" class="btn btn-secondary">
          翻词库
        </RouterLink>
      </div>
    </section>

    <section v-if="forecast.length" class="mt-[26px]">
      <div class="flex items-baseline justify-between gap-3">
        <span class="kicker">记忆日历 · 未来{{ forecast.length <= 7 ? '一周' : '两周' }}到期</span>
        <span class="num text-[11px] text-ink-35">
          共 {{ forecastTotal }} 张 · 空白日＝可以放心去玩
        </span>
      </div>
      <MemoryCalendar
        :days="forecast"
        :height="device.kind === 'mobile' ? 52 : 82"
        class="mt-3.5"
      />
    </section>

    <div class="mt-[30px] md:grid md:grid-cols-[1fr_1px_1fr]">
      <section class="md:pr-7">
        <p class="kicker mb-3">作品进度</p>
        <TransitionGroup
          tag="ul"
          name="list"
          class="relative m-0 flex list-none flex-col gap-4 p-0"
        >
          <li v-for="s in sources" :key="s.id">
            <div class="flex items-baseline justify-between gap-3">
              <span class="font-head text-[17px] md:text-[19px]">
                {{ s.title }}
                <span v-if="s.title_ja" class="jp text-[12px] text-ink-35">{{ s.title_ja }}</span>
              </span>
              <span class="num shrink-0 text-[11px] text-ink-50">
                已掌握 {{ s.known_term_count }} / {{ s.term_count }} 词
              </span>
            </div>
            <div class="mt-[7px] h-[3px] bg-rule">
              <div
                class="h-[3px] bg-accent"
                :style="{
                  width: s.term_count
                    ? `${Math.round((s.known_term_count / s.term_count) * 100)}%`
                    : '0%',
                }"
              />
            </div>
            <p class="num mt-[5px] mb-0 text-[11px] text-ink-35">
              <template v-if="s.line_count">
                {{ s.line_count }} 句 · {{ s.region ? '已设对话区域' : '未设对话区域' }}
              </template>
              <template v-else>
                还没开始 ·
                <button
                  v-if="device.kind === 'desktop'"
                  class="btn-quiet text-accent"
                  @click="startSession(s)"
                >
                  开始第一次会话
                </button>
              </template>
            </p>
          </li>
        </TransitionGroup>
        <p v-if="!sources.length" class="mt-3 text-[13px] text-ink-50">
          还没有作品。<RouterLink to="/sources" class="text-accent">添加一部</RouterLink
          >，然后开始第一次会话。
        </p>
      </section>

      <div class="hidden bg-divider md:block" />

      <section class="mt-7 md:mt-0 md:pl-7">
        <p class="kicker mb-3">最近会话</p>
        <table v-if="sessions.length" class="table-plain">
          <TransitionGroup tag="tbody" name="list" class="relative">
            <tr v-for="s in sessions" :key="s.id">
              <td class="pl-0">{{ s.source_title ?? '—' }}</td>
              <td class="num text-ink-50">{{ s.line_count }} 句 · {{ relTime(s.started_at) }}</td>
              <td class="pr-0 text-right">
                <RouterLink :to="`/inbox?session=${s.id}`" class="text-accent">收件箱</RouterLink>
                ·
                <RouterLink :to="`/quiz/${s.id}`" class="text-accent">短测</RouterLink>
              </td>
            </tr>
          </TransitionGroup>
        </table>
        <p v-else class="m-0 text-[13px] text-ink-35">还没有会话。</p>
        <p class="mt-4 mb-0 text-[11px] leading-[1.7] text-ink-35">
          日历回答的不是"有多少"，而是"今天要花多久、哪天可以歇"。
        </p>
      </section>
    </div>
  </div>
</template>
