<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { api } from '@/api/client'
import type { KnownStatus, Term } from '@/api/types'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { useAppStore } from '@/stores/app'
import { STATUS_LABEL } from '@/utils/format'

const app = useAppStore()
const route = useRoute()
const q = ref('')
const status = ref<KnownStatus | ''>('')
const terms = ref<Term[]>([])
const loading = ref(false)
let timer: number | undefined

async function load() {
  loading.value = true
  try {
    const params = new URLSearchParams({ limit: '200' })
    if (q.value.trim()) params.set('q', q.value.trim())
    if (status.value) params.set('status', status.value)
    const source = route.query.source
    if (typeof source === 'string') params.set('source_id', source)
    terms.value = await api.get<Term[]>(`/api/terms?${params}`)
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
</script>

<template>
  <div class="mx-auto max-w-4xl space-y-4">
    <h1 class="text-2xl font-semibold">词库</h1>
    <div class="flex flex-wrap gap-2">
      <input v-model="q" class="input flex-1 jp" placeholder="搜索词或读音…" />
      <div class="flex gap-1">
        <button
          class="btn-ghost text-xs"
          :class="{ 'ring-2 ring-accent': status === '' }"
          @click="status = ''"
        >
          全部
        </button>
        <button
          v-for="(label, k) in STATUS_LABEL"
          :key="k"
          class="btn-ghost text-xs"
          :class="{ 'ring-2 ring-accent': status === k }"
          @click="status = k as KnownStatus"
        >
          {{ label }}
        </button>
      </div>
    </div>
    <p v-if="route.query.source" class="text-xs text-ink-3">
      仅显示该作品中遇见的词。<RouterLink to="/library" class="text-accent-2">清除筛选</RouterLink>
    </p>

    <ul v-if="terms.length" class="card divide-y divide-line">
      <li v-for="t in terms" :key="t.id">
        <RouterLink
          :to="`/terms/${t.id}`"
          class="flex items-center justify-between gap-3 px-4 py-3 hover:bg-paper-2/60"
        >
          <div class="min-w-0">
            <p class="jp text-lg font-semibold">
              {{ t.headword }} <span class="text-sm font-normal text-ink-2">{{ t.reading }}</span>
            </p>
            <p class="truncate text-sm text-ink-2">
              {{
                t.senses
                  .map((s) => s.gloss_zh || s.gloss_en)
                  .filter(Boolean)
                  .join('；') || '—'
              }}
            </p>
          </div>
          <div class="flex shrink-0 items-center gap-2 text-xs text-ink-3">
            <span v-if="t.trap" class="chip bg-accent/15 text-accent-2">同形</span>
            <span
              v-if="t.encounter_count >= 2 && t.known_status !== 'known'"
              class="chip bg-plum/15 text-plum"
              >再见词</span
            >
            <span>{{ t.encounter_count }} 次 · {{ t.source_count }} 部</span>
            <StatusBadge :status="t.known_status" />
          </div>
        </RouterLink>
      </li>
    </ul>
    <p v-else-if="!loading" class="text-sm text-ink-2">
      还没有词条。在收件箱里确认句子中的词，就会出现在这里。
    </p>
  </div>
</template>
