<script setup lang="ts">
import { ref } from 'vue'
import { wsUrl } from '@/api/client'

const emit = defineEmits<{ submit: [text: string] }>()
const text = ref('')

function submit() {
  const value = text.value.trim()
  if (!value) return
  emit('submit', value)
  text.value = ''
}
</script>

<template>
  <div class="card p-3">
    <label class="label" for="manual-paste">手动粘贴（来自 Textractor / 剪贴板）</label>
    <div class="mt-1 flex gap-2">
      <textarea
        id="manual-paste"
        v-model="text"
        class="input jp h-20"
        placeholder="把台词粘贴到这里，Enter 保存"
        @keydown.enter.exact.prevent="submit"
      />
      <button class="btn-outline self-end" :disabled="!text.trim()" @click="submit">保存</button>
    </div>
    <p class="mt-1 text-xs text-ink-3">
      Hook 工具可直接连接 WebSocket <code>{{ wsUrl('/ws/hook') }}</code
      >，发送纯文本或 {"text": "…"}。
    </p>
  </div>
</template>
