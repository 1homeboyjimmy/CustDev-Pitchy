<template>
  <AppLayout>
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Specialized Workflow Header -->
      <header class="h-14 border-b border-white/5 flex items-center justify-between px-6 bg-pitchy-bg/50 backdrop-blur-md z-20">
        <div class="flex items-center gap-4">
          <button @click="handleGoBack" class="p-2 hover:bg-white/5 rounded-lg transition-colors text-white/40 hover:text-white">
            <ArrowLeftIcon class="w-4 h-4" />
          </button>
          <div class="h-4 w-px bg-white/10"></div>
          <div class="flex items-center gap-3">
            <span class="text-[10px] font-bold text-white/30 uppercase tracking-[0.2em]">Шаг 2/5</span>
            <span class="text-sm font-bold text-white tracking-tight">Картирование среды</span>
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
            <span class="text-[10px] font-mono text-white/20 uppercase">{{ currentSimulationId?.slice(0, 8) }}</span>
            <StatusBadge :type="currentStatus === 'error' ? 'danger' : (currentStatus === 'completed' ? 'success' : 'primary')" :dot="currentStatus === 'processing'">
              {{ currentStatus === 'error' ? 'Ошибка системы' : (currentStatus === 'completed' ? 'Стабильно' : 'Манифестация') }}
            </StatusBadge>
          </div>
        </div>
      </header>

      <!-- Main Layout -->
      <main class="flex-1 flex overflow-hidden relative">
        <!-- Left Panel: Knowledge Graph -->
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
            :currentPhase="2"
            @refresh="refreshGraph"
          />
        </div>

        <!-- Right Panel: Workbench -->
        <div 
          class="h-full transition-all duration-700 ease-[cubic-bezier(0.23,1,0.32,1)] bg-pitchy-bg/30"
          :class="{
            'w-full opacity-100': viewMode === 'workbench',
            'w-0 opacity-0 pointer-events-none': viewMode === 'graph',
            'w-1/2 opacity-100': viewMode === 'split'
          }"
        >
          <div class="h-full overflow-y-auto custom-scrollbar">
            <div class="p-8 max-w-4xl mx-auto space-y-8">
              <Step2EnvSetup
                :simulationId="currentSimulationId"
                :projectData="projectData"
                :graphData="graphData"
                :systemLogs="systemLogs"
                @go-back="handleGoBack"
                @next-step="handleNextStep"
                @add-log="addLog"
                @update-status="updateStatus"
              />
            </div>
          </div>
        </div>
      </main>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppLayout from '../components/layout/AppLayout.vue'
import GraphPanel from '../components/GraphPanel.vue'
import Step2EnvSetup from '../components/Step2EnvSetup.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import { 
  ArrowLeft as ArrowLeftIcon
} from 'lucide-vue-next'
import { getProject, getGraphData } from '../api/graph'
import { getSimulation, stopSimulation, getEnvStatus, closeSimulationEnv } from '../api/simulation'

const route = useRoute()
const router = useRouter()

const props = defineProps({
  simulationId: String
})

// Layout State
const viewMode = ref('split')
const currentStatus = ref('processing')

// Data State
const currentSimulationId = ref(route.params.simulationId)
const projectData = ref(null)
const graphData = ref(null)
const graphLoading = ref(false)
const systemLogs = ref([])

// --- Helpers ---
const addLog = (msg) => {
  const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
  systemLogs.value.unshift({ time, msg })
  if (systemLogs.value.length > 100) systemLogs.value.pop()
}

const updateStatus = (status) => {
  currentStatus.value = status
}

const handleGoBack = () => {
  if (projectData.value?.project_id) {
    router.push({ name: 'Process', params: { projectId: projectData.value.project_id } })
  } else {
    router.push('/')
  }
}

const handleNextStep = (params = {}) => {
  addLog('Манифестация завершена. Переход к Шагу 3: Пульс симуляции.')
  const routeParams = {
    name: 'SimulationRun',
    params: { simulationId: currentSimulationId.value }
  }
  if (params.maxRounds) {
    routeParams.query = { maxRounds: params.maxRounds }
  }
  router.push(routeParams)
}

// --- Data Logic ---
const checkAndStopRunningSimulation = async () => {
  if (!currentSimulationId.value) return
  try {
    const envStatusRes = await getEnvStatus({ simulation_id: currentSimulationId.value })
    if (envStatusRes.success && envStatusRes.data?.env_alive) {
      addLog('Обнаружен существующий пульс симуляции, стабилизация...')
      try {
        const closeRes = await closeSimulationEnv({ simulation_id: currentSimulationId.value, timeout: 5 })
        if (!closeRes.success) await forceStopSimulation()
      } catch (closeErr) {
        await forceStopSimulation()
      }
    }
  } catch (err) {
    console.warn('Проверка статуса задержана:', err.message)
  }
}

const forceStopSimulation = async () => {
  try {
    const stopRes = await stopSimulation({ simulation_id: currentSimulationId.value })
    if (stopRes.success) addLog('Пульс прекращен.')
  } catch (err) {
    console.error(err)
  }
}

const loadSimulationData = async () => {
  try {
    addLog(`Синхронизация с матрицей симуляции: ${currentSimulationId.value}`)
    const simRes = await getSimulation(currentSimulationId.value)
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
  } catch (err) {
    addLog(`Ошибка синхронизации: ${err.message}`)
  }
}

const loadGraph = async (graphId) => {
  graphLoading.value = true
  try {
    const res = await getGraphData(graphId)
    if (res.success) {
      graphData.value = res.data
      addLog('Граф знаний синхронизирован.')
    }
  } catch (err) {
    addLog(`Ошибка синхронизации графа: ${err.message}`)
  } finally {
    graphLoading.value = false
  }
}

const refreshGraph = () => {
  if (projectData.value?.graph_id) loadGraph(projectData.value.graph_id)
}

onMounted(async () => {
  addLog('Среда симуляции манифестирована.')
  await checkAndStopRunningSimulation()
  loadSimulationData()
})
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.05); border-radius: 10px; }
</style>
