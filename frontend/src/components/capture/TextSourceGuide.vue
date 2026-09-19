<script setup lang="ts">
import { computed } from 'vue'
import { t, type MessagePath } from '@/i18n'

type TextSource = 'hook' | 'ocr'

const props = defineProps<{ preferred: TextSource }>()
const emit = defineEmits<{ select: [source: TextSource] }>()

/** Order and wording only: both routes stay reachable, and `prefer` never
 *  disables the other one — it just moves it to the top next time. */
const ENTRY: Record<
  TextSource,
  { title: MessagePath; reason: MessagePath; href: string; link: MessagePath }
> = {
  hook: {
    title: 'capture.source.hookTitle',
    reason: 'capture.source.hookReason',
    href: '#hook-status',
    link: 'capture.source.hookLink',
  },
  ocr: {
    title: 'capture.source.ocrTitle',
    reason: 'capture.source.ocrReason',
    href: '#ocr-collect',
    link: 'capture.source.ocrLink',
  },
}

const order = computed<TextSource[]>(() =>
  props.preferred === 'hook' ? ['hook', 'ocr'] : ['ocr', 'hook'],
)
</script>

<template>
  <section class="framed mt-5 p-4">
    <p class="kicker m-0">{{ t('capture.source.title') }}</p>
    <div class="mt-2 grid gap-2 sm:grid-cols-2">
      <article v-for="source in order" :key="source" class="framed p-3" :data-source="source">
        <div class="flex flex-wrap items-baseline gap-2">
          <h2 class="m-0 font-head type-body">{{ t(ENTRY[source].title) }}</h2>
          <span v-if="source === preferred" class="tag tag-fact">
            {{ t('capture.source.recommended') }}
          </span>
          <button v-else type="button" class="btn-quiet ml-auto" @click="emit('select', source)">
            {{ t('capture.source.prefer') }}
          </button>
        </div>
        <p class="mt-1.5 mb-0 type-meta leading-relaxed text-ink-70">
          {{ t(ENTRY[source].reason) }}
        </p>
        <a class="mt-1.5 inline-block type-meta underline" :href="ENTRY[source].href">
          {{ t(ENTRY[source].link) }}
        </a>
      </article>
    </div>
  </section>
</template>
