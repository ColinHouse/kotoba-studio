<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { api } from '@/api/client'
import type { DictStatus, KnownStatus, Term } from '@/api/types'
import Furigana from '@/components/common/Furigana.vue'
import Skeleton from '@/components/common/Skeleton.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { useDelayedLoading } from '@/composables/useDelayedLoading'
import { useAppStore } from '@/stores/app'
import { frequencyBand } from '@/utils/frequency'

const app = useAppStore()
const route = useRoute()
const q = ref('')
const status = ref<KnownStatus | ''>('')
const sort = ref<'recent' | 'frequency'>('recent')
const hasFrequencies = ref(false)
const terms = ref<Term[]>([])
const counts = ref<Record<string, number>>({})
const loading = ref(false)
const showSkeleton = useDelayedLoading(loading, 200)
let timer: number | undefined

const FILTERS: { value: KnownStatus | ''; label: string }[] = [
  { value: '', label: '全部' },
  { value: 'unknown', label: '未学' },
  { value: 'learning', label: '学习中' },
  { value: 'known', label: '已掌握' },
]

const SORTS: { value: 'recent' | 'frequency'; label: string }[] = [
  { value: 'recent', label: '最近' },
  { value: 'frequency', label: '按频率' },
]

async function load() {
  loading.value = true
  try {
    const params = new URLSearchParams({ limit: '200' })
    if (q.value.trim()) params.set('q', q.value.trim())
    if (status.value) params.set('status', status.value)
    if (sort.value === 'frequency') params.set('sort', 'frequency')
    const source = route.query.source
    if (typeof source === 'string') params.set('source_id', source)
    terms.value = await api.get<Term[]>(`/api/terms?${params}`)
    if (!q.value.trim() && !status.value) {
      counts.value = terms.value.reduce<Record<string, number>>((acc, t) => {
        acc[t.known_status] = (acc[t.known_status] ?? 0) + 1
        acc[''] = (acc[''] ?? 0) + 1
        return acc
      }, {})
    }
  } catch (e) {
    app.fail(e)
  } finally {
    loading.value = false
  }
}
onMounted(async () => {
  try {
    hasFrequencies.value = (await api.get<DictStatus>('/api/dict/status')).has_frequencies
  } catch {
    /* the sort control simply stays unavailable */
  }
  await load()
})
watch([q, status, sort], () => {
  window.clearTimeout(timer)
  timer = window.setTimeout(load, 200)
})

/** 列表沿用分词的墨色规则：未学最黑最重，已掌握退到浅墨。 */
function wordClass(t: Term) {
  switch (t.known_status) {
    case 'known':
      return 'font-light text-ink-50'
    case 'learning':
      return 'font-normal text-ink-70'
    case 'ignored':
      return 'font-light text-ink-35 line-through'
    default:
      return 'font-semibold text-ink'
  }
}
const seenAgain = (t: Term) => t.encounter_count >= 2 && t.known_status !== 'known'
const glossOf = (t: Term) =>
  t.senses
    .map((s) => s.gloss_zh || s.gloss_en)
    .filter(Boolean)
    .join('；') || '—'
</script>

