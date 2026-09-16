<script setup lang="ts">
import { ref } from 'vue'
import SettingsSection from './SettingsSection.vue'
import { api } from '@/api/client'
import { useAppStore } from '@/stores/app'

const app = useAppStore()
const deck = ref('Kotoba Studio')
const busy = ref('')

async function downloadApkg() {
  busy.value = 'apkg'
  try {
    const res = await api.raw('/api/export/apkg', { deck: deck.value })
    if (!res.ok) throw new Error(await res.text())
    const blob = await res.blob()
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download =
      res.headers.get('content-disposition')?.match(/filename="?([^"]+)"?/)?.[1] ?? 'kotoba.apkg'
    link.click()
    URL.revokeObjectURL(link.href)
  } catch (e) {
    app.fail(e, '导出失败')
  } finally {
    busy.value = ''
  }
}

async function sendToAnki() {
  busy.value = 'anki'
  try {
    const r = await api.post<{ added: unknown[]; skipped: string[]; errors: unknown[] }>(
      '/api/export/anki-connect',
      { deck: deck.value },
    )
    app.toast(
      `Anki：新增 ${r.added.length}，跳过 ${r.skipped.length}，失败 ${r.errors.length}`,
      'success',
    )
  } catch (e) {
    app.fail(e)
  } finally {
    busy.value = ''
  }
}
</script>

<template>
  <SettingsSection
    title="导出到 Anki（可选）"
    hint="每个词一条笔记，含读音、释义、原句、截图与 AI 解释；重复导出按词条去重。"
  >
    <div class="flex flex-wrap gap-2">
      <input id="anki-deck" v-model="deck" class="input w-48" placeholder="牌组名" />
      <button class="btn-outline" :disabled="busy === 'apkg'" @click="downloadApkg">
        下载 .apkg
      </button>
      <button class="btn-outline" :disabled="busy === 'anki'" @click="sendToAnki">
        通过 AnkiConnect 加卡
      </button>
    </div>
  </SettingsSection>
</template>
