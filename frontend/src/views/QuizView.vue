<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api, mediaUrl } from '@/api/client'
import type { QuizItem, Session, SessionSummary } from '@/api/types'
import Furigana from '@/components/common/Furigana.vue'
import Skeleton from '@/components/common/Skeleton.vue'
import { useDelayedLoading } from '@/composables/useDelayedLoading'
import { useAppStore } from '@/stores/app'
import { useDeviceStore } from '@/stores/device'
import { diffAnswer } from '@/utils/diff'
import { fmtDuration } from '@/utils/format'

const props = defineProps<{ sessionId: string }>()
const app = useAppStore()
const device = useDeviceStore()
const items = ref<QuizItem[]>([])
const index = ref(0)
const given = ref('')
const revealed = ref(false)
const result = ref<{ correct: boolean; expected: string } | null>(null)
const score = ref({ answered: 0, correct: 0 })
const summary = ref<SessionSummary | null>(null)
const session = ref<Session | null>(null)
const loading = ref(true)
const showSkeleton = useDelayedLoading(loading, 200)
const startedAt = ref(Date.now())
const input = ref<HTMLInputElement | null>(null)

const KIND_LABEL: Record<string, string> = {
  reading: '读音回忆',
  cloze: '语境填空',
  meaning: '语境释义',
  listening: '听音理解',
  pitch: '音高型',
}

const current = computed(() => items.value[index.value] ?? null)
const pieces = computed(() =>
  result.value && given.value ? diffAnswer(given.value, result.value.expected) : [],
)

async function loadSummary() {
  const [s, meta] = await Promise.all([
    api.get<SessionSummary>(`/api/sessions/${props.sessionId}/summary`),
    api.get<Session>(`/api/sessions/${props.sessionId}`).catch(() => null),
  ])
  summary.value = s
  session.value = meta
}

onMounted(async () => {
  try {
    const r = await api.post<{ items: QuizItem[] }>(
      `/api/quiz/sessions/${props.sessionId}?limit=12`,
    )
    items.value = r.items
    if (!r.items.length) await loadSummary()
  } catch (e) {
    app.fail(e)
  } finally {
    loading.value = false
  }
})

async function submit(selfCorrect?: boolean) {
  const item = current.value
  if (!item) return
  try {
    result.value = await api.post<{ correct: boolean; expected: string }>('/api/quiz/answers', {
      card_id: item.card_id,
      encounter_id: item.encounter_id,
      kind: item.kind,
      given: item.kind === 'meaning' ? null : given.value,
      correct: item.kind === 'meaning' ? selfCorrect : null,
      duration_ms: Date.now() - startedAt.value,
      device_id: device.device?.id ?? null,
      session_id: Number(props.sessionId),
    })
    score.value.answered += 1
    if (result.value.correct) score.value.correct += 1
  } catch (e) {
    app.fail(e)
  }
}

async function next() {
  index.value += 1
  given.value = ''
  revealed.value = false
  result.value = null
  startedAt.value = Date.now()
  if (!current.value) {
    await loadSummary()
  } else {
    setTimeout(() => input.value?.focus(), 0)
  }
}

function pick(choice: string) {
  given.value = choice
  submit()
}
</script>

