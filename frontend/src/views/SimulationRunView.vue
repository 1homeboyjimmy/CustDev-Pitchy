<template>
  <StageShell active-id="custdev">
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Specialized Workflow Header -->
      <header class="workflow-header h-14 border-b border-white/5 flex items-center justify-between px-6 bg-pitchy-bg/50 backdrop-blur-md z-20">
        <div class="workflow-header-left flex items-center gap-4 min-w-0">
          <button @click="handleGoBack" class="p-2 hover:bg-white/5 rounded-lg transition-colors text-white/40 hover:text-white">
            <ArrowLeftIcon class="w-4 h-4" />
          </button>
          <div class="h-4 w-px bg-white/10"></div>
          <div class="flex items-center gap-3">
            <span class="text-[10px] font-bold text-white/30 uppercase tracking-[0.2em]">Шаг 3/5</span>
            <span class="text-sm font-bold text-white tracking-tight">Фокус-группа общества</span>
          </div>
        </div>

        <button class="workflow-header-mode px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest rounded-lg transition-all bg-white/5 border border-white/5 text-white/50 hover:text-white"
          @click="graphCollapsed = !graphCollapsed"
        >
          {{ graphCollapsed ? 'Показать граф' : 'Свернуть граф' }}
        </button>

        <div class="workflow-header-right flex items-center gap-4 min-w-0">
          <div class="flex flex-col items-end">
            <span class="text-[10px] font-mono text-white/20 uppercase">{{ currentSimulationId?.slice(0, 8) }}</span>
            <StatusBadge :type="statusClass" :dot="isSimulating">
              {{ statusText }}
            </StatusBadge>
          </div>
        </div>
      </header>

      <!-- Main Layout: граф сверху (сворачивается) → фокус-группа → движок -->
      <main class="flex-1 flex flex-col overflow-hidden">
        <!-- Граф (реал-тайм) -->
        <div
          class="border-b border-white/5 transition-all duration-500 ease-[cubic-bezier(0.23,1,0.32,1)] overflow-hidden shrink-0"
          :class="graphCollapsed ? 'h-0 opacity-0' : 'h-[42vh] opacity-100'"
        >
          <GraphPanel
            :graphData="graphData"
            :loading="graphLoading"
            :currentPhase="3"
            :isSimulating="isSimulating"
            @refresh="refreshGraph"
          />
        </div>

        <!-- Фокус-группа + движок -->
        <div class="flex-1 overflow-y-auto custom-scrollbar bg-pitchy-bg/30">
          <div class="p-6 lg:p-8 max-w-5xl mx-auto space-y-8">
            <FocusGroupPanel
              :profiles="profiles"
              :interviewQuestions="interviewQuestions"
              :interviews="interviews"
              :selected="selectedAgent"
              :chatHistory="chatHistory"
              :sending="chatSending"
              :running="interviewRunning"
              :interviewDone="interviewDone"
              :warmth="warmthMap"
              @select-agent="onSelectAgent"
              @send="onSendToAgent"
              @run-interview="runInterview"
            />

            <details class="rounded-2xl border border-white/10 bg-white/[0.02] overflow-hidden">
              <summary class="cursor-pointer px-4 py-3 text-sm font-medium text-white/70 hover:text-white select-none">
                Движок симуляции и лента действий
              </summary>
              <div class="px-2 pb-2">
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
            </details>
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
import FocusGroupPanel from '../components/FocusGroupPanel.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import {
  ArrowLeft as ArrowLeftIcon
} from 'lucide-vue-next'
import { getProject, getGraphData } from '../api/graph'
import {
  getSimulation, getSimulationConfig, stopSimulation, closeSimulationEnv, getEnvStatus,
  getSimulationProfiles, interviewAgents, saveCustdevAnswers
} from '../api/simulation'

const route = useRoute()
const router = useRouter()

const props = defineProps({
  simulationId: String
})

