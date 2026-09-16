<script setup lang="ts">
import { ref, watch } from 'vue'
import SettingsSection from './SettingsSection.vue'
import { useAppStore } from '@/stores/app'
import { useDeviceStore } from '@/stores/device'

const app = useAppStore()
const device = useDeviceStore()
const name = ref('')
const kind = ref<'desktop' | 'mobile'>('desktop')

// Registration is async, so follow the store rather than reading it once on mount.
watch(
  () => device.device,
  (registered) => {
    name.value = registered?.name ?? ''
    kind.value = device.kind
  },
  { immediate: true },
)

async function save() {
  try {
    await device.rename(name.value.trim() || '设备', kind.value)
    app.toast('设备已更新', 'success')
  } catch (e) {
    app.fail(e)
  }
}
</script>

<template>
  <SettingsSection title="本设备" hint="同一张卡只由一个归属端安排正式复习。">
    <div class="flex flex-wrap gap-2">
      <input id="device-name" v-model="name" class="input w-48" placeholder="设备名" />
      <select id="device-kind" v-model="kind" class="input w-auto">
        <option value="desktop">电脑</option>
        <option value="mobile">手机</option>
      </select>
      <button class="btn btn-secondary" @click="save">保存</button>
    </div>
    <p class="text-xs text-ink-3">ID {{ device.device?.id?.slice(0, 8) }}</p>
  </SettingsSection>
</template>
