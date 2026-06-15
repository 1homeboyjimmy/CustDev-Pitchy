/**
 * Temporarily store files and requirements to be uploaded
 * Used to immediately navigate after clicking Start Engine on home page, API call is made on Process page
 */
import { reactive } from 'vue'

const state = reactive({
  files: [],
  simulationRequirement: '',
  isPending: false,
  // Контекст гипотезы (для шага «Сигналы»): запрос разведки + сегменты ЦА.
  signalQuery: '',
  segments: []
})

export function setPendingUpload(files, requirement) {
  state.files = files
  state.simulationRequirement = requirement
  state.isPending = true
}

// Контекст для разведки сигналов (задаётся на экране «Гипотеза»).
export function setHypothesisContext(query, segments) {
  state.signalQuery = query || ''
  state.segments = Array.isArray(segments) ? segments : []
}

export function getPendingUpload() {
  return {
    files: state.files,
    simulationRequirement: state.simulationRequirement,
    isPending: state.isPending,
    signalQuery: state.signalQuery,
    segments: state.segments
  }
}

export function clearPendingUpload() {
  state.files = []
  state.simulationRequirement = ''
  state.isPending = false
  state.signalQuery = ''
  state.segments = []
}

export default state
