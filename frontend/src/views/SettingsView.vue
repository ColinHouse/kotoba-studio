<script setup lang="ts">
import AiSection from '@/components/settings/AiSection.vue'
import BackupSection from '@/components/settings/BackupSection.vue'
import DeviceSection from '@/components/settings/DeviceSection.vue'
import DictionarySection from '@/components/settings/DictionarySection.vue'
import ExportSection from '@/components/settings/ExportSection.vue'
import KnownImportSection from '@/components/settings/KnownImportSection.vue'
import OcrSection from '@/components/settings/OcrSection.vue'
import QrConnect from '@/components/settings/QrConnect.vue'
import ReviewSection from '@/components/settings/ReviewSection.vue'
import SettingsSection from '@/components/settings/SettingsSection.vue'
import { useAppStore } from '@/stores/app'

const app = useAppStore()
</script>

<template>
  <div class="mx-auto max-w-3xl space-y-6">
    <h1 class="text-2xl font-semibold">设置</h1>

    <SettingsSection title="连接手机">
      <QrConnect />
    </SettingsSection>

    <DeviceSection />
    <ReviewSection />
    <AiSection />
    <DictionarySection />
    <KnownImportSection />
    <OcrSection />
    <ExportSection />
    <BackupSection />

    <p class="text-center text-xs text-ink-3">
      Kotoba Studio v{{ app.health?.version }} · 服务器平台 {{ app.serverPlatform }}
    </p>
  </div>
</template>
