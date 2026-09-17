<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { api, mediaUrl } from '@/api/client'
import type { DictStatus, ReaderBlock } from '@/api/types'
import FrequencyOrder from '@/components/inbox/FrequencyOrder.vue'
import TermEditor, { type ConfirmPayload } from '@/components/inbox/TermEditor.vue'
import TokenChips from '@/components/inbox/TokenChips.vue'
import PageStage from '@/components/reader/PageStage.vue'
import PageText from '@/components/reader/PageText.vue'
import { useReader } from '@/composables/useReader'
import { useTermBuilder } from '@/composables/useTermBuilder'
import { arrowTurn, isTypingTarget } from '@/utils/reader'

const props = defineProps<{ sourceId: string }>()
const { title, pages, index, current, rtl, loading, load, turn } = useReader(Number(props.sourceId))
const builder = useTermBuilder()
const selected = ref<ReaderBlock | null>(null)
const hasFrequencies = ref(false)

const prevLabel = computed(() => (rtl.value ? '上一页 →' : '← 上一页'))
const nextLabel = computed(() => (rtl.value ? '← 下一页' : '下一页 →'))

onMounted(async () => {
  await load()
  api
    .get<DictStatus>('/api/dict/status')
    .then((status) => (hasFrequencies.value = status.has_frequencies))
    .catch(() => undefined)
  window.addEventListener('keydown', onKey)
})

onBeforeUnmount(() => window.removeEventListener('keydown', onKey))

watch(index, () => {
  closePanel()
  preload()
})

function onKey(event: KeyboardEvent) {
  if (isTypingTarget(event.target as HTMLElement | null)) return
  if (event.key === 'Escape') {
    closePanel()
    return
  }
  const direction = arrowTurn(rtl.value, event.key)
  if (!direction) return
  event.preventDefault()
  turn(direction)
}

function closePanel() {
  selected.value = null
  builder.reset()
}

function selectBlock(block: ReaderBlock) {
  selected.value = block
  builder.reset()
  builder.analyze({ id: block.line_id })
}

async function confirmTerm(payload: ConfirmPayload) {
  const block = selected.value
  if (!block) return
  const ok = await builder.confirm(
    { id: block.line_id, status: block.status, encounter_count: block.encounter_count },
    payload,
  )
  if (!ok) return
  block.status = 'kept'
  block.encounter_count += 1
  if (payload.card_types.length) block.card_count += 1
}

/** 只预取相邻两页：整卷不进内存，翻页又不至于等图。 */
function preload() {
  for (const page of [pages.value[index.value + 1], pages.value[index.value - 1]]) {
    const src = page?.image ? mediaUrl(page.image) : undefined
    if (!src) continue
    const img = new Image()
    img.src = src
  }
}
</script>

