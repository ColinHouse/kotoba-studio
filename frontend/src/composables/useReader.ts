import { computed, ref, watch } from 'vue'
import { api } from '@/api/client'
import type { ReaderPage, ReaderPages } from '@/api/types'
import { useAppStore } from '@/stores/app'
import type { PageTurn } from '@/utils/reader'

const DIRECTION_KEY = 'kotoba.reader.rtl'

/** 日漫默认从右往左；偏好存在本机，隐私模式下读不到就用默认值。 */
function storedRtl(): boolean {
  try {
    return globalThis.localStorage?.getItem(DIRECTION_KEY) !== 'ltr'
  } catch {
    return true
  }
}

/** The reader: the pages, which one is showing, and which way pages turn. */
export function useReader(sourceId: number) {
  const app = useAppStore()
  const title = ref('')
  const pages = ref<ReaderPage[]>([])
  const index = ref(0)
  const rtl = ref(storedRtl())
  const loading = ref(true)

  const current = computed<ReaderPage | null>(() => pages.value[index.value] ?? null)

  async function load() {
    loading.value = true
    try {
      const data = await api.get<ReaderPages>(`/api/sources/${sourceId}/pages`)
      title.value = data.title
      pages.value = data.pages
    } catch (e) {
      app.fail(e)
    } finally {
      loading.value = false
    }
  }

  function turn(direction: PageTurn) {
    if (direction === 'next') index.value = Math.min(index.value + 1, pages.value.length - 1)
    else if (direction === 'prev') index.value = Math.max(index.value - 1, 0)
  }

  watch(rtl, (value) => {
    try {
      globalThis.localStorage?.setItem(DIRECTION_KEY, value ? 'rtl' : 'ltr')
    } catch {
      /* 隐私模式：偏好只活在这次会话里 */
    }
  })

  return { title, pages, index, current, rtl, loading, load, turn }
}