<template>
  <div>
    <header class="flex flex-wrap items-end justify-between gap-5 border-b border-divider pb-3.5">
      <h1 class="page-title text-[27px] md:text-[32px]">词库</h1>
      <div class="flex flex-wrap items-center gap-3.5">
        <input
          id="library-search"
          v-model="q"
          class="jp w-[200px] border-0 border-b border-divider bg-transparent pb-[5px] text-[14px] text-ink outline-none placeholder:text-ink-35 focus-visible:border-accent md:w-[260px]"
          placeholder="搜索词或读音…"
        />
        <div class="seg">
          <button
            v-for="f in FILTERS"
            :key="f.value"
            type="button"
            class="seg-opt"
            :aria-pressed="status === f.value"
            @click="status = f.value"
          >
            {{ f.label }}<span v-if="counts[f.value]" class="num"> {{ counts[f.value] }}</span>
          </button>
        </div>
        <div v-if="hasFrequencies" class="seg">
          <button
            v-for="s in SORTS"
            :key="s.value"
            type="button"
            class="seg-opt"
            :aria-pressed="sort === s.value"
            @click="sort = s.value"
          >
            {{ s.label }}
          </button>
        </div>
        <span v-else class="text-[11px] text-ink-35" title="在设置页导入 Yomitan 频率词典后可用">
          频率排序需先导入频率词典
        </span>
      </div>
    </header>

    <p v-if="route.query.source" class="mt-3 mb-0 text-[11px] text-ink-35">
      仅显示该作品中遇见的词。<RouterLink to="/library" class="text-accent">清除筛选</RouterLink>
    </p>

    <!-- 骨架屏：延迟 200ms 显示，形状与词条列表一致，绝不使用 spinner -->
    <div v-if="showSkeleton" class="m-0 mt-2 flex list-none flex-col p-0">
      <div
        v-for="i in 6"
        :key="i"
        class="flex flex-wrap items-center gap-x-5 gap-y-1 border-b border-rule py-[15px] md:flex-nowrap"
      >
        <div class="w-[150px] shrink-0 md:w-[210px]">
          <Skeleton height="24px" width="70%" />
        </div>
        <div class="min-w-0 flex-1">
          <Skeleton height="16px" width="85%" />
        </div>
        <div class="w-[96px] shrink-0 md:text-right">
          <Skeleton height="14px" width="60px" />
        </div>
        <div class="flex w-[184px] shrink-0 items-center justify-end gap-1.5">
          <Skeleton height="20px" width="46px" rounded="3px" />
          <Skeleton height="20px" width="56px" rounded="3px" />
        </div>
      </div>
    </div>

    <Transition name="rise" mode="out-in">
      <div v-if="!loading && terms.length">
        <ul class="m-0 mt-2 flex list-none flex-col p-0">
          <li v-for="t in terms" :key="t.id" :class="t.trap ? 'bg-accent-100' : ''">
            <RouterLink
              :to="`/terms/${t.id}`"
              class="flex flex-wrap items-center gap-x-5 gap-y-1 border-b border-rule py-[15px] no-underline md:flex-nowrap"
              :class="t.trap ? 'px-3' : ''"
            >
              <span
                class="w-[150px] shrink-0 text-[22px] leading-[1.7] md:w-[210px] md:text-[26px]"
                :class="wordClass(t)"
              >
                <Furigana :word="t.headword" :reading="t.reading" />
              </span>
              <span
                class="min-w-0 flex-1 text-[14px] md:text-[15px]"
                :class="
                  t.trap
                    ? 'text-accent-800'
                    : t.known_status === 'known'
                      ? 'text-ink-50'
                      : 'text-ink'
                "
              >
                {{ glossOf(t) }}
                <span v-if="t.trap" class="text-[12px] text-gold"
                  >— 不是「{{ t.trap.zh_reading_meaning }}」</span
                >
              </span>
              <span class="num w-[96px] shrink-0 text-[11px] text-ink-35 md:text-right">
                {{ t.encounter_count }} 次 · {{ t.source_count }} 部
              </span>
              <span class="flex w-[184px] shrink-0 items-center justify-end gap-1.5">
                <span v-if="t.trap" class="tag tag-warn">同形</span>
                <span v-else-if="seenAgain(t)" class="tag tag-fact">再见词</span>
                <span
                  v-if="hasFrequencies"
                  class="tag tag-state"
                  :class="frequencyBand(t.frequency_rank).className"
                  >{{ frequencyBand(t.frequency_rank).label }}</span
                >
                <StatusBadge :status="t.known_status" />
              </span>
            </RouterLink>
          </li>
        </ul>
        <p class="mt-4 mb-0 text-[11px] leading-[1.7] text-ink-35">
          未学的词最黑最重，已掌握的退到浅墨——扫一眼就知道哪几行还欠着。
        </p>
      </div>
      <p v-else-if="!loading && !terms.length" class="mt-5 text-[13px] text-ink-50">
        还没有词条。在收件箱里确认句子中的词，就会出现在这里。
      </p>
    </Transition>
  </div>
</template>
