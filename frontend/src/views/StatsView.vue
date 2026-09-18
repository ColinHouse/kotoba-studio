<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '@/api/client'
import type { DailyReviewStat, StudyStats } from '@/api/types'
import { useAppStore } from '@/stores/app'
import {
  computeBarLayout,
  computePolylinePoints,
  computeRollingAccuracy,
  formatPercent,
} from '@/utils/stats'

const app = useAppStore()
const stats = ref<StudyStats | null>(null)
const loading = ref(true)
const hoveredDay = ref<DailyReviewStat | null>(null)

const CHART_WIDTH = 860
const CHART_HEIGHT = 160
const PADDING = { top: 16, right: 16, bottom: 24, left: 16 }

onMounted(async () => {
  try {
    stats.value = await api.get<StudyStats>('/api/stats')
  } catch (e) {
    app.fail(e)
  } finally {
    loading.value = false
  }
})

const summary = computed(() => stats.value?.summary)
const dailyReviews = computed(() => stats.value?.daily_reviews_90d ?? [])
const forecast = computed(() => stats.value?.forecast_30d ?? [])
const sources = computed(() => stats.value?.sources ?? [])

const forecastTotal = computed(() => forecast.value.reduce((acc, d) => acc + d.count, 0))

// 90-day daily review bars
const reviewBars = computed(() => {
  const counts = dailyReviews.value.map((d) => d.count)
  const rects = computeBarLayout(counts, CHART_WIDTH, CHART_HEIGHT, PADDING, 10)
  return rects.map((rect, idx) => ({
    ...rect,
    data: dailyReviews.value[idx],
  }))
})

// 7-day rolling accuracy trend line
const rollingAccuracy = computed(() => {
  if (!summary.value?.has_enough_history) return []
  return computeRollingAccuracy(dailyReviews.value, 7)
})

const accuracyPoints = computed(() => {
  if (!summary.value?.has_enough_history) return ''
  return computePolylinePoints(rollingAccuracy.value, CHART_WIDTH, CHART_HEIGHT, PADDING, 0, 1)
})

// Target retention dashed reference line y-position
const targetRetentionY = computed(() => {
  const target = summary.value?.target_retention ?? 0.9
  const innerHeight = CHART_HEIGHT - PADDING.top - PADDING.bottom
  return Number((PADDING.top + (1 - target) * innerHeight).toFixed(1))
})

