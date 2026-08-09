/**
 * Temporarily store files and requirements to be uploaded
 * Used to immediately navigate after clicking Start Engine on home page, API call is made on Process page
 */
import { reactive } from 'vue'

const state = reactive({
  files: [],
  simulationRequirement: '',
  preExtractedText: '',
  isPending: false,
  // Контекст гипотезы (для шага «Сигналы»): запрос разведки + сегменты ЦА.
  signalQuery: '',
  segments: [],
  // Результат разведки сигналов — переносим к созданию симуляции, чтобы
  // прикрепить его к прогону (доступ из истории).
  signalsResult: null
})

export function setPendingUpload(files, requirement) {
  state.files = files
  state.simulationRequirement = requirement
  state.preExtractedText = ''
  state.isPending = true
}

// Контекст для разведки сигналов (задаётся на экране «Гипотеза»).
export function setHypothesisContext(query, segments) {
  state.signalQuery = query || ''
  state.segments = Array.isArray(segments) ? segments : []
}

// Итог разведки сигналов (сохраняется на экране «Сигналы» по завершении).
export function setSignalsResult(result) {
  state.signalsResult = result || null
}

export function setPreExtractedText(text) {
  state.preExtractedText = typeof text === 'string' ? text : ''
}

// Сигналы живут дольше загрузки seed-файла: онтология и граф строятся
// после экрана разведки, поэтому очистка upload-состояния не должна терять
// результат, который ещё предстоит привязать к simulation_id.
export function clearSignalsResult() {
  state.signalsResult = null
}

export function getPendingUpload() {
  return {
    files: state.files,
    simulationRequirement: state.simulationRequirement,
    preExtractedText: state.preExtractedText,
    isPending: state.isPending,
    signalQuery: state.signalQuery,
    segments: state.segments,
    signalsResult: state.signalsResult
  }
}

export function clearPendingUpload() {
  state.files = []
  state.simulationRequirement = ''
  state.preExtractedText = ''
  state.isPending = false
  state.signalQuery = ''
  state.segments = []
}

export default state