<template>
  <div>
    <header class="flex flex-wrap items-end justify-between gap-3 border-b border-divider pb-3">
      <div class="min-w-0">
        <RouterLink to="/sources" class="kicker text-ink-50 hover:text-ink">← 作品</RouterLink>
        <h1 class="page-title mt-0.5 truncate text-[24px] md:text-[30px]">
          {{ title || '阅读' }}
        </h1>
      </div>
      <div class="flex items-center gap-4">
        <label class="flex cursor-pointer flex-col gap-0.5">
          <span class="kicker">翻页方向</span>
          <span class="seg">
            <button type="button" class="seg-opt" :aria-pressed="rtl" @click="rtl = true">
              右→左
            </button>
            <button type="button" class="seg-opt" :aria-pressed="!rtl" @click="rtl = false">
              左→右
            </button>
          </span>
        </label>
        <p v-if="current" class="num m-0 text-[13px] text-ink-50">
          第 {{ current.page }} / {{ pages.length }} 页
        </p>
      </div>
    </header>

    <p v-if="loading" class="mt-6 m-0 text-[13px] text-ink-50">正在打开…</p>
    <p v-else-if="!pages.length" class="mt-6 m-0 text-[13px] text-ink-50">
      这部作品还没有按页导入的内容。用 mokuro 处理漫画后，把 .mokuro 或整卷 zip 导入到它下面。
    </p>

    <div v-else-if="current" class="mt-4 lg:grid lg:grid-cols-[minmax(0,1fr)_360px] lg:gap-6">
      <section class="min-w-0">
        <div
          class="h-[calc(100dvh-330px)] min-h-[300px] border border-divider bg-surface/40 lg:h-[calc(100vh-260px)]"
        >
          <PageStage
            v-if="current.image"
            :key="current.page"
            :page="current.page"
            :image="current.image"
            :blocks="current.blocks"
            :active-line-id="selected?.line_id ?? null"
            :rtl="rtl"
            @turn="turn"
            @select="selectBlock"
          />
          <PageText
            v-else
            :blocks="current.blocks"
            :active-line-id="selected?.line_id ?? null"
            @select="selectBlock"
          />
        </div>

        <div class="mt-3 flex items-center justify-between gap-3">
          <button class="btn btn-secondary" :disabled="index === 0" @click="turn('prev')">
            {{ prevLabel }}
          </button>
          <span class="hidden text-[11px] text-ink-35 md:inline">← → 翻页 · 双指缩放</span>
          <button
            class="btn btn-secondary"
            :disabled="index >= pages.length - 1"
            @click="turn('next')"
          >
            {{ nextLabel }}
          </button>
        </div>
      </section>

      <aside class="mt-4 lg:mt-0">
        <template v-if="selected">
          <div
            class="lifted p-4 max-lg:fixed max-lg:inset-x-3 max-lg:bottom-[calc(var(--tab-bar-h)+10px)] max-lg:z-30 max-lg:max-h-[62dvh] max-lg:overflow-y-auto lg:static lg:border-0 lg:bg-transparent lg:p-0 lg:shadow-none"
          >
            <header class="flex items-start justify-between gap-3 border-b border-divider pb-2.5">
              <p class="jp m-0 text-[18px] leading-snug">{{ selected.text }}</p>
              <button class="btn-quiet shrink-0" @click="closePanel">关闭</button>
            </header>

            <div v-if="builder.analysis.value" class="mt-3">
              <TokenChips
                :analysis="builder.analysis.value"
                :selected-start="builder.picked.value?.span_start ?? null"
                @pick="builder.picked.value = $event"
              />
              <div
                v-if="builder.analysis.value.contractions.length"
                class="mt-3 flex flex-wrap gap-1.5"
              >
                <span
                  v-for="c in builder.analysis.value.contractions"
                  :key="c.form"
                  class="tag tag-fact jp"
                  :title="c.note_zh"
                >
                  {{ c.form }} ← {{ c.full }}
                </span>
              </div>
              <FrequencyOrder
                v-if="hasFrequencies"
                :tokens="builder.analysis.value.tokens"
                class="mt-3"
                @pick="builder.picked.value = $event"
              />
            </div>
            <p v-else class="mt-4 m-0 text-[12px] text-ink-35">正在分词…</p>

            <TermEditor
              v-if="builder.picked.value"
              :picked="builder.picked.value"
              :busy="builder.busy.value"
              class="mt-4"
              @confirm="confirmTerm"
              @cancel="builder.picked.value = null"
            />

            <div v-if="builder.result.value" class="framed mt-4 px-4 py-3 text-[13px]">
              已记录
              <RouterLink
                :to="`/terms/${builder.result.value.term.id}`"
                class="jp font-semibold text-accent"
              >
                {{ builder.result.value.term.headword }}
              </RouterLink>
              ，第 <span class="num">{{ builder.result.value.term.encounter_count }}</span> 次遇见
            </div>
          </div>
        </template>
        <p v-else class="mt-1 text-[13px] text-ink-35 lg:mt-0">
          点画面上的文字框查词建卡；已建过卡的框墨色更深。
        </p>
      </aside>
    </div>
  </div>
</template>
