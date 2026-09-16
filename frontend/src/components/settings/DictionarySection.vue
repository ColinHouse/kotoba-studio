<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import SettingsSection from './SettingsSection.vue'
import { api } from '@/api/client'
import type { DictStatus } from '@/api/types'
import { useAppStore } from '@/stores/app'
import {
  dictionaryCountLabel,
  dictionaryKindLabel,
  dictionaryListShows,
} from '@/utils/dictionaries'

const app = useAppStore()
const dict = ref<DictStatus | null>(null)
let poll: number | undefined

async function refresh() {
  dict.value = await api.get<DictStatus>('/api/dict/status')
}
onMounted(() => refresh().catch(app.fail))
onBeforeUnmount(() => window.clearInterval(poll))

const busy = () => ['downloading', 'importing'].includes(dict.value?.install.state ?? '')

async function install() {
  try {
    await api.post('/api/dict/jmdict/install')
    poll = window.setInterval(async () => {
      await refresh()
      if (['done', 'error', 'idle'].includes(dict.value?.install.state ?? '')) {
        window.clearInterval(poll)
        if (dict.value?.install.state === 'error') app.toast(dict.value.install.message, 'error')
      }
    }, 1500)
  } catch (e) {
    app.fail(e)
  }
}

const pitchBusy = () => ['downloading', 'importing'].includes(dict.value?.pitch.state ?? '')

async function installPitch() {
  window.clearInterval(poll)
  try {
    await api.post('/api/dict/pitch/install')
    poll = window.setInterval(async () => {
      await refresh()
      if (['done', 'error', 'idle'].includes(dict.value?.pitch.state ?? '')) {
        window.clearInterval(poll)
        if (dict.value?.pitch.state === 'done') app.toast('音高数据已安装', 'success')
        if (dict.value?.pitch.state === 'error') app.toast(dict.value.pitch.message, 'error')
      }
    }, 1500)
  } catch (e) {
    app.fail(e)
  }
}
</script>

<template>
  <SettingsSection title="词典">
    <template v-if="dict && dictionaryListShows(dict.dictionaries)">
      <ul class="space-y-1 text-sm">
        <li v-for="d in dict.dictionaries" :key="d.id">
          <span>{{ d.title }}</span>
          <span class="tag tag-fact ml-1.5 align-middle">{{ dictionaryKindLabel(d.kind) }}</span>
          <span class="text-ink-50">
            （{{ dictionaryCountLabel(d) }}<template v-if="d.revision">，{{ d.revision }}</template
            >）
          </span>
          <span v-if="d.attribution" class="block text-xs text-ink-35">{{ d.attribution }}</span>
        </li>
      </ul>
    </template>
    <p v-else-if="dict" class="text-sm text-ink-50">
      尚未安装 JMdict，也还没有导入其他词典。安装后可查词、识别表达、给出候选释义（约 25 MB 下载）。
    </p>
    <div class="flex flex-wrap items-center gap-2">
      <button class="btn-primary" :disabled="busy()" @click="install">
        {{ dict?.installed ? '更新 JMdict' : '安装 JMdict' }}
      </button>
      <span v-if="dict && dict.install.state !== 'idle'" class="text-sm text-ink-2">
        {{ dict.install.message
        }}<span v-if="dict.install.total">
          {{ Math.round((dict.install.done / dict.install.total) * 100) }}%</span
        >
      </span>
    </div>
    <p class="text-xs text-ink-3">
      中文释义：JMdict 不含中文，可在收件箱手动填写"这里的意思"，或用 AI 解释。后续版本支持导入
      Yomitan 格式的日中词典。
    </p>
    <p class="text-xs text-ink-3">
      词典数据来自
      <a
        class="underline"
        href="https://www.edrdg.org/wiki/index.php/JMdict-EDICT_Dictionary_Project"
        target="_blank"
        rel="noreferrer"
        >JMdict/EDICT 项目</a
      >（电子辞書研究開発グループ，EDRDG），依
      <a
        class="underline"
        href="https://creativecommons.org/licenses/by-sa/4.0/"
        target="_blank"
        rel="noreferrer"
        >CC BY-SA 4.0</a
      >
      授权使用。
    </p>
    <div class="space-y-2 border-t border-divider pt-3">
      <p class="text-sm">
        音高重音：{{ dict?.has_pitch ? '已安装' : '未安装' }}
        <span class="text-ink-50">（用于卡面音高线与音高小测）</span>
      </p>
      <div class="flex flex-wrap items-center gap-2">
        <button class="btn btn-secondary" :disabled="pitchBusy()" @click="installPitch">
          {{ pitchBusy() ? '安装中…' : dict?.has_pitch ? '更新音高数据' : '安装音高数据' }}
        </button>
        <span v-if="dict && dict.pitch.state !== 'idle'" class="text-sm text-ink-50">{{
          dict.pitch.message
        }}</span>
      </div>
      <p class="text-xs text-ink-50">
        音高数据来自
        <a
          class="underline"
          href="https://github.com/mifunetoshiro/kanjium"
          target="_blank"
          rel="noreferrer"
          >Kanjium</a
        >（Uros O.），依
        <a
          class="underline"
          href="https://creativecommons.org/licenses/by-sa/4.0/"
          target="_blank"
          rel="noreferrer"
          >CC BY-SA 4.0</a
        >
        授权使用。
      </p>
    </div>
  </SettingsSection>
</template>