// Layout State
const graphCollapsed = ref(false)
const currentStatus = ref('processing')

// Data State
const currentSimulationId = ref(route.params.simulationId)
const maxRounds = ref(route.query.maxRounds ? parseInt(route.query.maxRounds) : null)
const minutesPerRound = ref(30)
const projectData = ref(null)
const graphData = ref(null)
const graphLoading = ref(false)
const systemLogs = ref([])

// --- Фокус-группа ---
const profiles = ref([])
const interviewQuestions = ref([])
const interviews = ref([])
const selectedAgent = ref(null)
const chatHistory = ref([])
const chatSending = ref(false)
const interviewRunning = ref(false)
const interviewDone = ref(false)

// «Температура» персоны из её ответов (позитив/готовность → hot, скепсис → cold).
const POS = ['готов плат', 'куплю', 'подпиш', 'очень нужно', 'давно ищу', 'сразу возьм', 'удобно', 'сэконом', 'интересно', 'это боль', 'не хватает', 'жду такое']
const NEG = ['не нужно', 'не буду', 'не интересно', 'дорого', 'сомнева', 'вряд ли', 'не вижу смысл', 'не критич', 'и так норм', 'не плач']
const warmthMap = computed(() => {
  const byAgent = {}
  interviews.value.forEach((i) => { (byAgent[i.agent_name] || (byAgent[i.agent_name] = [])).push((i.response || '').toLowerCase()) })
  const map = {}
  for (const [name, arr] of Object.entries(byAgent)) {
    const t = arr.join(' ')
    const pos = POS.filter((k) => t.includes(k)).length
    const neg = NEG.filter((k) => t.includes(k)).length
    map[name] = neg > pos ? 'cold' : (pos >= 2 ? 'hot' : 'warm')
  }
  return map
})

// Стандартный список CustDev-вопросов (Mom Test) — фиксированный, без итераций.
const CUSTDEV_QUESTIONS = [
  'Как вы решаете эту задачу сейчас?',
  'Когда вы в последний раз сталкивались с этой проблемой?',
  'Что вы уже пробовали и что не устроило?',
  'Сколько времени и денег это стоит вам сейчас?',
  'Насколько это для вас серьёзная боль и почему?',
  'Готовы ли вы платить за решение и сколько в месяц?',
]

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

// --- Профили персон ---
const loadProfiles = async () => {
  try {
    const res = await getSimulationProfiles(currentSimulationId.value)
    if (res.success && Array.isArray(res.data)) profiles.value = res.data
    else if (res.success && Array.isArray(res.data?.profiles)) profiles.value = res.data.profiles
  } catch (e) {
    addLog(`Профили не загрузились: ${e.message}`)
  }
}

// Парсит ответ batch-интервью { reddit_<idx>: {response} } в записи аккордеона.
const pushInterviewResults = (results, question) => {
  Object.entries(results || {}).forEach(([k, v]) => {
    const idx = parseInt(String(k).split('_').pop())
    const p = profiles.value[idx]
    interviews.value.push({
      agent_name: p?.username || p?.name || `Агент ${idx}`,
      agent_role: p?.profession || '',
      agent_bio: p?.persona || p?.bio || '',
      question,
      response: v?.response || v?.answer || (typeof v === 'string' ? v : ''),
      key_quotes: v?.key_quotes || [],
    })
  })
}

