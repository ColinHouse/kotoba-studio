<script setup lang="ts">
import type { Trap } from '@/api/types'
import Furigana from '@/components/common/Furigana.vue'

defineProps<{ trap: Trap; framed?: boolean }>()
</script>

<template>
  <div class="trap" :class="framed ? 'trap-framed' : 'trap-band'">
    <p class="kicker mb-2.5 text-gold">中日同形 · 别照汉字读</p>
    <Furigana
      :word="trap.headword"
      :reading="trap.reading"
      class="block text-[24px] leading-[1.4] text-accent-800 md:text-[26px]"
    />
    <dl class="mt-3 grid grid-cols-[auto_1fr] gap-x-3.5 gap-y-1 type-body leading-relaxed">
      <dt class="pt-1 type-micro tracking-[0.1em] text-gold">中文</dt>
      <dd class="m-0 border-b border-gold/25 pb-[5px] text-accent-800">
        「{{ trap.headword }}」＝ {{ trap.zh_reading_meaning }}
      </dd>
      <dt class="pt-1 type-micro tracking-[0.1em] text-gold">日语</dt>
      <dd class="m-0 text-accent-800">
        「{{ trap.headword }}」＝ <b class="font-bold">{{ trap.ja_meaning }}</b>
      </dd>
    </dl>
    <p v-if="trap.note" class="mt-2 mb-0 type-meta text-gold">{{ trap.note }}</p>
  </div>
</template>

<style scoped>
.trap {
  background: var(--accent-100);
}
.trap-band {
  border-top: 1px solid var(--divider);
  border-bottom: 1px solid var(--divider);
  padding: 16px 24px;
}
.trap-framed {
  border: 1px solid color-mix(in srgb, var(--accent) 40%, transparent);
  border-radius: var(--radius-chip);
  padding: 16px 18px;
}
</style>
