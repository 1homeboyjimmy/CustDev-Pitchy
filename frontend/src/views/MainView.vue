<template>
  <div class="fixed inset-0 z-0 overflow-hidden pointer-events-none">
    <div class="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-white/10 blur-[120px] rounded-full"></div>
    <div class="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-white/10 blur-[120px] rounded-full"></div>
    <div class="absolute inset-0 bg-[linear-gradient(to_right,#ffffff05_1px,transparent_1px),linear-gradient(to_bottom,#ffffff05_1px,transparent_1px)] bg-[size:40px_40px] opacity-10"></div>
  </div>

  <div class="fixed inset-0 pt-20 flex flex-col overflow-hidden bg-transparent z-10 pointer-events-auto">
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Specialized Workflow Header -->
      <header class="h-14 border-b border-white/5 flex items-center justify-between px-6 bg-pitchy-bg/50 backdrop-blur-md z-20 relative w-full">
        <!-- Left Section -->
        <div class="flex items-center gap-4 flex-1 justify-start">
          <button @click="router.push('/')" class="p-2 hover:bg-white/5 rounded-lg transition-colors text-white/40 hover:text-white">
            <HomeIcon class="w-4 h-4" />
          </button>
          <div class="h-4 w-px bg-white/10"></div>
          <div class="flex items-center gap-3">
            <span class="text-[10px] font-bold text-white/30 uppercase tracking-[0.2em]">Шаг {{ currentStep }}/5</span>
            <span class="text-sm font-bold text-white tracking-tight">{{ stepNames[currentStep - 1] }}</span>
          </div>
        </div>

        <!-- Center Section (Absolute Centering) -->
        <div class="absolute left-1/2 -translate-x-1/2 flex items-center gap-2 bg-white/5 p-1 rounded-xl border border-white/5">
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

        <!-- Right Section -->
        <div class="flex items-center gap-4 flex-1 justify-end">
          <div class="flex flex-col items-end">
            <span class="text-[10px] font-mono text-white/20 uppercase">{{ currentProjectId?.slice(0, 8) }}</span>
            <StatusBadge :type="statusClass" :dot="currentPhase < 2">
              {{ statusText }}
            </StatusBadge>
          </div>
        </div>
      </header>

      <!-- Main Layout area -->
      <main class="flex-1 flex flex-col overflow-hidden relative">
        <!-- Panels area -->
        <div class="flex-1 flex overflow-hidden lg:flex-row flex-col">
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
              :currentPhase="currentPhase"
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
            <div class="h-full overflow-y-auto custom-scrollbar pb-12">
              <div class="p-8 max-w-4xl mx-auto space-y-8">
                <Step1GraphBuild 
                  v-if="currentStep === 1"
                  :currentPhase="currentPhase"
                  :projectData="projectData"
                  :ontologyProgress="ontologyProgress"
                  :buildProgress="buildProgress"
                  :graphData="graphData"
                  @next-step="handleNextStep"
                  @stop-task="stopPolling(); addLog('Поток анализа остановлен пользователем.'); currentPhase = 2;"
                />
                
                <!-- Step 2: Env Setup -->
                <Step2EnvSetup
                  v-else-if="currentStep === 2"
                  :projectData="projectData"
                  :graphData="graphData"
                  @go-back="handleGoBack"
                  @next-step="handleNextStep"
                  @add-log="addLog"
                />
              </div>
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
            <span v-if="!isTerminalCollapsed">АДРЕС_ПРОЕКТА: {{ currentProjectId?.slice(0, 12) }}</span>
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
            Waiting for system manifest...
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const props = defineProps({
  projectId: {
    type: String,
    required: false
  }
})

import StatusBadge from '../components/ui/StatusBadge.vue'
import GraphPanel from '../components/GraphPanel.vue'
import Step1GraphBuild from '../components/Step1GraphBuild.vue'
import Step2EnvSetup from '../components/Step2EnvSetup.vue'
import { 
  Home as HomeIcon,
  Terminal as TerminalIcon,
  ChevronUp as ChevronUpIcon,
  ChevronDown as ChevronDownIcon
} from 'lucide-vue-next'
import { generateOntology, getProject, buildGraph, getTaskStatus, getGraphData } from '../api/graph'
import { getPendingUpload, clearPendingUpload } from '../store/pendingUpload'

