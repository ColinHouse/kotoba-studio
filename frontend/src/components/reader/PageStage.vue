<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { mediaUrl } from '@/api/client'
import type { ReaderBlock } from '@/api/types'
import { boxInk, boxStyle, swipeTurn, type NaturalSize } from '@/utils/reader'

const props = defineProps<{
  page: number
  image: string
  blocks: ReaderBlock[]
  activeLineId: number | null
  rtl: boolean
}>()
const emit = defineEmits<{ turn: [direction: 'next' | 'prev']; select: [block: ReaderBlock] }>()

interface Point {
  x: number
  y: number
}

const stage = ref<HTMLElement | null>(null)
const natural = ref<NaturalSize>({ width: 0, height: 0 })
const fit = ref({ left: 0, top: 0, width: 0, height: 0 })
const scale = ref(1)
const offset = ref<Point>({ x: 0, y: 0 })
const pointers = new Map<number, Point>()
let observer: ResizeObserver | null = null
let start: Point | null = null
let pinch: { distance: number; mid: Point } | null = null
let base = { x: 0, y: 0, scale: 1 }
let moved = false

/** 图和热区共用一层几何：先按容器 contain，再整体缩放平移，框永远贴着画面。 */
const layerStyle = computed(() => ({
  left: `${fit.value.left}px`,
  top: `${fit.value.top}px`,
  width: `${fit.value.width}px`,
  height: `${fit.value.height}px`,
  transform: `translate(${offset.value.x}px, ${offset.value.y}px) scale(${scale.value})`,
}))

function measure() {
  const el = stage.value
  const size = natural.value
  if (!el || !size.width || !size.height) return
  const ratio = Math.min(el.clientWidth / size.width, el.clientHeight / size.height)
  const width = size.width * ratio
  const height = size.height * ratio
  fit.value = {
    left: (el.clientWidth - width) / 2,
    top: (el.clientHeight - height) / 2,
    width,
    height,
  }
}

function onLoad(event: Event) {
  const img = event.target as HTMLImageElement
  natural.value = { width: img.naturalWidth, height: img.naturalHeight }
}

watch(natural, measure)

onMounted(() => {
  if (typeof ResizeObserver === 'undefined') return
  observer = new ResizeObserver(measure)
  if (stage.value) observer.observe(stage.value)
})

onBeforeUnmount(() => observer?.disconnect())

function distance(a: Point, b: Point) {
  return Math.hypot(a.x - b.x, a.y - b.y)
}

function mid(a: Point, b: Point): Point {
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max)
}

/** Keep the zoomed page from being dragged into empty space. */
function clampOffset(next: Point, at: number): Point {
  const maxX = ((at - 1) * fit.value.width) / 2
  const maxY = ((at - 1) * fit.value.height) / 2
  return { x: clamp(next.x, -maxX, maxX), y: clamp(next.y, -maxY, maxY) }
}

function down(event: PointerEvent) {
  const el = event.currentTarget as HTMLElement
  el.setPointerCapture(event.pointerId)
  pointers.set(event.pointerId, { x: event.clientX, y: event.clientY })
  moved = false
  const points = [...pointers.values()]
  if (points.length === 1) {
    start = points[0]!
    base = { ...offset.value, scale: scale.value }
  } else if (points.length === 2) {
    pinch = { distance: distance(points[0]!, points[1]!), mid: mid(points[0]!, points[1]!) }
    base = { ...offset.value, scale: scale.value }
  }
}

function move(event: PointerEvent) {
  if (!pointers.has(event.pointerId)) return
  pointers.set(event.pointerId, { x: event.clientX, y: event.clientY })
  const points = [...pointers.values()]
  if (points.length >= 2 && pinch) {
    const [a, b] = points as [Point, Point]
    scale.value = clamp(base.scale * (distance(a, b) / pinch.distance), 1, 4)
    const center = mid(a, b)
    offset.value = clampOffset(
      { x: base.x + center.x - pinch.mid.x, y: base.y + center.y - pinch.mid.y },
      scale.value,
    )
    moved = true
    return
  }
  if (!start) return
  const dx = event.clientX - start.x
  const dy = event.clientY - start.y
  if (Math.hypot(dx, dy) > 8) moved = true
  if (scale.value > 1) offset.value = clampOffset({ x: base.x + dx, y: base.y + dy }, scale.value)
}

function up(event: PointerEvent) {
  if (!pointers.has(event.pointerId)) return
  pointers.delete(event.pointerId)
  if (pointers.size === 0) {
    // 放大时单指是拖动画面，不是翻页。
    if (start && !pinch && scale.value <= 1) {
      const turn = swipeTurn(props.rtl, event.clientX - start.x, event.clientY - start.y)
      if (turn) emit('turn', turn)
    }
    start = null
    pinch = null
  } else if (pointers.size === 1) {
    start = [...pointers.values()][0]!
    base = { ...offset.value, scale: scale.value }
    pinch = null
  }
}

function pick(block: ReaderBlock) {
  if (moved) return
  emit('select', block)
}
</script>

<template>
  <div
    ref="stage"
    class="relative h-full w-full touch-none overflow-hidden"
    @pointerdown="down"
    @pointermove="move"
    @pointerup="up"
    @pointercancel="up"
  >
    <img
      :src="mediaUrl(image)"
      class="absolute select-none object-contain"
      :style="layerStyle"
      :alt="`第 ${page} 页`"
      draggable="false"
      @load="onLoad"
    />
    <div class="absolute" :style="layerStyle">
      <button
        v-for="block in blocks"
        :key="block.line_id"
        type="button"
        :class="[boxInk(block), block.line_id === activeLineId && 'reader-box-active']"
        :style="boxStyle(block.box, natural)"
        :aria-label="block.text"
        :title="block.text"
        @click="pick(block)"
      />
    </div>
  </div>
</template>
