<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useDeviceStore } from '@/stores/device'

const app = useAppStore()
const device = useDeviceStore()
const route = useRoute()

const nav = computed(() => {
  const items = [
    { to: '/', label: '首页', icon: '⌂', mobile: true },
    { to: '/capture', label: '采集', icon: '⌖', mobile: false, desktopOnly: true },
    { to: '/inbox', label: '收件箱', icon: '✎', mobile: true },
    { to: '/review', label: '复习', icon: '◐', mobile: true },
    { to: '/library', label: '词库', icon: '本', mobile: true },
    { to: '/sources', label: '作品', icon: '▣', mobile: false },
    { to: '/settings', label: '设置', icon: '⚙', mobile: true },
  ]
  return items.filter((i) => !i.desktopOnly || device.kind === 'desktop')
})

function active(to: string) {
  if (to === '/') return route.path === '/'
  if (to === '/inbox') return route.path.startsWith('/inbox') || route.path.startsWith('/quiz')
  if (to === '/library') return route.path.startsWith('/library') || route.path.startsWith('/terms')
  return route.path.startsWith(to)
}
</script>

<template>
  <div class="min-h-dvh md:flex">
    <aside class="hidden md:flex md:w-56 md:flex-col md:border-r md:border-line md:bg-paper-2/60 md:px-4 md:py-6">
      <RouterLink to="/" class="mb-6 flex items-center gap-2 px-2">
        <span class="grid h-9 w-9 place-items-center rounded-xl bg-accent text-lg font-bold text-white jp">言</span>
        <span>
          <span class="block text-base font-semibold leading-tight">Kotoba Studio</span>
          <span class="block text-xs text-ink-3">会记住语境的伴读</span>
        </span>
      </RouterLink>
      <nav class="flex flex-col gap-1">
        <RouterLink
          v-for="item in nav"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition"
          :class="active(item.to) ? 'bg-accent/15 font-semibold text-accent-2' : 'text-ink-2 hover:bg-white/70'"
        >
          <span class="w-5 text-center">{{ item.icon }}</span>{{ item.label }}
        </RouterLink>
      </nav>
      <div class="mt-auto space-y-2 px-2 text-xs text-ink-3">
        <div v-if="app.activeSession" class="rounded-lg bg-white/70 p-2">
          <span class="label">进行中的会话</span>
          <div class="text-ink-2">{{ app.activeSession.source_title ?? '未指定作品' }} · {{ app.activeSession.line_count }} 句</div>
        </div>
        <div class="flex items-center gap-2">
          <span class="h-2 w-2 rounded-full" :class="app.offline ? 'bg-red-500' : 'bg-matcha'" />
          {{ app.offline ? '服务器离线' : `v${app.health?.version ?? '…'} · ${device.device?.name ?? device.kind}` }}
        </div>
      </div>
    </aside>

    <div class="flex min-h-dvh flex-1 flex-col">
      <header class="flex items-center justify-between border-b border-line bg-paper-2/70 px-4 py-3 md:hidden">
        <RouterLink to="/" class="flex items-center gap-2 font-semibold">
          <span class="grid h-7 w-7 place-items-center rounded-lg bg-accent text-sm text-white jp">言</span>Kotoba
        </RouterLink>
        <span class="text-xs text-ink-3">{{ app.offline ? '离线' : device.device?.name ?? '' }}</span>
      </header>

      <div v-if="app.offline" class="bg-red-50 px-4 py-2 text-sm text-red-700">
        无法连接 Kotoba Studio 服务器。请确认桌面端正在运行，手机需与电脑在同一局域网。
      </div>

      <main class="flex-1 px-4 pb-24 pt-4 md:px-8 md:pb-10 md:pt-8">
        <RouterView />
      </main>

      <nav class="fixed inset-x-0 bottom-0 z-20 flex border-t border-line bg-paper-2/95 backdrop-blur md:hidden" style="padding-bottom: env(safe-area-inset-bottom)">
        <RouterLink
          v-for="item in nav.filter((i) => i.mobile)"
          :key="item.to"
          :to="item.to"
          class="flex flex-1 flex-col items-center gap-0.5 py-2 text-[11px]"
          :class="active(item.to) ? 'text-accent-2 font-semibold' : 'text-ink-3'"
        >
          <span class="text-lg leading-none">{{ item.icon }}</span>{{ item.label }}
        </RouterLink>
      </nav>
    </div>

    <div class="pointer-events-none fixed inset-x-0 top-3 z-50 flex flex-col items-center gap-2 px-4">
      <div
        v-for="t in app.toasts"
        :key="t.id"
        class="pointer-events-auto rounded-xl px-4 py-2 text-sm shadow-lg"
        :class="t.kind === 'error' ? 'bg-red-600 text-white' : t.kind === 'success' ? 'bg-matcha text-white' : 'bg-ink text-paper'"
      >
        {{ t.text }}
      </div>
    </div>
  </div>
</template>
