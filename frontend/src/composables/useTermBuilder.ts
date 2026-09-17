import { ref } from 'vue'
import { api } from '@/api/client'
import type { Analysis, Encounter, Explanation, Term } from '@/api/types'
import type { ConfirmPayload } from '@/components/inbox/TermEditor.vue'
import type { PickedTerm } from '@/components/inbox/TokenChips.vue'
import { useAppStore } from '@/stores/app'

/** 建卡流程只需要这三样；收件箱的 Line 与阅读视图的文字块都满足。 */
export interface BuilderLine {
  id: number
  status: string
  encounter_count: number
}

/** 点词 → 确认建卡。收件箱与阅读视图共用，避免同一条流程有两份实现。 */
export function useTermBuilder() {
  const app = useAppStore()
  const analysis = ref<Analysis | null>(null)
  const picked = ref<PickedTerm | null>(null)
  const result = ref<{ term: Term; encounter: Encounter } | null>(null)
  const busy = ref(false)
  const explaining = ref(false)

  function reset() {
    analysis.value = null
    picked.value = null
    result.value = null
  }

  async function analyze(line: Pick<BuilderLine, 'id'>) {
    try {
      analysis.value = await api.post<Analysis>(`/api/lines/${line.id}/analyze`)
    } catch (e) {
      app.fail(e)
    }
  }

  async function confirm(line: BuilderLine, payload: ConfirmPayload): Promise<boolean> {
    busy.value = true
    try {
      result.value = await api.post<{ term: Term; encounter: Encounter }>('/api/encounters', {
        line_id: line.id,
        ...payload,
      })
      app.toast(
        payload.card_types.length
          ? `已建卡：${result.value.term.headword}`
          : `已记录语境：${result.value.term.headword}`,
        'success',
      )
      line.status = 'kept'
      line.encounter_count += 1
      picked.value = null
      await analyze(line)
      return true
    } catch (e) {
      app.fail(e)
      return false
    } finally {
      busy.value = false
    }
  }

  async function explain() {
    if (!result.value) return
    explaining.value = true
    try {
      const r = await api.post<{ explanation: Explanation }>('/api/ai/explain', {
        encounter_id: result.value.encounter.id,
      })
      result.value.encounter.ai_explanation = r.explanation
    } catch (e) {
      app.fail(e)
    } finally {
      explaining.value = false
    }
  }

  return { analysis, picked, result, busy, explaining, reset, analyze, confirm, explain }
}