// Прогон стандартного CustDev-интервью: по одному вопросу за раз (аккордеон наполняется вживую).
const runInterview = async () => {
  if (interviewRunning.value || profiles.value.length === 0) return
  try {
    const env = await getEnvStatus({ simulation_id: currentSimulationId.value })
    if (!env.success || !env.data?.env_alive) {
      interviewDone.value = false
      addLog('Интервью недоступно: среда симуляции уже закрыта. Запустите цикл заново.')
      currentStatus.value = 'error'
      return
    }
  } catch (e) {
    addLog(`Не удалось проверить среду интервью: ${e.message}`)
    return
  }
  interviewRunning.value = true
  interviewDone.value = false
  interviews.value = []
  interviewQuestions.value = [...CUSTDEV_QUESTIONS]
  const agentIdxs = profiles.value.map((_, i) => i)
  try {
    for (const q of CUSTDEV_QUESTIONS) {
      try {
        const res = await interviewAgents({
          simulation_id: currentSimulationId.value,
          platform: 'reddit', // одна платформа = индексы совпадают с профилями и нет дублей
          interviews: agentIdxs.map((i) => ({ agent_id: i, prompt: q })),
        })
        if (res.success) pushInterviewResults(res.data?.results || res.data, q)
      } catch (e) {
        addLog(`Вопрос пропущен: ${e.message}`)
        // A closed environment cannot recover on the next question.
        if (/not running|closed|не запущ/i.test(e?.message || '')) break
      }
    }
    addLog('CustDev-интервью завершено.')
    interviewDone.value = true
    // Сохраняем ответы на бэк — для финального отчёта «Сигналы × Симуляция».
    try {
      await saveCustdevAnswers(currentSimulationId.value, interviews.value)
      addLog('Ответы фокус-группы сохранены для отчёта.')
    } catch (e) {
      addLog(`Не удалось сохранить ответы: ${e.message}`)
    }
  } finally {
    interviewRunning.value = false
  }
}

const onSelectAgent = (p) => {
  selectedAgent.value = p
  chatHistory.value = []
}

// Личный 1-на-1 чат с выбранным агентом (только после интервью; агент помнит свои ответы).
const onSendToAgent = async (text) => {
  if (!selectedAgent.value || chatSending.value || !interviewDone.value) return
  const idx = profiles.value.indexOf(selectedAgent.value)
  const name = selectedAgent.value.username || selectedAgent.value.name
  chatHistory.value.push({ role: 'user', content: text })
  chatSending.value = true
  // Контекст: реплики этого агента из интервью — чтобы он не противоречил себе.
  const prior = interviews.value
    .filter((i) => i.agent_name === name)
    .map((i) => `Вопрос: ${i.question}\nТвой ответ: ${i.response}`)
    .join('\n\n')
  const prompt = (prior
    ? `Ранее в CustDev-интервью ты отвечал так:\n${prior}\n\nОтвечай в том же характере и не противоречь своим ответам.\n\nВопрос собеседника: ${text}`
    : text)
  try {
    const res = await interviewAgents({
      simulation_id: currentSimulationId.value,
      platform: 'reddit',
      interviews: [{ agent_id: idx, prompt }],
    })
    if (res.success) {
      const results = res.data?.results || res.data || {}
      const agentRes = results[`reddit_${idx}`] || results[`twitter_${idx}`] || Object.values(results)[0]
      const content = agentRes?.response || agentRes?.answer || (typeof agentRes === 'string' ? agentRes : '…')
      chatHistory.value.push({ role: 'assistant', content })
    }
  } catch (e) {
    chatHistory.value.push({ role: 'assistant', content: `Связь прервалась: ${e.message}` })
  } finally {
    chatSending.value = false
  }
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
  loadProfiles()
})

onUnmounted(stopGraphRefresh)
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.05); border-radius: 10px; }

@media (max-width: 640px) {
  .workflow-header {
    height: auto !important;
    min-height: 3.5rem;
    flex-wrap: wrap;
    gap: 0.35rem;
    padding: 0.5rem 0.75rem;
  }
  .workflow-header-left { flex: 1 1 auto; min-width: 0; }
  .workflow-header-left > div:last-child span:last-child {
    display: block;
    max-width: 40vw;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .workflow-header-mode {
    order: 3;
    flex: 1 0 100%;
    width: 100%;
    text-align: center;
  }
  .workflow-header-right { flex: 0 0 auto; }
  .workflow-header-right span:first-child { display: none; }
}
</style>
