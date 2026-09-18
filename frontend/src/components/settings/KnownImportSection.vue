<script setup lang="ts">
import { ref } from 'vue'
import SettingsSection from './SettingsSection.vue'
import { api } from '@/api/client'
import { useAppStore } from '@/stores/app'

interface KnownImportResult {
  created: number
  updated: number
  skipped: number
  unparsed: number
  field: number | null
}

const app = useAppStore()
const format = ref('list')
const field = ref('')
const file = ref<File | null>(null)
const busy = ref(false)
const result = ref<string | null>(null)

function pick(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0] ?? null
  result.value = null
}

async function submit() {
  if (!file.value) return
  busy.value = true
  result.value = null
  try {
    const form = new FormData()
    form.append('file', file.value)
    form.append('format', format.value)
    if (format.value === 'anki' && field.value.trim() !== '') {
      form.append('field', field.value.trim())
    }
    const r = await api.post<KnownImportResult>('/api/terms/known/import', form)
    result.value =
      `新建 ${r.created} · 更新 ${r.updated} · 已有卡跳过 ${r.skipped} · 未解析 ${r.unparsed}` +
      (r.field !== null ? ` · 使用字段 #${r.field}` : '')
    app.toast('已知词导入完成', 'success')
  } catch (e) {
    app.fail(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <SettingsSection
    title="已知词导入"
    hint="学过的词先标成已知，覆盖率和预习才不会把时间花在它们身上；已经有卡的词不会被改动。"
  >
    <div class="flex flex-wrap items-end gap-4">
      <label class="block" for="known-format">
        <span class="field-label">来源</span>
        <select id="known-format" v-model="format" class="input w-56">
          <option value="list">文本列表（一行一词，可带读法）</option>
          <option value="anki">Anki .apkg</option>
          <option value="jpdb">jpdb JSON</option>
        </select>
      </label>
      <label v-if="format === 'anki'" class="block" for="known-field">
        <span class="field-label">字段序号（留空自动找日语字段）</span>
        <input id="known-field" v-model="field" type="number" min="0" class="input w-24" />
      </label>
      <label class="block" for="known-file">
        <span class="field-label">文件</span>
        <input
          id="known-file"
          type="file"
          class="text-[12px] text-ink-70"
          accept=".txt,.apkg,.json"
          @change="pick"
        />
      </label>
      <button class="btn btn-primary" :disabled="!file || busy" @click="submit">
        {{ busy ? '导入中…' : '导入' }}
      </button>
    </div>
    <p v-if="result" class="text-[13px] text-ink-70">{{ result }}</p>
    <p class="text-[12px] text-ink-70">
      文本列表支持 UTF-8 与 Shift_JIS，`#` 开头的行是注释，`词&lt;Tab&gt;读法` 可以带读法。
    </p>
  </SettingsSection>
</template>
