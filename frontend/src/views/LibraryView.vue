<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { api } from '@/api/client'
import type { KnownStatus, Term } from '@/api/types'
import Furigana from '@/components/common/Furigana.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { useAppStore } from '@/stores/app'

const app = useAppStore()
const route = useRoute()
const q = ref('')
const status = ref<KnownStatus | ''>('')
const terms = ref<Term[]>([])
const counts = ref<Record<string, number>>({})
const loading = ref(false)
let timer: number | undefined

const FILTERS: { value: KnownStatus | ''; label: string }[] = [
  { value: '', label: '全部' },
  { value: 'unknown', label: '未学' },
  { value: 'learning', label: '学习中' },
  { value: 'known', label: '已掌握' },
]

async function load() {
  loading.value = true
  try {
    const params = new URLSearchParams({ limit: '200' })
    if (q.value.trim()) params.set('q', q.value.trim())
    if (status.value) params.set('status', status.value)
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
onMounted(load)
watch([q, status], () => {
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
      </div>
    </header>

    <p v-if="route.query.source" class="mt-3 mb-0 text-[11px] text-ink-35">
      仅显示该作品中遇见的词。<RouterLink to="/library" class="text-accent">清除筛选</RouterLink>
    </p>

    <ul v-if="terms.length" class="m-0 mt-2 flex list-none flex-col p-0">
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
              t.trap ? 'text-accent-800' : t.known_status === 'known' ? 'text-ink-50' : 'text-ink'
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
          <span class="flex w-[120px] shrink-0 justify-end gap-1.5">
            <span v-if="t.trap" class="tag tag-warn">同形</span>
            <span v-else-if="seenAgain(t)" class="tag tag-fact">再见词</span>
            <StatusBadge :status="t.known_status" />
          </span>
        </RouterLink>
      </li>
    </ul>
    <p v-else-if="!loading" class="mt-5 text-[13px] text-ink-50">
      还没有词条。在收件箱里确认句子中的词，就会出现在这里。
    </p>

    <p v-if="terms.length" class="mt-4 mb-0 text-[11px] leading-[1.7] text-ink-35">
      未学的词最黑最重，已掌握的退到浅墨——扫一眼就知道哪几行还欠着。
    </p>
  </div>
</template>