const route = useRoute()
const router = useRouter()

// Layout State
const viewMode = ref('split')
const isTerminalCollapsed = ref(true)
const logContent = ref(null)
const currentStep = ref(1)
const stepNames = ['Построение графа', 'Общество агентов', 'Симуляция', 'Ответные меры', 'Взаимодействие']

// Handle Terminal Expansion vs Graph Height
watch(isTerminalCollapsed, () => {
  // Give it a moment for the transition to finish
  setTimeout(() => {
    window.dispatchEvent(new Event('resize'))
  }, 500)
})

// Data State
const currentProjectId = ref(route.params.projectId)
const loading = ref(false)
const graphLoading = ref(false)
const error = ref('')
const projectData = ref(null)
const graphData = ref(null)
const currentPhase = ref(-1) // -1: Upload, 0: Ontology, 1: Build, 2: Complete
const ontologyProgress = ref(null)
const buildProgress = ref(null)
const systemLogs = ref([])

// Polling timers
let pollTimer = null
let graphPollTimer = null

// --- Status Computed ---
const statusClass = computed(() => {
  if (error.value) return 'danger'
  if (currentPhase.value >= 2) return 'success'
  return 'primary'
})

const statusText = computed(() => {
  if (error.value) return 'Ошибка системы'
  if (currentPhase.value >= 2) return 'Готово'
  if (currentPhase.value === 1) return 'Построение графа'
  if (currentPhase.value === 0) return 'Анализ онтологии'
  return 'Инициализация'
})

// --- Helpers ---
const addLog = (msg) => {
  const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
  systemLogs.value.push({ time, msg })  // Push to end for terminal behavior
  if (systemLogs.value.length > 100) systemLogs.value.shift()
  
  nextTick(() => {
    if (logContent.value) {
      logContent.value.scrollTop = logContent.value.scrollHeight
    }
  })
}

const handleNextStep = () => {
  if (currentStep.value < 5) {
    currentStep.value++
    addLog(`Переход к шагу ${currentStep.value}: ${stepNames[currentStep.value - 1]}`)
  }
}

const handleGoBack = () => {
  if (currentStep.value > 1) {
    currentStep.value--
    addLog(`Возврат к шагу ${currentStep.value}: ${stepNames[currentStep.value - 1]}`)
  }
}

// --- Data Logic ---

const initProject = async () => {
  addLog('Среда симуляции инициализирована.')
  if (currentProjectId.value === 'new') {
    await handleNewProject()
  } else {
    await loadProject()
  }
}

const handleNewProject = async () => {
  const pending = getPendingUpload()
  if (!pending.isPending || pending.files.length === 0) {
    error.value = 'Файлы для загрузки не найдены.'
    addLog('Критическая ошибка: Файлы для нового проекта не найдены.')
    return
  }
  
  try {
    loading.value = true
    currentPhase.value = 0
    ontologyProgress.value = { message: 'Анализ архитектуры общества...' }
    addLog('Запуск генерации онтологии...')
    
    const formData = new FormData()
    pending.files.forEach(f => formData.append('files', f))
    formData.append('simulation_requirement', pending.simulationRequirement)
    
    const res = await generateOntology(formData)
    if (res.success) {
      clearPendingUpload()
      currentProjectId.value = res.data.project_id
      projectData.value = res.data
      router.replace({ name: 'Process', params: { projectId: res.data.project_id } })
      ontologyProgress.value = null
      addLog(`Онтология успешно синтезирована для проекта ${res.data.project_id}`)
      await startBuildGraph()
    } else {
      error.value = res.error || 'Анализ синтаксиса не удался'
      addLog(`Ошибка при синтезе: ${error.value}`)
    }
  } catch (err) {
    error.value = err.message
    addLog(`Исключение в конвейере синтеза: ${err.message}`)
  } finally {
    loading.value = false
  }
}