// 30-day forecast bars
const forecastBars = computed(() => {
  const counts = forecast.value.map((d) => d.count)
  const rects = computeBarLayout(counts, CHART_WIDTH, CHART_HEIGHT, PADDING, 10)
  return rects.map((rect, idx) => ({
    ...rect,
    data: forecast.value[idx],
  }))
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <header class="flex flex-wrap items-end justify-between gap-4 border-b border-divider pb-3.5">
      <div>
        <p class="kicker text-accent">记忆轨迹</p>
        <h1 class="page-title mt-1 text-[32px] md:text-[38px]">学习统计</h1>
      </div>
      <div class="type-meta leading-[1.8] text-ink-70 md:text-right">
        <p class="m-0">所有复习记录与留存指标由 SQL 聚合计算，诚实反映长期记忆轨迹。</p>
        <p v-if="summary?.streak_days" class="num m-0">
          连续复习第 <b class="font-semibold text-ink">{{ summary.streak_days }}</b> 天
        </p>
      </div>
    </header>

    <!-- Loading State -->
    <div v-if="loading" class="py-12 text-center text-sm text-ink-70">正在聚合统计数据…</div>

    <div v-else class="space-y-6">
      <!-- 1. Key Metrics Cards -->
      <section class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <div class="rounded-chip border border-divider bg-paper p-3.5 shadow-sm">
          <div class="type-micro text-ink-70">真实保留率</div>
          <div class="num mt-1 text-xl font-bold text-ink">
            {{ formatPercent(summary?.real_retention) }}
          </div>
          <div class="mt-1 type-micro text-ink-70">
            目标 {{ formatPercent(summary?.target_retention) }}
          </div>
        </div>

        <div class="rounded-chip border border-divider bg-paper p-3.5 shadow-sm">
          <div class="type-micro text-ink-70">连续复习</div>
          <div class="num mt-1 text-xl font-bold text-accent">
            {{ summary?.streak_days ?? 0 }} <span class="text-xs font-normal text-ink-70">天</span>
          </div>
          <div class="mt-1 type-micro text-ink-70">累计活跃 {{ summary?.days_active ?? 0 }} 天</div>
        </div>

        <div class="rounded-chip border border-divider bg-paper p-3.5 shadow-sm">
          <div class="type-micro text-ink-70">总复习量</div>
          <div class="num mt-1 text-xl font-bold text-ink">
            {{ summary?.total_reviews ?? 0 }}
            <span class="text-xs font-normal text-ink-70">次</span>
          </div>
          <div class="mt-1 type-micro text-ink-70">仅计已调度复习</div>
        </div>

        <div class="rounded-chip border border-divider bg-paper p-3.5 shadow-sm">
          <div class="type-micro text-ink-70">已掌握卡片</div>
          <div class="num mt-1 text-xl font-bold text-ink">
            {{ summary?.mastered_cards ?? 0 }}
            <span class="text-xs font-normal text-ink-70">张</span>
          </div>
          <div class="mt-1 type-micro text-ink-70">全部 {{ summary?.total_cards ?? 0 }} 张</div>
        </div>

        <div
          class="col-span-2 rounded-chip border border-divider bg-paper p-3.5 shadow-sm sm:col-span-1"
        >
          <div class="type-micro text-ink-70">未来 30 天到期</div>
          <div class="num mt-1 text-xl font-bold text-ink">
            {{ forecastTotal }} <span class="text-xs font-normal text-ink-70">张</span>
          </div>
          <div class="mt-1 type-micro text-ink-70">包含今日与已到期</div>
        </div>
      </section>

      <!-- 2. Daily Reviews & Accuracy (Past 90 Days) -->
      <section class="rounded-chip border border-divider bg-paper p-4 md:p-5 shadow-sm">
        <div
          class="flex flex-col justify-between gap-2 border-b border-divider pb-3 sm:flex-row sm:items-center"
        >
          <div>
            <h2 class="text-sm font-bold text-ink">近 90 天复习量与正确率</h2>
            <p class="type-micro text-ink-70">柱状表示当日复习次数，曲线表示 7 日滚动正确率</p>
          </div>
          <!-- Legend -->
          <div class="flex items-center gap-3 type-micro text-ink-70">
            <span class="flex items-center gap-1">
              <span class="inline-block size-2.5 rounded-xs bg-ink-35 opacity-40" />
              复习量
            </span>
            <span v-if="summary?.has_enough_history" class="flex items-center gap-1">
              <span class="inline-block h-0.5 w-3 bg-ink" />
              正确率
            </span>
            <span class="flex items-center gap-1">
              <span class="inline-block h-0.5 w-3 border-b border-dashed border-ink-50" />
              目标 ({{ formatPercent(summary?.target_retention) }})
            </span>
          </div>
        </div>

        <!-- Insufficient History Notice -->
        <div
          v-if="!summary?.has_enough_history"
          class="mt-3 rounded-xs border border-rule-2 bg-surface px-3 py-2 text-xs text-ink-70"
        >
          数据还太少（当前累计活跃 {{ summary?.days_active ?? 0 }} 天）：持续复习满 14
          天后将在此展示正确率趋势线，不凭空外推。
        </div>

        <!-- SVG Chart -->
        <div class="mt-4 overflow-x-auto">
          <svg
            :viewBox="`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`"
            class="w-full min-w-[640px] text-ink"
            preserveAspectRatio="none"
          >
            <!-- Baseline -->
            <line
              :x1="PADDING.left"
              :y1="CHART_HEIGHT - PADDING.bottom"
              :x2="CHART_WIDTH - PADDING.right"
              :y2="CHART_HEIGHT - PADDING.bottom"
              stroke="var(--divider)"
              stroke-width="1"
            />

            <!-- Target retention dashed reference line -->
            <line
              :x1="PADDING.left"
              :y1="targetRetentionY"
              :x2="CHART_WIDTH - PADDING.right"
              :y2="targetRetentionY"
              stroke="var(--divider)"
              stroke-width="1"
              stroke-dasharray="4 4"
            />

            <!-- Daily bars -->
            <rect
              v-for="bar in reviewBars"
              :key="bar.data.date"
              :x="bar.x"
              :y="bar.y"
              :width="bar.width"
              :height="bar.height"
              fill="currentColor"
              class="opacity-30 transition-opacity hover:opacity-80"
              @mouseenter="hoveredDay = bar.data"
              @mouseleave="hoveredDay = null"
            />

            <!-- Trend Polyline -->
            <polyline
              v-if="accuracyPoints"
              :points="accuracyPoints"
              fill="none"
              stroke="var(--ink)"
              stroke-width="1.8"
              stroke-linejoin="round"
              stroke-linecap="round"
            />
          </svg>
        </div>

        <!-- Chart Footer / Hover Info -->
        <div class="mt-2 flex h-5 items-center justify-between type-micro text-ink-70">
          <div>
            <span v-if="hoveredDay" class="num">
              {{ hoveredDay.date }}: 复习 {{ hoveredDay.count }} 次
              <template v-if="hoveredDay.count > 0">
                · 正确 {{ hoveredDay.correct }} · 正确率 {{ formatPercent(hoveredDay.accuracy) }}
              </template>
            </span>
            <span v-else class="text-ink-70">悬停或触碰柱状查看单日详情</span>
          </div>
          <div class="num text-ink-70">
            {{ dailyReviews[0]?.date }} 至 {{ dailyReviews[dailyReviews.length - 1]?.date }}
          </div>
        </div>
      </section>

      <!-- 3. Forecast for Next 30 Days -->
      <section class="rounded-chip border border-divider bg-paper p-4 md:p-5 shadow-sm">
        <div class="border-b border-divider pb-3">
          <h2 class="text-sm font-bold text-ink">未来 30 天到期预测</h2>
          <p class="type-micro text-ink-70">
            根据 FSRS 记忆稳定性计算的到期分布；首日包含今天已到期与未复习卡片
          </p>
        </div>

        <div class="mt-4 overflow-x-auto">
          <svg
            :viewBox="`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`"
            class="w-full min-w-[640px] text-ink"
            preserveAspectRatio="none"
          >
            <!-- Baseline -->
            <line
              :x1="PADDING.left"
              :y1="CHART_HEIGHT - PADDING.bottom"
              :x2="CHART_WIDTH - PADDING.right"
              :y2="CHART_HEIGHT - PADDING.bottom"
              stroke="var(--divider)"
              stroke-width="1"
            />

            <!-- Forecast bars -->
            <rect
              v-for="(bar, i) in forecastBars"
              :key="bar.data.date"
              :x="bar.x"
              :y="bar.y"
              :width="bar.width"
              :height="bar.height"
              :fill="i === 0 ? 'var(--accent)' : 'currentColor'"
              :class="i === 0 ? 'opacity-90' : 'opacity-25 hover:opacity-60'"
            />
          </svg>
        </div>

        <div class="mt-2 flex justify-between type-micro text-ink-70">
          <span class="num text-accent font-medium"
            >今天 / 已到期 ({{ forecast[0]?.count ?? 0 }})</span
          >
          <span class="num">{{ forecast[forecast.length - 1]?.date }}</span>
        </div>
      </section>

      <!-- 4. Source Breakdown (Single Column on Mobile) -->
      <section class="rounded-chip border border-divider bg-paper p-4 md:p-5 shadow-sm">
        <div class="border-b border-divider pb-3">
          <h2 class="text-sm font-bold text-ink">按作品统计</h2>
          <p class="type-micro text-ink-70">各作品的生词沉淀与掌握程度</p>
        </div>

        <div v-if="sources.length === 0" class="py-8 text-center text-xs text-ink-70">
          暂无作品数据。导入作品并建卡后在此展示。
        </div>

        <!-- Desktop Table -->
        <div v-else class="mt-3 hidden md:block overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead>
              <tr class="border-b border-divider type-micro text-ink-70">
                <th class="py-2.5 font-normal">作品</th>
                <th class="py-2.5 font-normal text-right">建卡数</th>
                <th class="py-2.5 font-normal text-right">已掌握</th>
                <th class="py-2.5 font-normal text-right">掌握率</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-rule-2">
              <tr v-for="s in sources" :key="s.source_id" class="hover:bg-surface/50">
                <td class="py-3 font-medium text-ink">{{ s.title }}</td>
                <td class="num py-3 text-right text-ink-70">{{ s.cards_count }}</td>
                <td class="num py-3 text-right text-ink-70">{{ s.mastered_count }}</td>
                <td class="num py-3 text-right font-medium text-ink">
                  {{ s.cards_count > 0 ? formatPercent(s.mastered_count / s.cards_count) : '—' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Mobile Single-Column Cards -->
        <div v-if="sources.length > 0" class="mt-3 divide-y divide-rule-2 md:hidden">
          <div v-for="s in sources" :key="s.source_id" class="py-3">
            <div class="font-medium text-ink text-sm">{{ s.title }}</div>
            <div class="mt-1.5 flex items-center justify-between text-xs text-ink-70">
              <span
                >建卡 <span class="num font-semibold text-ink">{{ s.cards_count }}</span></span
              >
              <span
                >掌握 <span class="num font-semibold text-ink">{{ s.mastered_count }}</span></span
              >
              <span>
                掌握率
                <span class="num font-semibold text-ink">
                  {{ s.cards_count > 0 ? formatPercent(s.mastered_count / s.cards_count) : '—' }}
                </span>
              </span>
            </div>
            <!-- Progress Bar -->
            <div class="mt-2 h-1.5 w-full rounded-full bg-surface overflow-hidden">
              <div
                class="h-full bg-accent transition-all"
                :style="{
                  width: s.cards_count > 0 ? `${(s.mastered_count / s.cards_count) * 100}%` : '0%',
                }"
              />
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
