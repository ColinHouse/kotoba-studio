<script setup lang="ts">
import { ref } from 'vue'
import { wsUrl } from '@/api/client'

const emit = defineEmits<{ submit: [text: string] }>()
const open = ref(false)
const text = ref('')

function submit() {
  const value = text.value.trim()
  if (!value) return
  emit('submit', value)
  text.value = ''
}
</script>

<template>
  <div>
    <button class="btn-quiet" :aria-expanded="open" @click="open = !open">
      手动粘贴 / Textractor {{ open ? '⌃' : '⌄' }}
    </button>

    <div v-if="open" class="framed mt-2.5 p-3.5">
      <label class="field-label" for="manual-paste">把台词粘贴到这里，Enter 保存</label>
      <div class="flex gap-2">
        <textarea
          id="manual-paste"
          v-model="text"
          class="input jp"
          style="min-height: 64px"
          @keydown.enter.exact.prevent="submit"
        />
        <button class="btn btn-secondary self-end" :disabled="!text.trim()" @click="submit">
          保存
        </button>
      </div>
      <p class="mt-2 mb-0 text-[11px] leading-relaxed text-ink-70">
        Hook 工具可直接连接 WebSocket <code class="num">{{ wsUrl('/ws/hook') }}</code
        >，发送纯文本或 {"text": "…"}。
      </p>
    </div>
  </div>
</template>
