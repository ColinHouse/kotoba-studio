import { ref, watch, type Ref } from 'vue'
import { api } from '@/api/client'
import type {
  CollectResult,
  Display,
  Line,
  OcrResult,
  Provider,
  Region,
  Screenshot,
} from '@/api/types'
import { useAppStore } from '@/stores/app'

const REGION_SAVE_DELAY_MS = 400

interface Options {
  sessionId: Ref<number | null>
  /** Persist the framed region so the next session reuses it. */
  persistRegion: (region: Region) => Promise<void> | void
  onLine: (line: Line) => void
}

/** Screenshot → frame a region → OCR or collect. Desktop only. */
export function useScreenCapture({ sessionId, persistRegion, onLine }: Options) {
  const app = useAppStore()
  const displays = ref<Display[]>([])
  const display = ref(0)
  const providers = ref<Provider[]>([])
  const provider = ref('auto')
  const shot = ref<Screenshot | null>(null)
  const region = ref<Region | null>(null)
  const ocr = ref<OcrResult | null>(null)
  /** The screenshot the current `ocr` blocks belong to, when one was saved. */
  const ocrImagePath = ref<string | null>(null)
  const busy = ref<'' | 'shot' | 'ocr' | 'collect'>('')
  let saveTimer: number | undefined

  const chosenProvider = () => (provider.value === 'auto' ? null : provider.value)

  async function init() {
    ;[displays.value, providers.value] = await Promise.all([
      api.get<Display[]>('/api/capture/displays').catch(() => []),
      api.get<Provider[]>('/api/capture/providers'),
    ])
    provider.value = app.settings?.ocr_provider ?? 'auto'
  }

  async function takeShot() {
    busy.value = 'shot'
    try {
      shot.value = await api.post<Screenshot>('/api/capture/screenshot', { display: display.value })
    } catch (e) {
      app.fail(e)
    } finally {
      busy.value = ''
    }
  }

  async function runOcr() {
    if (!region.value) return
    busy.value = 'ocr'
    try {
      ocr.value = await api.post<OcrResult>('/api/capture/ocr', {
        region: region.value,
        provider: chosenProvider(),
      })
      // Nothing was saved: the view falls back to the screen preview crop.
      ocrImagePath.value = null
    } catch (e) {
      app.fail(e)
    } finally {
      busy.value = ''
    }
  }

  async function collect() {
    if (!region.value) return
    busy.value = 'collect'
    try {
      const result = await api.post<CollectResult>('/api/capture/collect', {
        region: region.value,
        session_id: sessionId.value,
        provider: chosenProvider(),
      })
      ocr.value = result.ocr
      ocrImagePath.value = result.screenshot_path
      if (!result.line) app.toast('没有识别到文字', 'error')
      else if (result.duplicate) app.toast('这句已经收藏过了')
      else app.toast('已收藏', 'success')
      if (result.line) onLine(result.line)
    } catch (e) {
      app.fail(e)
    } finally {
      busy.value = ''
    }
  }

  // Debounced so dragging the frame doesn't write on every pointer move.
  watch(region, (next) => {
    if (!next) return
    window.clearTimeout(saveTimer)
    saveTimer = window.setTimeout(async () => {
      try {
        await persistRegion(next)
      } catch (e) {
        app.fail(e)
      }
    }, REGION_SAVE_DELAY_MS)
  })

  return {
    displays,
    display,
    providers,
    provider,
    shot,
    region,
    ocr,
    ocrImagePath,
    busy,
    init,
    takeShot,
    runOcr,
    collect,
  }
}
