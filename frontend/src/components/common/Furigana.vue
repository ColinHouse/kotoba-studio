<script setup lang="ts">
import { computed } from 'vue'
import { furigana } from '@/utils/furigana'

const props = withDefaults(
  defineProps<{ word: string; reading?: string | null; show?: boolean }>(),
  { reading: '', show: true },
)

const segments = computed(() =>
  props.show ? furigana(props.word, props.reading ?? '') : [{ text: props.word }],
)
</script>

<template>
  <span class="jp"
    ><template v-for="(seg, i) in segments" :key="i"
      ><ruby v-if="seg.ruby"
        >{{ seg.text }}<rt>{{ seg.ruby }}</rt></ruby
      ><template v-else>{{ seg.text }}</template></template
    ></span
  >
</template>
