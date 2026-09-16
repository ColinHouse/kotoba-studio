<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Region } from '@/api/types'

const props = defineProps<{
  src: string
  width: number
  height: number
  scale: number
  display: number
  modelValue: Region | null
}>()
const emit = defineEmits<{ 'update:modelValue': [region: Region] }>()

const img = ref<HTMLImageElement | null>(null)
const drag = ref<{ x0: number; y0: number; x1: number; y1: number } | null>(null)

/** displayed px → logical points */
function toLogical(px: number, py: number) {
  const el = img.value!
  return {
    x: Math.round((px * (props.width / el.clientWidth)) / props.scale),
    y: Math.round((py * (props.height / el.clientHeight)) / props.scale),
  }
}

function pos(e: PointerEvent) {
  const rect = img.value!.getBoundingClientRect()
  return {
    x: Math.min(Math.max(e.clientX - rect.left, 0), rect.width),
    y: Math.min(Math.max(e.clientY - rect.top, 0), rect.height),
  }
}

function down(e: PointerEvent) {
  const p = pos(e)
  drag.value = { x0: p.x, y0: p.y, x1: p.x, y1: p.y }
  ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
}
function move(e: PointerEvent) {
  if (!drag.value) return
  const p = pos(e)
  drag.value.x1 = p.x
  drag.value.y1 = p.y
}
function up() {
  if (!drag.value) return
  const d = drag.value
  drag.value = null
  const a = toLogical(Math.min(d.x0, d.x1), Math.min(d.y0, d.y1))
  const b = toLogical(Math.max(d.x0, d.x1), Math.max(d.y0, d.y1))
  const w = b.x - a.x
  const h = b.y - a.y
  if (w < 8 || h < 8) return
  emit('update:modelValue', { left: a.x, top: a.y, width: w, height: h, display: props.display })
}

const box = computed(() => {
  const el = img.value
  if (drag.value) {
    const d = drag.value
    return {
      left: Math.min(d.x0, d.x1),
      top: Math.min(d.y0, d.y1),
      width: Math.abs(d.x1 - d.x0),
      height: Math.abs(d.y1 - d.y0),
    }
  }
  const r = props.modelValue
  if (!r || !el || !el.clientWidth) return null
  const fx = el.clientWidth / (props.width / props.scale)
  const fy = el.clientHeight / (props.height / props.scale)
  return { left: r.left * fx, top: r.top * fy, width: r.width * fx, height: r.height * fy }
})
</script>

<template>
  <div
    class="relative select-none overflow-hidden rounded-chip border border-divider bg-surface"
    style="touch-action: none"
  >
    <img
      ref="img"
      :src="src"
      class="block w-full"
      draggable="false"
      alt="屏幕预览"
      @pointerdown="down"
      @pointermove="move"
      @pointerup="up"
      @pointercancel="up"
    />

    <!-- 已框选：实线 + 四角，外侧压暗 -->
    <div
      v-if="box"
      class="pointer-events-none absolute border border-accent"
      style="box-shadow: 0 0 0 9999px rgba(32, 31, 29, 0.28)"
      :style="{
        left: `${box.left}px`,
        top: `${box.top}px`,
        width: `${box.width}px`,
        height: `${box.height}px`,
      }"
    >
      <i
        class="corner"
        style="left: -1px; top: -1px; border-left-width: 2px; border-top-width: 2px"
      />
      <i
        class="corner"
        style="right: -1px; top: -1px; border-right-width: 2px; border-top-width: 2px"
      />
      <i
        class="corner"
        style="left: -1px; bottom: -1px; border-left-width: 2px; border-bottom-width: 2px"
      />
      <i
        class="corner"
        style="right: -1px; bottom: -1px; border-right-width: 2px; border-bottom-width: 2px"
      />
    </div>

    <!-- 未框选：虚线提示，每部作品只做一次 -->
    <div
      v-else
      class="pointer-events-none absolute inset-0 grid place-items-center"
      style="background: rgba(32, 31, 29, 0.34)"
    >
      <div
        class="rounded-chip border-2 border-dashed border-accent px-10 py-[26px] text-center"
        style="background: color-mix(in srgb, var(--paper) 90%, transparent)"
      >
        <p class="m-0 font-head text-[26px] text-gold">拖出对话框区域</p>
        <p class="mt-1 mb-0 text-[12px] text-gold">每部作品只做一次，之后自动复用</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.corner {
  position: absolute;
  width: 9px;
  height: 9px;
  border: 0 solid var(--accent);
}
</style>
