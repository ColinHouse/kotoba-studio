<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { t, type MessagePath } from '@/i18n'
import { useAppStore } from '@/stores/app'
import { useDeviceStore } from '@/stores/device'

const app = useAppStore()
const device = useDeviceStore()
const route = useRoute()

interface NavItem {
  to: string
  key: MessagePath
  mobile: boolean
  desktopOnly?: boolean
}

const NAV: NavItem[] = [
  { to: '/', key: 'nav.home', mobile: true },
  { to: '/capture', key: 'nav.capture', mobile: false, desktopOnly: true },
  { to: '/inbox', key: 'nav.inbox', mobile: true },
  { to: '/review', key: 'nav.review', mobile: true },
  { to: '/stats', key: 'nav.stats', mobile: true },
  { to: '/library', key: 'nav.library', mobile: true },
  { to: '/kanji', key: 'nav.kanji', mobile: false },
  { to: '/sources', key: 'nav.sources', mobile: false },
  { to: '/settings', key: 'nav.settings', mobile: true },
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
          <span class="block type-micro text-ink-35">{{ t('shell.tagline') }}</span>
        </span>
      </RouterLink>

      <nav class="flex flex-col gap-0.5 type-body">
        <RouterLink
          v-for="item in nav"
          :key="item.to"
          :to="item.to"
          class="py-1.5 no-underline"
          :class="active(item.to) ? 'text-accent' : 'text-ink-70 hover:text-ink'"
        >
          <span :class="active(item.to) ? 'border-b border-accent pb-[3px]' : ''">{{
            t(item.key)
          }}</span>
        </RouterLink>
      </nav>

      <div class="mt-auto type-micro leading-[1.7] text-ink-35">
        <template v-if="app.activeSession">
          <div class="border-t border-rule pt-2.5">{{ t('shell.activeSession') }}</div>
          <div class="text-ink-50">
            {{ app.activeSession.source_title ?? t('shell.noSource') }} ·
            <span class="num">{{ app.activeSession.line_count }}</span> {{ t('shell.lines') }}
          </div>
        </template>
        <div class="num mt-2.5" :class="app.activeSession ? '' : 'border-t border-rule pt-2.5'">
          v{{ app.health?.version ?? '…' }} · {{ device.device?.name ?? device.kind }}
        </div>
      </div>
    </aside>

    <div class="flex min-h-dvh flex-1 flex-col">
      <p v-if="app.offline" class="m-0 bg-accent-100 px-5 py-2 type-meta text-gold">
        {{ t('shell.offline') }}
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
        class="fixed inset-x-0 bottom-0 z-20 flex border-t border-divider bg-bg font-head type-note md:hidden"
        style="padding-bottom: max(26px, env(safe-area-inset-bottom))"
      >
        <RouterLink
          v-for="item in mobileNav"
          :key="item.to"
          :to="item.to"
          class="relative flex-1 py-2.5 text-center no-underline"
          :class="active(item.to) ? 'text-accent' : 'text-ink-50'"
        >
          <span
            v-if="active(item.to)"
            class="absolute left-1/2 top-0 h-0.5 w-[26px] -translate-x-1/2 bg-accent"
          />
          {{ t(item.key) }}
        </RouterLink>
      </nav>
    </div>

    <!-- 提示：压在内容上方，不占布局 -->
    <div
      class="pointer-events-none fixed inset-x-0 top-3 z-50 flex flex-col items-center gap-2 px-4"
    >
      <TransitionGroup name="rise">
        <p
          v-for="toast in app.toasts"
          :key="toast.id"
          class="pointer-events-auto m-0 rounded-ui border px-4 py-2 type-note shadow-[var(--shadow)]"
          :class="
            toast.kind === 'error'
              ? 'border-accent bg-accent-100 text-gold'
              : 'border-divider bg-paper text-ink'
          "
        >
          {{ toast.text }}
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
