<template>
  <StageShell active-id="custdev">
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Specialized Workflow Header -->
      <header class="h-14 border-b border-white/5 flex items-center justify-between px-6 bg-pitchy-bg/50 backdrop-blur-md z-20">
        <div class="flex items-center gap-4">
          <button @click="handleGoBack" class="p-2 hover:bg-white/5 rounded-lg transition-colors text-white/40 hover:text-white">
            <ArrowLeftIcon class="w-4 h-4" />
          </button>
          <div class="h-4 w-px bg-white/10"></div>
          <div class="flex items-center gap-3">
            <span class="text-[10px] font-bold text-white/30 uppercase tracking-[0.2em]">Шаг 3/5</span>
            <span class="text-sm font-bold text-white tracking-tight">Активная симуляция мультивселенной</span>
          </div>
        </div>

        <div class="flex items-center gap-2 bg-white/5 p-1 rounded-xl border border-white/5">
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

        <div class="flex items-center gap-4">
          <div class="flex flex-col items-end">
            <span class="text-[10px] font-mono text-white/20 uppercase">{{ currentSimulationId?.slice(0, 8) }}</span>
            <StatusBadge :type="statusClass" :dot="isSimulating">
              {{ statusText }}
            </StatusBadge>
          </div>
        </div>
      </header>

      <!-- Main Layout -->
      <main class="flex-1 flex overflow-hidden relative">
        <!-- Left Panel: Graph (Real-time updates) -->
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
            :currentPhase="3"
            :isSimulating="isSimulating"
            @refresh="refreshGraph"
          />
        </div>

        <!-- Right Panel: Simulation Feed & Controls -->
        <div 
          class="h-full transition-all duration-700 ease-[cubic-bezier(0.23,1,0.32,1)] bg-pitchy-bg/30"
          :class="{
            'w-full opacity-100': viewMode === 'workbench',
            'w-0 opacity-0 pointer-events-none': viewMode === 'graph',
            'w-1/2 opacity-100': viewMode === 'split'
          }"
        >
          <div class="h-full overflow-y-auto custom-scrollbar">
            <div class="p-8 max-w-5xl mx-auto space-y-8">
              <Step3Simulation
                :simulationId="currentSimulationId"
                :maxRounds="maxRounds"
                :minutesPerRound="minutesPerRound"
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
  </StageShell>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import StageShell from '../components/layout/StageShell.vue'
import GraphPanel from '../components/GraphPanel.vue'
import Step3Simulation from '../components/Step3Simulation.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import { 
  ArrowLeft as ArrowLeftIcon
} from 'lucide-vue-next'
import { getProject, getGraphData } from '../api/graph'
import { getSimulation, getSimulationConfig, stopSimulation, closeSimulationEnv, getEnvStatus } from '../api/simulation'

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
const maxRounds = ref(route.query.maxRounds ? parseInt(route.query.maxRounds) : null)
const minutesPerRound = ref(30)
const projectData = ref(null)
const graphData = ref(null)
const graphLoading = ref(false)
const systemLogs = ref([])

// --- Status Computed ---
const statusClass = computed(() => {
  if (currentStatus.value === 'error') return 'danger'
  if (currentStatus.value === 'completed') return 'success'
  return 'primary'
})

const statusText = computed(() => {
  if (currentStatus.value === 'error') return 'Ошибка пульса'
  if (currentStatus.value === 'completed') return 'Цикл завершен'
  return 'Симуляция активна'
})

const isSimulating = computed(() => currentStatus.value === 'processing')

// --- Helpers ---
const addLog = (msg) => {
  const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
  systemLogs.value.unshift({ time, msg })
  if (systemLogs.value.length > 200) systemLogs.value.pop()
}

const updateStatus = (status) => {
  currentStatus.value = status
}

const handleGoBack = async () => {
  addLog('Завершение текущего цикла симуляции...')
  stopGraphRefresh()
  try {
    const envStatusRes = await getEnvStatus({ simulation_id: currentSimulationId.value })
    if (envStatusRes.success && envStatusRes.data?.env_alive) {
      await closeSimulationEnv({ simulation_id: currentSimulationId.value, timeout: 5 })
    } else if (isSimulating.value) {
      await stopSimulation({ simulation_id: currentSimulationId.value })
    }
  } catch (err) {
    console.warn(err)
  }
  router.push({ name: 'Simulation', params: { simulationId: currentSimulationId.value } })
}

const handleNextStep = () => {
  addLog('Цикл завершен. Переход к аналитическому синтезу.')
}

// --- Data Logic ---
const loadSimulationData = async () => {
  try {
    addLog(`Установка связи с симуляцией: ${currentSimulationId.value}`)
    const simRes = await getSimulation(currentSimulationId.value)
    if (simRes.success && simRes.data) {
      const simData = simRes.data
      try {
        const configRes = await getSimulationConfig(currentSimulationId.value)
        if (configRes.success && configRes.data?.time_config?.minutes_per_round) {
          minutesPerRound.value = configRes.data.time_config.minutes_per_round
        }
      } catch (e) {}

      if (simData.project_id) {
        const projRes = await getProject(simData.project_id)
        if (projRes.success && projRes.data) {
          projectData.value = projRes.data
          if (projRes.data.graph_id) await loadGraph(projRes.data.graph_id)
        }
      }
    }
  } catch (err) {
    addLog(`Ошибка связи: ${err.message}`)
  }
}

const loadGraph = async (graphId) => {
  if (!isSimulating.value) graphLoading.value = true
  try {
    const res = await getGraphData(graphId)
    if (res.success) {
      graphData.value = res.data
      if (!isSimulating.value) addLog('Граф знаний синхронизирован.')
    }
  } catch (err) {
    addLog(`Задержка синхронизации графа: ${err.message}`)
  } finally {
    graphLoading.value = false
  }
}

const refreshGraph = () => {
  if (projectData.value?.graph_id) loadGraph(projectData.value.graph_id)
}

let graphRefreshTimer = null
const startGraphRefresh = () => {
  if (graphRefreshTimer) return
  graphRefreshTimer = setInterval(refreshGraph, 30000)
}

const stopGraphRefresh = () => {
  if (graphRefreshTimer) {
    clearInterval(graphRefreshTimer)
    graphRefreshTimer = null
  }
}

watch(isSimulating, (nv) => {
  if (nv) startGraphRefresh()
  else stopGraphRefresh()
}, { immediate: true })

onMounted(() => {
  addLog('Цикл симуляции манифестирован.')
  loadSimulationData()
})

onUnmounted(stopGraphRefresh)
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.05); border-radius: 10px; }
</style>
