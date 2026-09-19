<script setup lang="ts">
import { computed, onBeforeUnmount, ref, type CSSProperties } from 'vue'
import type { OcrResult } from '@/api/types'
import { t } from '@/i18n'

/** 要叠加的截图；`crop` 是识别区域在整张图里的比例（0..1），缺省表示整张都是。 */
interface OcrImage {
  src: string
  crop?: { x: number; y: number; width: number; height: number }
}

const props = defineProps<{
  result: OcrResult
  image: OcrImage | null
}>()

const LOW_CONFIDENCE = 0.6
const COPY_FEEDBACK_MS = 1500

const copied = ref<number | null>(null)
let copiedTimer: number | undefined

const stageStyle = computed<CSSProperties | undefined>(() => {
  const crop = props.image?.crop
  return crop ? { aspectRatio: `${crop.width} / ${crop.height}` } : undefined
})

// Percentage math, not pixels: the block boxes are normalized to the image,
// so the same numbers work at every display size and HiDPI scale.
const imageStyle = computed<CSSProperties | undefined>(() => {
  const crop = props.image?.crop
  if (!crop) return undefined
  return {
    width: `${100 / crop.width}%`,
    left: `${(-crop.x / crop.width) * 100}%`,
    top: `${(-crop.y / crop.height) * 100}%`,
  }
})

function boxStyle(box: [number, number, number, number]): CSSProperties {
  const [x, y, width, height] = box
  return {
    left: `${x * 100}%`,
    top: `${y * 100}%`,
    width: `${width * 100}%`,
    height: `${height * 100}%`,
  }
}

function percent(confidence: number): string {
  return `${(confidence * 100).toFixed(1)}%`
}

async function copy(event: MouseEvent, text: string, index: number): Promise<void> {
  try {
    await navigator.clipboard.writeText(text)
    copied.value = index
  } catch {
    // No clipboard permission: select the label instead, so the text can
    // still be copied by hand.
    const label = (event.currentTarget as HTMLElement).querySelector('.ocr-label')
    if (label) window.getSelection()?.selectAllChildren(label)
  }
  window.clearTimeout(copiedTimer)
  copiedTimer = window.setTimeout(() => (copied.value = null), COPY_FEEDBACK_MS)
}

onBeforeUnmount(() => window.clearTimeout(copiedTimer))
</script>

<template>
  <section>
    <p class="kicker">
      {{ t('capture.ocr.result') }} · {{ result.provider }} ·
      <span class="num">{{ result.elapsed_ms }} ms</span>
    </p>

    <template v-if="result.blocks.length && image">
      <div
        class="ocr-stage rounded-chip mt-2"
        :class="{ 'ocr-stage-crop': !!image.crop }"
        :style="stageStyle"
      >
        <img class="ocr-image" :src="image.src" alt="" draggable="false" :style="imageStyle" />
        <button
          v-for="(block, index) in result.blocks"
          :key="index"
          type="button"
          class="ocr-box"
          :class="{ 'ocr-box-low': block.confidence < LOW_CONFIDENCE }"
          data-ocr-box
          :style="boxStyle(block.box)"
          @click="copy($event, block.text, index)"
        >
          <span class="ocr-label">
            <span class="jp">{{ block.text }}</span>
            <span class="num">{{ percent(block.confidence) }}</span>
            <span v-if="copied === index" class="ocr-copied">{{ t('capture.ocr.copied') }}</span>
          </span>
        </button>
      </div>
      <p class="mt-1.5 mb-0 type-micro text-ink-70">{{ t('capture.ocr.copyHint') }}</p>
    </template>

    <template v-else>
      <p class="jp mt-2 mb-0 text-[18px] leading-[1.95] md:text-[20px]">
        {{ result.normalized ?? result.text }}
      </p>
      <p class="mt-2 mb-0 type-meta text-ink-70">
        {{ result.blocks.length ? t('capture.ocr.noImage') : t('capture.ocr.noBlocks') }}
      </p>
    </template>
  </section>
</template>

<style scoped>
.ocr-stage {
  position: relative;
  overflow: hidden;
  border: 1px solid var(--divider);
  background: var(--surface);
}
.ocr-image {
  display: block;
  width: 100%;
  height: auto;
}
.ocr-stage-crop .ocr-image {
  position: absolute;
  max-width: none;
}
/* 墨线 + 纸色描边：截图什么底色都能看清；低置信度用线型区分，不用颜色。 */
.ocr-box {
  position: absolute;
  padding: 0;
  border: 2px solid var(--ink);
  box-shadow: 0 0 0 1px var(--paper);
  background: transparent;
  cursor: pointer;
}
.ocr-box:hover {
  border-color: var(--accent);
}
.ocr-box-low {
  border-style: dashed;
}
.ocr-label {
  position: absolute;
  top: -2px;
  left: -2px;
  display: inline-flex;
  gap: 0.4em;
  align-items: baseline;
  padding: 1px 6px;
  border: 1px solid var(--divider);
  background: var(--paper);
  color: var(--ink);
  font-size: 12px;
  line-height: 1.6;
  white-space: nowrap;
  user-select: text;
}
.ocr-copied {
  color: var(--gold-deep);
}
</style>
