<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '@/api/client'
import type { AiUsage, Backup, DictStatus, Owner, Provider, Settings } from '@/api/types'
import QrConnect from '@/components/QrConnect.vue'
import { useAppStore } from '@/stores/app'
import { useDeviceStore } from '@/stores/device'
import { fmtBytes, fmtDateTime } from '@/utils/format'

const app = useAppStore()
const device = useDeviceStore()
const settings = ref<Settings | null>(null)
const dict = ref<DictStatus | null>(null)
const providers = ref<Provider[]>([])
const backups = ref<Backup[]>([])
const usage = ref<AiUsage | null>(null)
const keyStatus = ref<{ provider: string; configured: boolean; source: string } | null>(null)
const presets = ref<Record<string, { base_url: string; model: string }>>({})
const aiKey = ref('')
const deviceName = ref('')
const deviceKind = ref<'desktop' | 'mobile'>('desktop')
const ankiDeck = ref('Kotoba Studio')
const busy = ref('')
let poll: number | undefined

async function loadAll() {
  ;[settings.value, dict.value, providers.value, backups.value, usage.value, keyStatus.value] = await Promise.all([
    api.get<Settings>('/api/settings'),
    api.get<DictStatus>('/api/dict/status'),
    api.get<Provider[]>('/api/capture/providers'),
    api.get<Backup[]>('/api/backups'),
    api.get<AiUsage>('/api/ai/usage'),
    api.get<{ provider: string; configured: boolean; source: string }>('/api/settings/ai-key'),
  ])
  presets.value = (await api.get<{ presets: Record<string, { base_url: string; model: string }> }>('/api/ai/presets')).presets
  deviceName.value = device.device?.name ?? ''
  deviceKind.value = device.kind
}
onMounted(() => loadAll().catch(app.fail))
onBeforeUnmount(() => window.clearInterval(poll))

async function save(patch: Partial<Settings>) {
  try {
    settings.value = await api.put<Settings>('/api/settings', patch)
    app.settings = settings.value
    app.toast('已保存', 'success')
  } catch (e) {
    app.fail(e)
  }
}

function applyPreset(name: string) {
  const p = presets.value[name]
  if (!p || !settings.value) return
  save({ ai_provider: name, ai_base_url: p.base_url, ai_model: p.model })
}

async function saveKey() {
  if (!aiKey.value.trim() || !settings.value) return
  busy.value = 'key'
  try {
    keyStatus.value = await api.put('/api/settings/ai-key', { provider: settings.value.ai_provider, key: aiKey.value })
    aiKey.value = ''
    app.toast('API Key 已存入系统凭据', 'success')
  } catch (e) {
    app.fail(e)
  } finally {
    busy.value = ''
  }
}

async function installDict() {
  try {
    await api.post('/api/dict/jmdict/install')
    poll = window.setInterval(async () => {
      dict.value = await api.get<DictStatus>('/api/dict/status')
      if (['done', 'error', 'idle'].includes(dict.value.install.state)) {
        window.clearInterval(poll)
        if (dict.value.install.state === 'error') app.toast(dict.value.install.message, 'error')
      }
    }, 1500)
  } catch (e) {
    app.fail(e)
  }
}

async function createBackup() {
  busy.value = 'backup'
  try {
    await api.post('/api/backups')
    backups.value = await api.get<Backup[]>('/api/backups')
    app.toast('备份完成', 'success')
  } catch (e) {
    app.fail(e)
  } finally {
    busy.value = ''
  }
}

async function restore(b: Backup) {
  if (!confirm(`用「${b.name}」覆盖当前数据？当前数据会先自动另存一份。`)) return
  busy.value = 'restore'
  try {
    await api.post('/api/backups/restore', { name: b.name })
    backups.value = await api.get<Backup[]>('/api/backups')
    app.toast('已恢复', 'success')
  } catch (e) {
    app.fail(e)
  } finally {
    busy.value = ''
  }
}

async function exportApkg() {
  busy.value = 'apkg'
  try {
    const res = await api.raw('/api/export/apkg', { deck: ankiDeck.value })
    if (!res.ok) throw new Error(await res.text())
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = res.headers.get('content-disposition')?.match(/filename="?([^"]+)"?/)?.[1] ?? 'kotoba.apkg'
    a.click()
    URL.revokeObjectURL(a.href)
  } catch (e) {
    app.fail(e, '导出失败')
  } finally {
    busy.value = ''
  }
}

