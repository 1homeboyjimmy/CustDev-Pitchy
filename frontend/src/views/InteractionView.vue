<template>
  <StageShell active-id="custdev">
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Specialized Workflow Header -->
      <header class="workflow-header min-h-14 border-b border-white/5 flex flex-wrap items-center justify-between gap-2 px-3 py-2 sm:px-6 bg-pitchy-bg/50 backdrop-blur-md z-20">
        <div class="workflow-header-left flex items-center gap-2 sm:gap-4 min-w-0 flex-1">
          <button @click="router.push({ name: 'Report', params: { reportId: currentReportId } })" class="p-2 hover:bg-white/5 rounded-lg transition-colors text-white/40 hover:text-white">
            <ArrowLeftIcon class="w-4 h-4" />
          </button>
          <div class="h-4 w-px bg-white/10"></div>
          <div class="flex items-center gap-2 min-w-0">
            <span class="text-[10px] font-bold text-white/30 uppercase tracking-[0.2em]">Шаг 5/5</span>
            <span class="text-sm font-bold text-white tracking-tight truncate">Структурированный когнитивный диалог</span>
          </div>
        </div>

        <div class="workflow-header-mode order-3 sm:order-none w-full sm:w-auto flex items-center justify-start sm:justify-center gap-2 bg-white/5 p-1 rounded-xl border border-white/5 overflow-x-auto">
          <button 
            v-for="mode in ['graph', 'split', 'workbench']" 
            :key="mode"
            @click="viewMode = mode"
            class="px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest rounded-lg transition-all"
            :class="viewMode === mode ? 'bg-white/10 text-white shadow-[0_0_20px_rgba(255,255,255,0.15)]' : 'text-white/40 hover:text-white/60'"
          >
            {{ mode === 'graph' ? 'Граф' : (mode === 'split' ? 'Разделение' : 'Рабочая зона') }}
          </button>
        </div>

        <div class="workflow-header-right flex items-center gap-4 shrink-0">
          <div class="flex flex-col items-end">
            <span class="text-[10px] font-mono text-white/20 uppercase tracking-tighter">{{ simulationId?.slice(0, 8) || 'БЕЗ_ID' }}</span>
            <StatusBadge :type="currentStatus === 'error' ? 'danger' : (currentStatus === 'processing' ? 'primary' : 'success')" :dot="currentStatus === 'processing'">
              {{ currentStatus === 'error' ? 'Ошибка связи' : (currentStatus === 'processing' ? 'Активно' : 'Готово') }}
            </StatusBadge>
          </div>
        </div>
      </header>

      <!-- Main Layout -->
      <main class="flex-1 flex flex-col overflow-hidden relative">
        <div class="flex-1 flex overflow-hidden lg:flex-row flex-col">
          <!-- Left Panel: Graph -->
          <div 
            class="workflow-panel h-full border-r border-white/5 transition-all duration-700 ease-[cubic-bezier(0.23,1,0.32,1)]"
            :class="{
              'w-full opacity-100 panel-full': viewMode === 'graph',
              'w-0 opacity-0 pointer-events-none panel-hidden': viewMode === 'workbench',
              'w-1/2 opacity-100 panel-split': viewMode === 'split'
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
            class="workflow-panel h-full transition-all duration-700 ease-[cubic-bezier(0.23,1,0.32,1)] bg-pitchy-bg/30"
            :class="{
              'w-full opacity-100 panel-full': viewMode === 'workbench',
              'w-0 opacity-0 pointer-events-none panel-hidden': viewMode === 'graph',
              'w-1/2 opacity-100 panel-split': viewMode === 'split'
            }"
          >
            <div class="h-full overflow-hidden">
              <Step5Interaction
                :reportId="currentReportId"
                :simulationId="simulationId"
                :projectData="projectData"
                @add-log="addLog"
                @update-status="updateStatus"
              />
            </div>
          </div>
        </div>
      </main>

      <!-- Terminal Bar -->
      <div 
        class="bg-[#0A0A0F]/95 border-t border-white/10 overflow-hidden shadow-2xl flex flex-col transition-all duration-500 ease-in-out shrink-0"
        :class="isTerminalCollapsed ? 'h-6' : 'h-48'"
      >
        <div 
          class="h-6 bg-white/[0.02] border-b border-white/5 px-4 flex items-center justify-between text-[7px] font-mono font-bold tracking-[0.2em] text-white/30 shrink-0 cursor-pointer hover:bg-white/[0.04] transition-colors"
          @click="isTerminalCollapsed = !isTerminalCollapsed"
        >
          <div class="flex items-center gap-2">
            <TerminalIcon class="w-3 h-3 text-white/80" />
            ТЕРМИНАЛ_СИСТЕМЫ_Pitchy_PRO [{{ isTerminalCollapsed ? 'СВЕРНУТ' : 'ПУЛЬС_РЕАЛЬНОГО_ВРЕМЕНИ' }}]
          </div>
          <div class="flex items-center gap-4">
            <span v-if="!isTerminalCollapsed">АДРЕС_ОТЧЕТА: {{ currentReportId?.slice(0, 12) }}</span>
            <div class="flex items-center gap-2">
              <span class="text-white/80">{{ systemLogs.length }} ЗАПИСЕЙ</span>
              <ChevronUpIcon v-if="isTerminalCollapsed" class="w-3 h-3" />
              <ChevronDownIcon v-else class="w-3 h-3" />
            </div>
          </div>
        </div>
        <div v-if="!isTerminalCollapsed" class="flex-1 overflow-y-auto p-3 space-y-1 custom-scrollbar font-mono text-[10px]" ref="logContent">
          <div v-for="(log, idx) in systemLogs" :key="idx" class="flex gap-4 group/log">
            <span class="text-white/20 group-hover/log:text-white/40 transition-colors shrink-0">{{ log.time }}</span>
            <span class="text-white/60 group-hover/log:text-white/80 transition-colors break-all">
              <span class="text-white/80 mr-1">>></span> {{ log.msg }}
            </span>
          </div>
          <div v-if="systemLogs.length === 0" class="h-full flex items-center justify-center text-[9px] text-white/10 uppercase tracking-[0.3em]">
            Waiting for report manifest...
          </div>
        </div>
      </div>
    </div>
  </StageShell>
</template>

<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import StageShell from '../components/layout/StageShell.vue'
import GraphPanel from '../components/GraphPanel.vue'
import Step5Interaction from '../components/Step5Interaction.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import { 
  ArrowLeft as ArrowLeftIcon,
  Terminal as TerminalIcon,
  ChevronUp as ChevronUpIcon,
  ChevronDown as ChevronDownIcon
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
const isTerminalCollapsed = ref(false)
const logContent = ref(null)

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
  systemLogs.value.push({ time, msg })
  if (systemLogs.value.length > 200) systemLogs.value.shift()
  
  nextTick(() => {
    if (logContent.value) {
      logContent.value.scrollTop = logContent.value.scrollHeight
    }
  })
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
@media (max-width: 1023.98px) {
  .workflow-panel.panel-split { width: 100% !important; height: 50% !important; min-height: 0; }
  .workflow-panel.panel-full { width: 100% !important; height: 100% !important; }
  .workflow-panel.panel-hidden { width: 100% !important; height: 0 !important; border: 0; }
}

@media (max-width: 640px) {
  .workflow-header-right span:first-child { display: none; }
  .workflow-header-mode { scrollbar-width: none; }
  .workflow-header-mode::-webkit-scrollbar { display: none; }
  .workflow-header-mode button { flex: 0 0 auto; }
}
</style>
