<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { clipboardStatus, startClipboard, stopClipboard } from '@/api/capture'
import type { ClipboardStatus } from '@/api/types'
import { t } from '@/i18n'
import { useAppStore } from '@/stores/app'

/** Zero-install transport: any tool that copies the line to the clipboard
 *  (Textractor included) works without installing a WebSocket extension. */
const app = useAppStore()
const status = ref<ClipboardStatus | null>(null)
const busy = ref(false)

async function refresh() {
  try {
    status.value = await clipboardStatus()
  } catch {
    /* the page has its own offline handling; a retry is not worth a toast */
  }
}

async function toggle() {
  busy.value = true
  try {
    status.value = status.value?.running ? await stopClipboard() : await startClipboard()
  } catch (e) {
    app.fail(e)
  } finally {
    busy.value = false
  }
}

onMounted(refresh)
</script>

<template>
  <section class="framed mt-2 px-3.5 py-2.5">
    <div class="flex flex-wrap items-center gap-x-3 gap-y-2">
      <span class="kicker">{{ t('capture.clipboard.title') }}</span>
      <span class="type-meta text-ink-70">
        {{ status?.running ? t('capture.clipboard.on') : t('capture.clipboard.off') }}
      </span>
      <span v-if="status?.running" class="type-meta text-ink-70">
        {{ t('capture.clipboard.captured') }} <span class="num">{{ status.captured }}</span>
      </span>
      <button class="btn-quiet ml-auto" :disabled="busy" @click="toggle">
        {{ status?.running ? t('capture.clipboard.stop') : t('capture.clipboard.start') }}
      </button>
    </div>
    <p class="mt-2 mb-0 type-micro leading-relaxed text-ink-70">
      {{ t('capture.clipboard.hint') }}
    </p>
  </section>
</template>
