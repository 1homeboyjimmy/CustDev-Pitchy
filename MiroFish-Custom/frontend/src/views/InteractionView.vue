<template>
  <AppLayout>
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Specialized Workflow Header -->
      <header class="h-14 border-b border-white/5 flex items-center justify-between px-6 bg-pitchy-bg/50 backdrop-blur-md z-20">
        <div class="flex items-center gap-4">
          <button @click="router.push({ name: 'Report', params: { reportId: currentReportId } })" class="p-2 hover:bg-white/5 rounded-lg transition-colors text-white/40 hover:text-white">
            <ArrowLeftIcon class="w-4 h-4" />
          </button>
          <div class="h-4 w-px bg-white/10"></div>
          <div class="flex items-center gap-3">
            <span class="text-[10px] font-bold text-white/30 uppercase tracking-[0.2em]">Шаг 5/5</span>
            <span class="text-sm font-bold text-white tracking-tight">Структурированный когнитивный диалог</span>
          </div>
        </div>

        <div class="flex items-center gap-2 bg-white/5 p-1 rounded-xl border border-white/5">
          <button 
            v-for="mode in ['graph', 'split', 'workbench']" 
            :key="mode"
            @click="viewMode = mode"
            class="px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest rounded-lg transition-all"
            :class="viewMode === mode ? 'bg-pitchy-violet text-white shadow-glow-primary' : 'text-white/40 hover:text-white/60'"
          >
            {{ mode === 'graph' ? 'Граф' : (mode === 'split' ? 'Разделение' : 'Рабочая зона') }}
          </button>
        </div>

        <div class="flex items-center gap-4">
          <div class="flex flex-col items-end">
            <span class="text-[10px] font-mono text-white/20 uppercase tracking-tighter">{{ simulationId?.slice(0, 8) || 'БЕЗ_ID' }}</span>
            <StatusBadge :type="currentStatus === 'error' ? 'danger' : (currentStatus === 'processing' ? 'primary' : 'success')" :dot="currentStatus === 'processing'">
              {{ currentStatus === 'error' ? 'Ошибка связи' : (currentStatus === 'processing' ? 'Активно' : 'Готово') }}
            </StatusBadge>
          </div>
        </div>
      </header>

      <!-- Main Layout -->
      <main class="flex-1 flex overflow-hidden relative">
        <!-- Left Panel: Graph -->
        <div 
          class="h-full border-r border-white/5 transition-all duration-700 ease-[cubic-bezier(0.23,1,0.32,1)]"
          :class="{
            'w-full opacity-100': viewMode === 'graph',
            'w-0 opacity-0 pointer-events-none': viewMode === 'workbench',
            'w-1/2 opacity-100': viewMode === 'split'
          }"
        >
          <GraphPanel 
            :graphData="graphData"
            :loading="graphLoading"
            :currentPhase="5"
            @refresh="refreshGraph"
          />
        </div>

        <!-- Right Panel: Interaction -->
        <div 
          class="h-full transition-all duration-700 ease-[cubic-bezier(0.23,1,0.32,1)] bg-pitchy-bg/30"
          :class="{
            'w-full opacity-100': viewMode === 'workbench',
            'w-0 opacity-0 pointer-events-none': viewMode === 'graph',
            'w-1/2 opacity-100': viewMode === 'split'
          }"
        >
          <div class="h-full">
            <Step5Interaction
              :reportId="currentReportId"
              :simulationId="simulationId"
              :projectData="projectData"
              :systemLogs="systemLogs"
              @add-log="addLog"
              @update-status="updateStatus"
            />
          </div>
        </div>
      </main>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppLayout from '../components/layout/AppLayout.vue'
import GraphPanel from '../components/GraphPanel.vue'
import Step5Interaction from '../components/Step5Interaction.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import { 
  ArrowLeft as ArrowLeftIcon
} from 'lucide-vue-next'
import { getProject, getGraphData } from '../api/graph'
import { getSimulation } from '../api/simulation'
import { getReport } from '../api/report'

const route = useRoute()
const router = useRouter()

const props = defineProps({
  reportId: String
})

// Layout State
const viewMode = ref('split')
const currentStatus = ref('ready')

// Data State
const currentReportId = ref(route.params.reportId)
const simulationId = ref(null)
const projectData = ref(null)
const graphData = ref(null)
const graphLoading = ref(false)
const systemLogs = ref([])

// --- Helpers ---
const addLog = (msg) => {
  const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
  systemLogs.value.unshift({ time, msg })
  if (systemLogs.value.length > 200) systemLogs.value.pop()
}

const updateStatus = (status) => {
  currentStatus.value = status
}

const loadReportData = async () => {
  try {
    addLog(`Установка глубокой связи с отчетом: ${currentReportId.value}`)
    const reportRes = await getReport(currentReportId.value)
    if (reportRes.success && reportRes.data) {
      const reportData = reportRes.data
      simulationId.value = reportData.simulation_id
      
      if (simulationId.value) {
        const simRes = await getSimulation(simulationId.value)
        if (simRes.success && simRes.data) {
          const simData = simRes.data
          if (simData.project_id) {
            const projRes = await getProject(simData.project_id)
            if (projRes.success && projRes.data) {
              projectData.value = projRes.data
              if (projRes.data.graph_id) await loadGraph(projRes.data.graph_id)
            }
          }
        }
      }
    }
  } catch (err) {
    addLog(`Прерывание связи: ${err.message}`)
  }
}

const loadGraph = async (graphId) => {
  graphLoading.value = true
  try {
    const res = await getGraphData(graphId)
    if (res.success) {
      graphData.value = res.data
      addLog('Когнитивный граф синхронизирован.')
    }
  } catch (err) {
    addLog(`Ошибка загрузки графа: ${err.message}`)
  } finally {
    graphLoading.value = false
  }
}

const refreshGraph = () => {
  if (projectData.value?.graph_id) loadGraph(projectData.value.graph_id)
}

watch(() => route.params.reportId, (newId) => {
  if (newId && newId !== currentReportId.value) {
    currentReportId.value = newId
    loadReportData()
  }
}, { immediate: true })

onMounted(() => {
  addLog('Слой взаимодействия инициализирован.')
  loadReportData()
})
</script>

<style scoped>
</style>
