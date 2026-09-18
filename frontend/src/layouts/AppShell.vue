<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useDeviceStore } from '@/stores/device'

const app = useAppStore()
const device = useDeviceStore()
const route = useRoute()

interface NavItem {
  to: string
  label: string
  mobile: boolean
  desktopOnly?: boolean
}

const NAV: NavItem[] = [
  { to: '/', label: '首页', mobile: true },
  { to: '/capture', label: '采集', mobile: false, desktopOnly: true },
  { to: '/inbox', label: '收件箱', mobile: true },
  { to: '/review', label: '复习', mobile: true },
  { to: '/stats', label: '统计', mobile: true },
  { to: '/library', label: '词库', mobile: true },
  { to: '/kanji', label: '汉字', mobile: false },
  { to: '/sources', label: '作品', mobile: false },
  { to: '/settings', label: '设置', mobile: true },
]

const nav = computed(() => NAV.filter((i) => !i.desktopOnly || device.kind === 'desktop'))
const mobileNav = computed(() => nav.value.filter((i) => i.mobile))

function active(to: string) {
  if (to === '/') return route.path === '/'
  if (to === '/inbox') return route.path.startsWith('/inbox') || route.path.startsWith('/quiz')
  if (to === '/library') return route.path.startsWith('/library') || route.path.startsWith('/terms')
  return route.path.startsWith(to)
}
</script>

<template>
  <div class="min-h-dvh md:flex">
    <!-- 桌面外壳：208px 文字导航，不用图标 -->
    <aside
      class="hidden shrink-0 flex-col border-r border-divider px-5 py-[26px] md:flex"
      style="width: var(--shell-nav)"
    >
      <RouterLink to="/" class="mb-[26px] flex items-center gap-2.5 no-underline">
        <span
          class="jp grid size-[34px] place-items-center rounded-chip border border-accent text-[17px] text-accent"
          >言</span
        >
        <span>
          <span class="block font-head text-[18px] leading-tight text-ink">ことばこ</span>
          <span class="block text-[11px] text-ink-70">会记住语境的伴读</span>
        </span>
      </RouterLink>

      <nav class="flex flex-col gap-0.5 text-[14px]">
        <RouterLink
          v-for="item in nav"
          :key="item.to"
          :to="item.to"
          class="py-1.5 no-underline"
          :class="active(item.to) ? 'text-accent' : 'text-ink-70 hover:text-ink'"
        >
          <span :class="active(item.to) ? 'border-b border-accent pb-[3px]' : ''">{{
            item.label
          }}</span>
        </RouterLink>
      </nav>

      <div class="mt-auto text-[11px] leading-[1.7] text-ink-70">
        <template v-if="app.activeSession">
          <div class="border-t border-rule pt-2.5">进行中的会话</div>
          <div class="text-ink-70">
            {{ app.activeSession.source_title ?? '未指定作品' }} ·
            <span class="num">{{ app.activeSession.line_count }}</span> 句
          </div>
        </template>
        <div class="num mt-2.5" :class="app.activeSession ? '' : 'border-t border-rule pt-2.5'">
          v{{ app.health?.version ?? '…' }} · {{ device.device?.name ?? device.kind }}
        </div>
      </div>
    </aside>

    <div class="flex min-h-dvh flex-1 flex-col">
      <p v-if="app.offline" class="m-0 bg-accent-100 px-5 py-2 text-[12px] text-gold">
        无法连接 ことばこ 服务器。请确认桌面端正在运行，手机需与电脑在同一局域网。
      </p>

      <main class="flex-1">
        <div class="mx-auto w-full page-shell">
          <RouterView v-slot="{ Component }">
            <component :is="Component" :key="route.path" class="page-enter" />
          </RouterView>
        </div>
      </main>

      <!-- 手机底部 Tab：文字，无图标；底部留安全区 -->
      <nav
        class="fixed inset-x-0 bottom-0 z-20 flex border-t border-divider bg-bg font-head text-[13px] md:hidden"
        style="padding-bottom: max(26px, env(safe-area-inset-bottom))"
      >
        <RouterLink
          v-for="item in mobileNav"
          :key="item.to"
          :to="item.to"
          class="relative flex-1 py-2.5 text-center no-underline"
          :class="active(item.to) ? 'text-accent' : 'text-ink-70'"
        >
          <span
            v-if="active(item.to)"
            class="absolute left-1/2 top-0 h-0.5 w-[26px] -translate-x-1/2 bg-accent"
          />
          {{ item.label }}
        </RouterLink>
      </nav>
    </div>

    <!-- 提示：压在内容上方，不占布局 -->
    <div
      class="pointer-events-none fixed inset-x-0 top-3 z-50 flex flex-col items-center gap-2 px-4"
    >
      <TransitionGroup name="rise">
        <p
          v-for="t in app.toasts"
          :key="t.id"
          class="pointer-events-auto m-0 rounded-ui border px-4 py-2 text-[13px] shadow-[var(--shadow)]"
          :class="
            t.kind === 'error'
              ? 'border-accent bg-accent-100 text-gold'
              : 'border-divider bg-paper text-ink'
          "
        >
          {{ t.text }}
        </p>
      </TransitionGroup>
    </div>
  </div>
</template>

<style scoped>
/* 每个页面用同一组尺寸：桌面 1050px 内容宽，手机 20px 边距 + Tab 高度。 */
.page-shell {
  max-width: var(--content-max);
  padding: 18px var(--mobile-pad) calc(var(--tab-bar-h) + 26px);
}
@media (min-width: 768px) {
  .page-shell {
    padding: var(--page-pad-top) var(--page-pad-x) var(--page-pad-bottom);
  }
}
</style>
