<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '@/api/client'
import type { KanjiGrid, KanjiTerm, KanjiTerms, Source, SourceKanji } from '@/api/types'
import { useAppStore } from '@/stores/app'
import { kanjiInk, kanjiStatusLabel } from '@/utils/kanji'

const app = useAppStore()
const grid = ref<KanjiGrid | null>(null)
const selected = ref<string | null>(null)
const terms = ref<KanjiTerm[]>([])
const sources = ref<Source[]>([])
const sourceId = ref('')
const sourceKanji = ref<SourceKanji[]>([])
const installMessage = ref('')
const installing = ref(false)

async function loadGrid() {
  grid.value = await api.get<KanjiGrid>('/api/kanji')
}

async function install() {
  installing.value = true
  installMessage.value = '正在下载 KANJIDIC2…'
  try {
    await api.post('/api/dict/kanjidic/install')
    for (let i = 0; i < 120; i += 1) {
      await new Promise((resolve) => setTimeout(resolve, 700))
      const status = await api.get<{ kanjidic: { state: string; message: string } }>(
        '/api/dict/status',
      )
      installMessage.value = status.kanjidic.message
      if (status.kanjidic.state === 'done') {
        await loadGrid()
        return
      }
      if (status.kanjidic.state === 'error') return
    }
    installMessage.value = '下载超时，请稍后在设置里重试。'
  } catch (e) {
    app.fail(e)
  } finally {
    installing.value = false
  }
}

async function pick(character: string) {
  selected.value = character
  try {
    terms.value = (await api.get<KanjiTerms>(`/api/kanji/${encodeURIComponent(character)}`)).terms
  } catch (e) {
    app.fail(e)
  }
}

async function loadSource() {
  if (!sourceId.value) {
    sourceKanji.value = []
    return
  }
  try {
    sourceKanji.value = (
      await api.get<{ kanji: SourceKanji[] }>(`/api/kanji/source/${sourceId.value}`)
    ).kanji
  } catch (e) {
    app.fail(e)
  }
}

onMounted(async () => {
  try {
    await loadGrid()
    sources.value = await api.get<Source[]>('/api/sources')
  } catch (e) {
    app.fail(e)
  }
})
</script>

<template>
  <div>
    <header class="mb-5">
      <h1 class="m-0 font-head text-[24px] text-ink">汉字</h1>
      <p class="mt-1 type-meta text-ink-50">
        常用汉字表按掌握度着色，墨色越深越熟；点一个字看它出现在哪些词里。
      </p>
    </header>

    <div v-if="grid && !grid.installed" class="border border-rule p-4">
      <p class="m-0 type-note text-ink">还没有导入 KANJIDIC2 汉字表（EDRDG，CC BY-SA 4.0）。</p>
      <button class="btn btn-primary mt-3" :disabled="installing" @click="install">
        导入汉字表
      </button>
      <p v-if="installMessage" class="mt-2 type-meta text-ink-50">{{ installMessage }}</p>
    </div>

    <template v-else-if="grid">
      <p class="num mb-3 type-meta text-ink-50">
        常用 <span class="text-ink">{{ grid.summary.total }}</span> 字 · 已掌握
        {{ grid.summary.mastered }} · 学习中 {{ grid.summary.learning }} · 见过
        {{ grid.summary.seen }} · 未见过 {{ grid.summary.unseen }}
      </p>

      <div class="grid grid-cols-[repeat(auto-fill,minmax(30px,1fr))] gap-0.5">
        <button
          v-for="entry in grid.kanji"
          :key="entry.character"
          type="button"
          class="jp aspect-square cursor-pointer border-0 bg-transparent text-[17px] hover:bg-paper"
          :class="[kanjiInk(entry.status), selected === entry.character ? 'bg-accent-100' : '']"
          :title="`${entry.character} · ${kanjiStatusLabel(entry.status)} · ${entry.terms} 个词`"
          @click="pick(entry.character)"
        >
          {{ entry.character }}
        </button>
      </div>

      <section v-if="selected" class="mt-6 border-t border-rule pt-4">
        <h2 class="m-0 font-head text-[18px] text-ink">
          <span class="jp">{{ selected }}</span>
          <span class="ml-2 type-meta text-ink-50">{{ terms.length }} 个词</span>
        </h2>
        <ul v-if="terms.length" class="mt-2 list-none p-0">
          <li
            v-for="term in terms"
            :key="term.term_id"
            class="border-b border-rule py-1.5 type-body"
          >
            <RouterLink :to="`/terms/${term.term_id}`" class="no-underline">
              <span class="jp text-ink">{{ term.headword }}</span>
              <span class="jp ml-2 type-meta text-ink-50">{{ term.reading }}</span>
            </RouterLink>
            <span v-if="term.has_card" class="ml-2 type-micro text-gold">有卡</span>
            <span v-else-if="term.known_status === 'known'" class="ml-2 type-micro text-ink-50"
              >已知</span
            >
          </li>
        </ul>
        <p v-else class="mt-2 type-note text-ink-35">还没有含这个字的词。</p>
      </section>

      <section class="mt-6 border-t border-rule pt-4">
        <h2 class="m-0 font-head type-body text-ink">作品里的超纲字</h2>
        <p class="mt-1 type-meta text-ink-50">超出常用汉字表的字，按在这部作品里的出现次数排。</p>
        <select
          v-model="sourceId"
          class="mt-2 border border-rule bg-transparent px-2 py-1 type-note text-ink"
          @change="loadSource"
        >
          <option value="">选择作品</option>
          <option v-for="source in sources" :key="source.id" :value="String(source.id)">
            {{ source.title }}
          </option>
        </select>
        <ul v-if="sourceKanji.length" class="mt-2 flex list-none flex-wrap gap-2 p-0">
          <li v-for="item in sourceKanji" :key="item.character">
            <button
              type="button"
              class="jp cursor-pointer border border-rule bg-transparent px-2 py-1 type-body text-ink"
              :title="`出现 ${item.occurrences} 次，${item.terms} 个词`"
              @click="pick(item.character)"
            >
              {{ item.character
              }}<span class="num ml-1 type-micro text-ink-50">{{ item.occurrences }}</span>
            </button>
          </li>
        </ul>
        <p v-else-if="sourceId" class="mt-2 type-note text-ink-35">
          这部作品没有超出常用汉字表的字，或者还没有遇到词。
        </p>
      </section>
    </template>
  </div>
</template>