async function exportAnki() {
  busy.value = 'anki'
  try {
    const r = await api.post<{ added: unknown[]; skipped: string[]; errors: unknown[] }>('/api/export/anki-connect', { deck: ankiDeck.value })
    app.toast(`Anki：新增 ${r.added.length}，跳过 ${r.skipped.length}，失败 ${r.errors.length}`, 'success')
  } catch (e) {
    app.fail(e)
  } finally {
    busy.value = ''
  }
}

async function saveDevice() {
  try {
    await device.rename(deviceName.value.trim() || '设备', deviceKind.value)
    app.toast('设备已更新', 'success')
  } catch (e) {
    app.fail(e)
  }
}
</script>

<template>
  <div v-if="settings" class="mx-auto max-w-3xl space-y-6">
    <h1 class="text-2xl font-semibold">设置</h1>

    <section class="card space-y-3 p-5">
      <h2 class="font-semibold">连接手机</h2>
      <QrConnect />
    </section>

    <section class="card space-y-3 p-5">
      <h2 class="font-semibold">本设备</h2>
      <div class="flex flex-wrap gap-2">
        <input v-model="deviceName" class="input w-48" placeholder="设备名" />
        <select v-model="deviceKind" class="input w-auto"><option value="desktop">电脑</option><option value="mobile">手机</option></select>
        <button class="btn-outline" @click="saveDevice">保存</button>
      </div>
      <p class="text-xs text-ink-3">ID {{ device.device?.id?.slice(0, 8) }} · 同一张卡只由一个归属端安排正式复习。</p>
    </section>

    <section class="card space-y-3 p-5">
      <h2 class="font-semibold">复习</h2>
      <label class="block text-sm">
        <span class="label">新卡默认归属</span>
        <select class="input w-auto" :value="settings.review_owner_default ?? 'auto'" @change="save({ review_owner_default: (($event.target as HTMLSelectElement).value === 'auto' ? null : ($event.target as HTMLSelectElement).value) as Owner | null })">
          <option value="auto">自动（注册了手机就归手机，否则归电脑）</option>
          <option value="desktop">电脑</option>
          <option value="mobile">手机</option>
          <option value="any">任意设备</option>
        </select>
      </label>
      <label class="block text-sm">
        <span class="label">目标记忆保持率 {{ Math.round(settings.desired_retention * 100) }}%</span>
        <input type="range" min="0.75" max="0.97" step="0.01" :value="settings.desired_retention" class="w-full" @change="save({ desired_retention: Number(($event.target as HTMLInputElement).value) })" />
        <span class="text-xs text-ink-3">FSRS 参数：越高复习越频繁。默认 90%。</span>
      </label>
    </section>

    <section class="card space-y-3 p-5">
      <h2 class="font-semibold">AI 解释（可选）</h2>
      <div class="flex flex-wrap gap-2">
        <button v-for="(p, name) in presets" :key="name" class="btn-ghost text-xs" :class="{ 'ring-2 ring-accent': settings.ai_provider === name }" @click="applyPreset(name as string)">{{ name }}</button>
      </div>
      <div class="grid gap-2 sm:grid-cols-2">
        <label class="text-sm"><span class="label">Base URL</span><input :value="settings.ai_base_url" class="input" @change="save({ ai_base_url: ($event.target as HTMLInputElement).value })" /></label>
        <label class="text-sm"><span class="label">模型</span><input :value="settings.ai_model" class="input" @change="save({ ai_model: ($event.target as HTMLInputElement).value })" /></label>
      </div>
      <div class="flex flex-wrap gap-2">
        <input v-model="aiKey" type="password" class="input flex-1" :placeholder="keyStatus?.configured ? `已配置（${keyStatus.source}），输入新 Key 可替换` : '粘贴 API Key（存入系统钥匙串）'" />
        <button class="btn-outline" :disabled="busy === 'key' || !aiKey" @click="saveKey">保存 Key</button>
      </div>
      <p v-if="usage" class="text-xs text-ink-3">已调用 {{ usage.calls }} 次（失败 {{ usage.failed }}）· 估算费用 ${{ usage.cost_estimate_usd.toFixed(4) }} · 只发送目标词、当前句和之前 ≤3 句，不发送后续剧情。</p>
    </section>

    <section class="card space-y-3 p-5">
      <h2 class="font-semibold">词典</h2>
      <p v-if="dict?.installed" class="text-sm">已安装：{{ dict.dictionaries.map((d) => `${d.title}（${d.entry_count.toLocaleString()} 条，${d.revision}）`).join('；') }}</p>
      <p v-else class="text-sm text-ink-2">尚未安装 JMdict。安装后可查词、识别表达、给出候选释义（约 25 MB 下载）。</p>
      <div class="flex items-center gap-2">
        <button class="btn-primary" :disabled="dict?.install.state === 'downloading' || dict?.install.state === 'importing'" @click="installDict">{{ dict?.installed ? '更新 JMdict' : '安装 JMdict' }}</button>
        <span v-if="dict && dict.install.state !== 'idle'" class="text-sm text-ink-2">{{ dict.install.message }}<span v-if="dict.install.total"> {{ Math.round((dict.install.done / dict.install.total) * 100) }}%</span></span>
      </div>
      <p class="text-xs text-ink-3">中文释义：JMdict 不含中文；可在收件箱手动填写"这里的意思"，或用 AI 解释。后续版本支持导入 Yomitan 格式的日中词典。</p>
    </section>

    <section class="card space-y-2 p-5">
      <h2 class="font-semibold">OCR 引擎</h2>
      <ul class="text-sm">
        <li v-for="p in providers" :key="p.name" class="flex items-center gap-2 py-1">
          <span class="h-2 w-2 rounded-full" :class="p.available ? 'bg-matcha' : 'bg-line'" />
          <span class="font-mono">{{ p.name }}</span><span class="text-ink-2">{{ p.note }}</span><span v-if="p.recommended" class="chip bg-matcha/15 text-[10px] text-matcha">推荐</span>
        </li>
      </ul>
      <label class="block text-sm"><span class="label">默认引擎</span>
        <select class="input w-auto" :value="settings.ocr_provider" @change="save({ ocr_provider: ($event.target as HTMLSelectElement).value })">
          <option value="auto">自动</option>
          <option v-for="p in providers" :key="p.name" :value="p.name">{{ p.name }}</option>
        </select>
      </label>
    </section>

    <section class="card space-y-3 p-5">
      <h2 class="font-semibold">导出到 Anki（可选）</h2>
      <div class="flex flex-wrap gap-2">
        <input v-model="ankiDeck" class="input w-48" placeholder="牌组名" />
        <button class="btn-outline" :disabled="busy === 'apkg'" @click="exportApkg">下载 .apkg</button>
        <button class="btn-outline" :disabled="busy === 'anki'" @click="exportAnki">通过 AnkiConnect 加卡</button>
      </div>
      <p class="text-xs text-ink-3">每个词一条笔记，包含读音、释义、原句、截图、AI 解释；重复导出会按词条去重。</p>
    </section>

    <section class="card space-y-3 p-5">
      <h2 class="font-semibold">备份</h2>
      <button class="btn-primary" :disabled="busy === 'backup'" @click="createBackup">立即备份（数据库 + 截图/音频）</button>
      <ul class="divide-y divide-line text-sm">
        <li v-for="b in backups" :key="b.name" class="flex items-center justify-between py-2">
          <span class="font-mono text-xs">{{ b.name }} <span class="text-ink-3">{{ fmtBytes(b.size) }} · {{ fmtDateTime(b.created_at) }}</span></span>
          <button class="btn-ghost text-xs" :disabled="busy === 'restore'" @click="restore(b)">恢复</button>
        </li>
      </ul>
      <p class="text-xs text-ink-3">备份保存在数据目录的 backups/ 下；恢复前会自动另存当前数据。</p>
    </section>

    <p class="text-center text-xs text-ink-3">Kotoba Studio v{{ app.health?.version }} · 服务器平台 {{ app.serverPlatform }}</p>
  </div>
</template>