const loadProject = async () => {
  try {
    loading.value = true
    addLog(`Восстановление состояния проекта: ${currentProjectId.value}`)
    const res = await getProject(currentProjectId.value)
    if (res.success) {
      projectData.value = res.data
      updatePhaseByStatus(res.data.status)
      addLog(`Состояние проекта восстановлено. Режим: ${res.data.status}`)
      
      if (res.data.status === 'ontology_generated' && !res.data.graph_id) {
        await startBuildGraph()
      } else if (res.data.status === 'graph_building' && res.data.graph_build_task_id) {
        currentPhase.value = 1
        startPollingTask(res.data.graph_build_task_id)
        startGraphPolling()
      } else if (res.data.status === 'graph_completed' && res.data.graph_id) {
        currentPhase.value = 2
        await loadGraph(res.data.graph_id)
      }
    } else {
      error.value = res.error
      addLog(`Ошибка восстановления проекта: ${res.error}`)
    }
  } catch (err) {
    error.value = err.message
    addLog(`Исключение при восстановлении: ${err.message}`)
  } finally {
    loading.value = false
  }
}

const updatePhaseByStatus = (status) => {
  switch (status) {
    case 'created':
    case 'ontology_generated': currentPhase.value = 0; break;
    case 'graph_building': currentPhase.value = 1; break;
    case 'graph_completed': currentPhase.value = 2; break;
    case 'failed': error.value = 'Ошибка фазы'; break;
  }
}

const startBuildGraph = async () => {
  try {
    currentPhase.value = 1
    buildProgress.value = { progress: 0, message: 'Построение узлов...' }
    addLog('Запуск построения графа знаний...')
    
    const res = await buildGraph({ project_id: currentProjectId.value })
    if (res.success) {
      addLog(`Задача построения графа в очереди. ID: ${res.data.task_id}`)
      startGraphPolling()
      startPollingTask(res.data.task_id)
    } else {
      error.value = res.error
      addLog(`Очередь построения отклонена: ${res.error}`)
    }
  } catch (err) {
    error.value = err.message
    addLog(`Исключение в конвейере построения: ${err.message}`)
  }
}

const startGraphPolling = () => {
  fetchGraphData()
  graphPollTimer = setInterval(fetchGraphData, 10000)
}

const fetchGraphData = async () => {
  try {
    const projRes = await getProject(currentProjectId.value)
    if (projRes.success && projRes.data.graph_id) {
      const gRes = await getGraphData(projRes.data.graph_id)
      if (gRes.success) {
        graphData.value = gRes.data
        const nodeCount = gRes.data.node_count || gRes.data.nodes?.length || 0
        addLog(`Синхронизация состояния графа. Узлов: ${nodeCount}`)
      }
    }
  } catch (err) {
    console.warn('Синхронизация задерживается:', err.message)
  }
}

const startPollingTask = (taskId) => {
  pollTaskStatus(taskId)
  pollTimer = setInterval(() => pollTaskStatus(taskId), 2000)
}

const pollTaskStatus = async (taskId) => {
  try {
    const res = await getTaskStatus(taskId)
    if (res.success) {
      const task = res.data
      if (task.message && task.message !== buildProgress.value?.message) {
        addLog(task.message)
      }
      buildProgress.value = { progress: task.progress || 0, message: task.message }
      if (task.status === 'completed') {
        addLog('Построение графа завершено.')
        stopPolling()
        stopGraphPolling()
        currentPhase.value = 2
        const projRes = await getProject(currentProjectId.value)
        if (projRes.success && projRes.data.graph_id) {
            projectData.value = projRes.data
            await loadGraph(projRes.data.graph_id)
        }
      } else if (task.status === 'failed') {
        stopPolling()
        error.value = task.error
        addLog(`Задача провалена: ${task.error}`)
      }
    }
  } catch (e) {
    console.error(e)
  }
}

const loadGraph = async (graphId) => {
  graphLoading.value = true
  try {
    const res = await getGraphData(graphId)
    if (res.success) {
      graphData.value = res.data
      addLog('Полный граф синхронизирован.')
    }
  } catch (e) {
    addLog(`Ошибка синхронизации: ${e.message}`)
  } finally {
    graphLoading.value = false
  }
}

const refreshGraph = () => {
  if (projectData.value?.graph_id) {
    addLog('Запущена ручная синхронизация графа.')
    loadGraph(projectData.value.graph_id)
  }
}

const stopPolling = () => {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = null
}

const stopGraphPolling = () => {
  if (graphPollTimer) clearInterval(graphPollTimer)
  graphPollTimer = null
}

onMounted(initProject)
onUnmounted(() => {
  stopPolling()
  stopGraphPolling()
})
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.1);
}
</style>
