<script setup lang="ts">
import { locale, setLocale, t } from '@/i18n'
import SettingsSection from './SettingsSection.vue'
</script>

<template>
  <!-- Label stays bilingual in both locales on purpose: an English reader has to
       find this switch while looking at a Chinese interface (#130). -->
  <SettingsSection :title="t('settings.language.title')">
    <div class="seg">
      <button
        type="button"
        class="seg-opt"
        :aria-pressed="locale === 'zh-CN'"
        @click="setLocale('zh-CN')"
      >
        简体中文
      </button>
      <button
        type="button"
        class="seg-opt"
        :aria-pressed="locale === 'en'"
        @click="setLocale('en')"
      >
        English
      </button>
    </div>
  </SettingsSection>
</template>
