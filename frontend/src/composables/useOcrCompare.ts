import { ref } from 'vue'
import { compareOcr, setOcrProvider } from '@/api/capture'
import type { CompareResult, Region } from '@/api/types'
import { useAppStore } from '@/stores/app'

/** Run every OCR engine on the framed region and set the chosen one as default. */
export function useOcrCompare() {
  const app = useAppStore()
  const results = ref<CompareResult[]>([])
  const running = ref(false)

  async function run(region: Region) {
    running.value = true
    try {
      results.value = await compareOcr(region)
    } catch (e) {
      app.fail(e)
    } finally {
      running.value = false
    }
  }

  async function setDefault(provider: string) {
    try {
      app.settings = await setOcrProvider(provider)
      app.toast(`默认引擎已设为 ${provider}`, 'success')
    } catch (e) {
      app.fail(e)
    }
  }

  return { results, running, run, setDefault }
}