<template>
  <div class="mx-auto max-w-[660px]">
    <header class="flex items-baseline justify-between gap-3 border-b border-divider pb-3">
      <h1 class="page-title text-[26px] md:text-[28px]">会后短测</h1>
      <span class="num type-meta text-ink-50">
        {{ Math.min(index + 1, items.length) }} / {{ items.length }} · 对 {{ score.correct }}
      </span>
    </header>

    <!-- 骨架屏：延迟 200ms 显示，模拟短测卡片结构，绝不使用 spinner -->
    <div v-if="showSkeleton" class="mt-5 space-y-4">
      <Skeleton height="14px" width="70px" />
      <Skeleton height="38px" width="85%" />
      <Skeleton height="16px" width="45%" />
      <div class="flex gap-2.5 pt-2">
        <Skeleton height="40px" width="100%" rounded="var(--radius-ui)" />
        <Skeleton height="40px" width="76px" rounded="var(--radius-ui)" />
      </div>
    </div>

    <Transition name="rise" mode="out-in">
      <div v-if="!loading && current">
        <p class="kicker mt-5 text-accent">{{ KIND_LABEL[current.kind] }}</p>

        <audio
          v-if="current.kind === 'listening' && current.audio_path"
          :src="mediaUrl(current.audio_path)"
          controls
          class="mt-3"
        />
        <p v-else class="jp mt-2.5 mb-0 text-[23px] leading-[2.1] md:text-[26px]">
          {{ current.prompt }}
        </p>
        <p class="mt-2 mb-0 type-note text-ink-50">{{ current.hint }}</p>

        <div v-if="!result" class="mt-5">
          <template v-if="current.kind === 'meaning'">
            <button v-if="!revealed" class="btn btn-primary" @click="revealed = true">
              显示答案
            </button>
            <template v-else>
              <p class="m-0 text-[18px]">{{ current.answer }}</p>
              <div class="mt-4 flex gap-2.5">
                <button class="btn btn-secondary" @click="submit(false)">没想起来</button>
                <button class="btn btn-primary" @click="submit(true)">想起来了</button>
              </div>
            </template>
          </template>
          <template v-else-if="current.kind === 'pitch'">
            <div class="flex flex-wrap gap-2.5">
              <button
                v-for="choice in current.choices"
                :key="choice"
                class="btn btn-secondary"
                @click="pick(choice)"
              >
                {{ choice }}
              </button>
            </div>
          </template>
          <form v-else class="flex gap-2.5" @submit.prevent="submit()">
            <input
              ref="input"
              v-model="given"
              class="input jp text-[18px]"
              placeholder="输入答案…"
            />
            <button class="btn btn-primary" :disabled="!given.trim()">提交</button>
          </form>
        </div>

        <div v-else class="mt-[22px] border-t border-rule pt-[18px]">
          <dl class="m-0 grid grid-cols-[64px_1fr] items-baseline gap-x-3.5 gap-y-2.5">
            <template v-if="current.kind !== 'meaning'">
              <dt class="text-right type-micro tracking-[0.1em] text-ink-35">你写的</dt>
              <dd class="jp m-0 text-[22px] md:text-[24px]">
                <template v-if="pieces.length">
                  <span
                    v-for="(p, i) in pieces.filter((x) => !x.missing)"
                    :key="i"
                    :class="p.ok ? '' : 'wrong'"
                    >{{ p.text }}</span
                  >
                </template>
                <template v-else>{{ given || '（空）' }}</template>
              </dd>
            </template>
            <dt class="text-right type-micro tracking-[0.1em] text-ink-35">
              {{ result.correct ? '正确' : '正确答案' }}
            </dt>
            <dd class="jp m-0 text-[22px] md:text-[24px]">
              <template v-if="pieces.length && !result.correct">
                <span
                  v-for="(p, i) in pieces.filter((x) => !x.extra)"
                  :key="i"
                  :class="p.ok ? '' : 'right'"
                  >{{ p.text }}</span
                >
              </template>
              <template v-else>{{ result.expected }}</template>
            </dd>
          </dl>

          <p class="jp mt-3.5 mb-0 type-body text-ink-70">
            <Furigana :word="current.headword" :reading="current.reading" /> ·
            {{ current.kind === 'meaning' ? current.answer : '' }}
          </p>

          <div class="mt-5 flex flex-wrap items-center gap-3.5">
            <button class="btn btn-primary" @click="next">下一题</button>
            <span class="type-micro text-ink-35">短测只作记录，不改变 FSRS 的正式安排。</span>
          </div>
        </div>
      </div>

      <!-- 版权页式的收束 -->
      <section v-else-if="!loading && summary" class="mt-6">
        <div class="border-b border-divider pb-[18px] text-center">
          <p class="kicker text-accent">本次会话复盘</p>
          <p class="m-0 mt-1.5 font-head text-[26px] md:text-[30px]">
            {{ session?.source_title ?? '本次会话' }}
          </p>
          <p class="num m-0 type-meta text-ink-50">时长 {{ fmtDuration(summary.duration_s) }}</p>
        </div>

        <div class="mt-[22px] grid grid-cols-4">
          <div
            v-for="(stat, i) in [
              { n: summary.lines_total, label: '收藏' },
              { n: summary.kept, label: '确认' },
              { n: summary.new_terms.length, label: '新词' },
              { n: summary.seen_again_terms.length, label: '再见词' },
            ]"
            :key="stat.label"
            class="text-center"
            :class="i < 3 ? 'border-r border-rule' : ''"
          >
            <p
              class="num m-0 font-head text-[34px] leading-none md:text-[40px]"
              :class="stat.n ? 'text-ink' : 'text-ink-35'"
            >
              {{ stat.n }}
            </p>
            <p class="m-0 mt-1.5 type-micro tracking-[0.1em] text-ink-50">{{ stat.label }}</p>
          </div>
        </div>

        <div class="my-5 h-px bg-divider" />
        <div class="num flex justify-between type-note text-ink-70">
          <span
            >建卡 <b class="font-semibold text-ink">{{ summary.cards_created }}</b> 张</span
          >
          <span
            >短测
            <b class="font-semibold text-ink"
              >{{ summary.quiz.correct }}/{{ summary.quiz.answered }}</b
            ></span
          >
        </div>

        <div v-if="summary.new_terms.length" class="mt-5 border-t border-rule pt-4">
          <p class="kicker">这次新认识的</p>
          <p class="jp mt-2 mb-0 text-[20px]">
            <template v-for="(t, i) in summary.new_terms" :key="t.id"
              ><Furigana :word="t.headword" :reading="t.reading" /><span
                v-if="i < summary.new_terms.length - 1"
                >、</span
              ></template
            >
          </p>
        </div>
        <div v-if="summary.seen_again_terms.length" class="mt-4">
          <p class="kicker">之前也遇到过</p>
          <p class="jp mt-2 mb-0 text-[18px] text-ink-70">
            {{ summary.seen_again_terms.map((t) => t.headword).join('、') }}
          </p>
        </div>

        <div class="mt-[22px] flex gap-2.5">
          <RouterLink to="/review" class="btn btn-primary">去正式复习</RouterLink>
          <RouterLink :to="`/inbox?session=${sessionId}`" class="btn btn-secondary">
            回到收件箱
          </RouterLink>
        </div>
      </section>
    </Transition>
  </div>
</template>

<style scoped>
/* 差异用线型和墨色标，不用红色 */
.wrong {
  color: var(--ink-50);
  text-decoration: line-through;
  text-decoration-style: dotted;
}
.right {
  font-weight: 600;
  color: var(--gold-deep);
  border-bottom: 2px solid var(--accent);
}
</style>
