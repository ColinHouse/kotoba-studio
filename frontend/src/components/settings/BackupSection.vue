<script setup lang="ts">
import { onMounted, ref } from 'vue'
import SettingsSection from './SettingsSection.vue'
import { api } from '@/api/client'
import type { Backup } from '@/api/types'
import { useAppStore } from '@/stores/app'
import { fmtBytes, fmtDateTime } from '@/utils/format'

const app = useAppStore()
const backups = ref<Backup[]>([])
const busy = ref('')

async function refresh() {
  backups.value = await api.get<Backup[]>('/api/backups')
}
onMounted(() => refresh().catch(app.fail))

async function create() {
  busy.value = 'create'
  try {
    await api.post('/api/backups')
    await refresh()
    app.toast('备份完成', 'success')
  } catch (e) {
    app.fail(e)
  } finally {
    busy.value = ''
  }
}

async function restore(backup: Backup) {
  if (!window.confirm(`用「${backup.name}」覆盖当前数据？当前数据会先自动另存一份。`)) return
  busy.value = 'restore'
  try {
    await api.post('/api/backups/restore', { name: backup.name })
    await refresh()
    app.toast('已恢复', 'success')
  } catch (e) {
    app.fail(e)
  } finally {
    busy.value = ''
  }
}
</script>

<template>
  <SettingsSection title="备份" hint="备份保存在数据目录的 backups/ 下；恢复前会自动另存当前数据。">
    <button class="btn-primary" :disabled="busy === 'create'" @click="create">
      立即备份（数据库 + 截图/音频）
    </button>
    <ul class="divide-y divide-line text-sm">
      <li
        v-for="b in backups"
        :key="b.name"
        class="flex flex-wrap items-center justify-between gap-2 py-2"
      >
        <span class="font-mono text-xs">
          {{ b.name }}
          <span class="text-ink-3">{{ fmtBytes(b.size) }} · {{ fmtDateTime(b.created_at) }}</span>
        </span>
        <button class="btn-quiet" :disabled="busy === 'restore'" @click="restore(b)">恢复</button>
      </li>
      <li v-if="!backups.length" class="py-2 text-ink-3">还没有备份。</li>
    </ul>
  </SettingsSection>
</template>
