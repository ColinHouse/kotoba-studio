<script setup lang="ts">
import { nextTick, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { mediaUrl } from '@/api/client'
import type { Line } from '@/api/types'
import { relTime } from '@/utils/format'
import { confirmShortcut } from '@/utils/platform'
import { followsNewest } from '@/utils/scroll'

const props = defineProps<{ lines: Line[]; inboxLink: string; elapsed?: string | null }>()

const shortcut = confirmShortcut(navigator.userAgent)

/**
 * New lines arrive while the user may be reading earlier ones. Grow-only: an
 * in-place dedup update keeps the row and its scroll position; a genuinely new
 * line follows only when the reader was already at the bottom.
 */
watch(
  () => props.lines.length,
  async (now, before) => {
    if (now <= before) return
    const scroll = document.documentElement
    const follow = followsNewest(window.scrollY, window.innerHeight, scroll.scrollHeight)
    await nextTick()
    if (follow) window.scrollTo({ top: document.documentElement.scrollHeight })
  },
)
</script>

<template>
  <section class="flex min-w-0 flex-col">
    <div class="flex items-baseline justify-between">
      <h2 class="m-0 font-head text-[18px] font-normal">本次收藏</h2>
      <span class="num text-[11px] text-ink-35">
        {{ lines.length }} 句<template v-if="elapsed"> · {{ elapsed }}</template>
      </span>
    </div>

    <TransitionGroup tag="ul" name="list" class="relative m-0 mt-3 flex list-none flex-col p-0">
      <li
        v-for="(line, i) in lines"
        :key="line.id"
        class="flex gap-[11px] border-rule py-3 first:pt-0"
        :class="i < lines.length - 1 ? 'border-b' : ''"
      >
        <img
          v-if="line.screenshot_path"
          :src="mediaUrl(line.screenshot_path)"
          class="plate h-[42px] w-[74px] shrink-0"
          style="border-width: 4px"
          alt=""
        />
        <div class="min-w-0">
          <p class="jp m-0 text-[14px] leading-[1.7]" :class="i === 0 ? 'text-ink' : 'text-ink-70'">
            <!-- 同一行的文字变长（去重时会就地更新）只让文字淡入，整行不重新入场；
                 新建的行由上面的 list 过渡负责整行出现。 -->
            <Transition name="ink"
              ><span :key="line.text">{{ line.text }}</span></Transition
            >
          </p>
          <p class="m-0 mt-px text-[10px] text-ink-35">
            {{ line.origin }} · {{ relTime(line.captured_at) }}
          </p>
        </div>
      </li>
    </TransitionGroup>

    <p v-if="!lines.length" class="m-0 text-[12px] leading-relaxed text-ink-35">
      收藏的句子会出现在这里；游戏结束后到收件箱统一整理。
    </p>
    <RouterLink v-else :to="inboxLink" class="btn-quiet mt-4 self-start">去收件箱整理 →</RouterLink>

    <div class="mt-auto border-t border-rule pt-[18px] text-[11px] leading-[1.9] text-ink-35">
      <p class="kicker m-0 text-ink-50">键盘</p>
      <p class="num m-0">{{ shortcut }} 收藏这句</p>
    </div>
  </section>
</template>

<style scoped>
/* No leave classes on purpose: the changed text is replaced at once and only
   the new text fades in — removing a line's text would look like a deletion. */
.ink-enter-active {
  transition: opacity var(--mo-quick) var(--ease-soft);
}
.ink-enter-from {
  opacity: 0;
}
</style>
