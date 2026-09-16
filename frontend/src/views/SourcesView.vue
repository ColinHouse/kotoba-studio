<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import type { Kind, Session, Source } from '@/api/types'
import { useAppStore } from '@/stores/app'
import { useDeviceStore } from '@/stores/device'
import { KIND_LABEL } from '@/utils/format'

const app = useAppStore()
const device = useDeviceStore()
const router = useRouter()
const sources = ref<Source[]>([])
const form = ref<{ title: string; title_ja: string; kind: Kind }>({
  title: '',
  title_ja: '',
  kind: 'game',
})
const busy = ref(false)

async function load() {
  sources.value = await api.get<Source[]>('/api/sources')
}
onMounted(() => load().catch(app.fail))

async function create() {
  if (!form.value.title.trim()) return
  busy.value = true
  try {
    await api.post('/api/sources', {
      title: form.value.title.trim(),
      title_ja: form.value.title_ja.trim() || null,
      kind: form.value.kind,
    })
    form.value = { title: '', title_ja: '', kind: 'game' }
    await load()
    app.toast('已添加作品', 'success')
  } catch (e) {
    app.fail(e)
  } finally {
    busy.value = false
  }
}

async function start(s: Source) {
  try {
    const session = await api.post<Session>('/api/sessions', { source_id: s.id, mode: 'companion' })
    app.activeSession = session
    router.push(device.kind === 'desktop' ? '/capture' : '/inbox')
  } catch (e) {
    app.fail(e)
  }
}

async function remove(s: Source) {
  if (!confirm(`删除「${s.title}」？句子会保留但不再关联作品。`)) return
  try {
    await api.del(`/api/sources/${s.id}`)
    await load()
  } catch (e) {
    app.fail(e)
  }
}
</script>

<template>
  <div class="mx-auto max-w-4xl space-y-6">
    <h1 class="text-2xl font-semibold">作品</h1>
    <form class="card grid gap-2 p-4 sm:grid-cols-[1fr_1fr_auto_auto]" @submit.prevent="create">
      <input v-model="form.title" class="input" placeholder="作品名（中文或任意）" required />
      <input v-model="form.title_ja" class="input jp" placeholder="日文原名（可选）" />
      <select v-model="form.kind" class="input">
        <option v-for="(label, k) in KIND_LABEL" :key="k" :value="k">{{ label }}</option>
      </select>
      <button class="btn-primary" :disabled="busy">添加</button>
    </form>

    <ul class="space-y-2">
      <li
        v-for="s in sources"
        :key="s.id"
        class="card flex flex-wrap items-center justify-between gap-3 p-4"
      >
        <div>
          <p class="font-semibold">
            {{ s.title }}
            <span v-if="s.title_ja" class="jp text-sm font-normal text-ink-2">{{
              s.title_ja
            }}</span>
          </p>
          <p class="text-xs text-ink-3">
            {{ KIND_LABEL[s.kind] }} · {{ s.line_count }} 句 · {{ s.term_count }} 词 ·
            {{ s.region ? `对话区域 ${s.region.width}×${s.region.height}` : '未设置对话区域' }}
          </p>
        </div>
        <div class="flex gap-2">
          <button v-if="device.kind === 'desktop'" class="btn-primary" @click="start(s)">
            开始会话
          </button>
          <RouterLink :to="`/library?source=${s.id}`" class="btn-outline">词库</RouterLink>
          <button class="btn-ghost text-red-600" @click="remove(s)">删除</button>
        </div>
      </li>
    </ul>
    <p v-if="!sources.length" class="text-sm text-ink-2">
      添加你正在玩的 Galgame 或在看的动画，词卡会按作品归档，并记录同一个词在不同作品里的出现。
    </p>
  </div>
</template>
