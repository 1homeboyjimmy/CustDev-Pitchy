<template>
  <div class="space-y-8 animate-in fade-in slide-in-from-right-4 duration-700">
    <!-- Top Control Bar (Matrix Pulse) -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <GlassCard 
        v-for="plt in ['twitter', 'reddit']" 
        :key="plt"
        :class="[
          'relative overflow-hidden group transition-all duration-500',
          runStatus[`${plt}_running`] ? (plt === 'twitter' ? 'border-white/40 bg-white/5' : 'border-white/40 bg-white/5') : 'border-white/5 opacity-60'
        ]"
      >
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center gap-3">
            <div :class="['w-8 h-8 rounded-xl flex items-center justify-center', plt === 'twitter' ? 'bg-white/20 text-white/80' : 'bg-white/20 text-white']">
              <component :is="plt === 'twitter' ? GlobeIcon : UsersIcon" class="w-4 h-4" />
            </div>
            <div class="space-y-0.5">
              <div class="text-[10px] font-bold text-white/30 uppercase tracking-widest">{{ plt === 'twitter' ? 'Квадратная матрица' : 'Матрица сообщества' }}</div>
              <div class="text-sm font-bold text-white">{{ plt === 'twitter' ? 'Инфо-площадь' : 'Тематический кластер' }}</div>
            </div>
          </div>
          <StatusBadge :type="runStatus[`${plt}_completed`] ? 'success' : (runStatus[`${plt}_running`] ? (plt === 'twitter' ? 'cyan' : 'primary') : 'default')" :dot="runStatus[`${plt}_running`]">
            {{ runStatus[`${plt}_completed`] ? 'Стабилизировано' : (runStatus[`${plt}_running`] ? 'Активно' : 'Ожидание') }}
          </StatusBadge>
        </div>

        <div class="grid grid-cols-3 gap-2">
          <div v-for="(v, k) in { 'Раунд': (runStatus[`${plt}_current_round`] || 0) + '/' + (runStatus.total_rounds || maxRounds || '-'), 'События': runStatus[`${plt}_actions_count`] || 0, 'Поток': (plt === 'twitter' ? twitterElapsedTime : redditElapsedTime) }" :key="k" class="p-2 rounded-xl bg-white/5 border border-white/5 text-center space-y-0.5">
            <div class="text-[8px] font-bold text-white/20 uppercase tracking-tighter">{{ k }}</div>
            <div class="text-xs font-bold text-white font-mono">{{ v }}</div>
          </div>
        </div>

        <!-- Glow effect on active -->
        <div v-if="runStatus[`${plt}_running`]" :class="['absolute -inset-1 opacity-20 blur-2xl -z-10', plt === 'twitter' ? 'bg-white/8' : 'bg-white/10']"></div>
      </GlassCard>
    </div>

    <!-- Timeline Action Overlay -->
    <div class="relative space-y-6 min-h-[400px]">
      <!-- Final Action Button (Visible when completed) -->
      <div v-if="phase === 2 || runStatus.twitter_completed" class="sticky top-0 z-30 pb-4 flex justify-center animate-in slide-in-from-top-4 duration-500">
        <PitchyButton variant="primary" :loading="isGeneratingReport" @click="handleNextStep" class="shadow-[0_0_20px_rgba(255,255,255,0.15)] px-8 py-4">
          Синтезировать аналитический отчет
          <template #icon><ZapIcon class="w-4 h-4 fill-current" /></template>
        </PitchyButton>
      </div>

      <!-- Timeline Feed -->
      <div class="relative pl-8 md:pl-0">
        <!-- Vertical Axis -->
        <div class="absolute left-4 md:left-1/2 top-4 bottom-4 w-px bg-gradient-to-b from-white via-white/70 to-transparent opacity-20 hidden md:block"></div>
        
        <div class="space-y-6 relative">
          <TransitionGroup name="action-fade">
            <div v-for="(action, idx) in chronologicalActions" :key="action._uniqueId" 
              :class="['relative flex flex-col md:flex-row items-start md:items-center gap-6 group', idx % 2 === 0 ? 'md:flex-row' : 'md:flex-row-reverse']">
              
              <!-- Center Marker -->
              <div class="absolute left-4 md:left-1/2 -translate-x-1/2 w-3 h-3 rounded-full border border-white/20 bg-[#0A0A0F] z-10 hidden md:block group-hover:border-white/20 transition-colors">
                <div v-if="idx === chronologicalActions.length - 1" class="absolute inset-0 rounded-full bg-white/8 animate-ping opacity-50"></div>
              </div>

              <!-- Content Card -->
              <div :class="['w-full md:w-[calc(50%-2rem)]', action.platform === 'twitter' ? 'md:text-left' : 'md:text-left']">
                <GlassCard class="p-4 hover:border-white/20 transition-all duration-300">
                  <div class="flex items-start justify-between mb-3">
                    <div class="flex items-center gap-2">
                      <div class="w-7 h-7 rounded-lg bg-white/5 flex items-center justify-center text-white/40 font-bold text-[10px] border border-white/10 uppercase">
                        {{ action.agent_name?.charAt(0) || 'A' }}
                      </div>
                      <div class="space-y-0.5">
                        <div class="text-[11px] font-bold text-white group-hover:text-white/80 transition-colors">{{ action.agent_name }}</div>
                        <div class="flex items-center gap-1.5 font-mono text-[8px] text-white/30 uppercase tracking-tighter">
                          <span :class="action.platform === 'twitter' ? 'text-white/80' : 'text-white'">{{ action.platform }}</span>
                          <span>•</span>
                          <span>Р{{ action.round_num }}</span>
                          <span>•</span>
                          <span>{{ formatActionTime(action.timestamp) }}</span>
                        </div>
                      </div>
                    </div>
                    <StatusBadge :type="action.platform === 'twitter' ? 'cyan' : 'primary'" size="sm" class="opacity-80">
                      {{ getActionTypeLabel(action.action_type) }}
                    </StatusBadge>
                  </div>

                  <!-- Dynamic Content Blocks -->
                  <div class="space-y-3">
                    <!-- Text Content -->
                    <p v-if="action.action_args?.content" class="text-[12px] text-white/70 leading-relaxed font-sans">{{ action.action_args.content }}</p>
                    <p v-if="action.action_type === 'QUOTE_POST' && action.action_args?.quote_content" class="text-[12px] text-white/70 leading-relaxed">{{ action.action_args.quote_content }}</p>

                    <!-- Quoted Block -->
                    <div v-if="action.action_args?.original_content" class="p-3 rounded-xl bg-white/[0.03] border border-white/5 space-y-2 relative overflow-hidden">
                       <div class="flex items-center gap-2 text-[9px] font-bold text-white/20 uppercase">
                         <QuoteIcon class="w-2.5 h-2.5" />
                         <span>@{{ action.action_args.original_author_name }}</span>
                       </div>
                       <p class="text-[10px] text-white/40 italic line-clamp-3">"{{ action.action_args.original_content }}"</p>
                    </div>

                    <!-- Actions Info (Likes, Votes, etc) -->
                    <div v-if="['LIKE_POST', 'UPVOTE_POST', 'DOWNVOTE_POST', 'REPOST'].includes(action.action_type)" class="flex items-center gap-2 p-2 rounded-lg bg-white/5 border border-white/10">
                      <HeartIcon v-if="action.action_type === 'LIKE_POST'" class="w-3 h-3 text-white/80 fill-current" />
                      <ArrowUpIcon v-if="action.action_type === 'UPVOTE_POST'" class="w-3 h-3 text-white/80" />
                      <ArrowDownIcon v-if="action.action_type === 'DOWNVOTE_POST'" class="w-3 h-3 text-white" />
                      <RepeatIcon v-if="action.action_type === 'REPOST'" class="w-3 h-3 text-white/80" />
                      <span class="text-[9px] font-bold text-white/50 uppercase">{{ getActionTypeLabel(action.action_type) }} НА СЛЕДЕ #{{ action.action_args?.post_id || 'ID_NULL' }}</span>
                    </div>
                  </div>
                </GlassCard>
              </div>
            </div>
          </TransitionGroup>
        </div>
      </div>

      <!-- Empty State / Searching -->
      <div v-if="allActions.length === 0" class="flex flex-col items-center justify-center py-20 space-y-4">
        <div class="relative">
          <div class="w-16 h-16 rounded-full border-2 border-white/20 animate-spin border-t-white/80"></div>
          <div class="absolute inset-4 rounded-full border-2 border-white/20 animate-spin-slow border-t-white"></div>
        </div>
        <div class="text-[10px] font-bold text-white/30 uppercase tracking-[0.3em] animate-pulse whitespace-nowrap">Синхронизация матрицы событий...</div>
      </div>
    </div>

    <!-- System Logs Terminal -->
    <div class="rounded-2xl bg-[#0A0A0F]/90 border border-white/10 overflow-hidden shadow-2xl">
      <div class="h-10 bg-white/[0.02] border-b border-white/5 px-4 flex items-center justify-between text-[9px] font-mono font-bold tracking-[0.2em] text-white/30">
        <div class="flex items-center gap-2">
          <ActivityIcon class="w-3 h-3 text-white/80" />
          МОНИТОР_ОБОРУДОВАНИЯ_СИМУЛЯЦИИ
        </div>
        <div class="flex items-center gap-4">
          <div v-if="runStatus.runner_status === 'running'" class="flex items-center">
            <button 
              @click="handleStopSimulation" 
              class="flex items-center gap-1.5 px-2 py-1 rounded bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500/20 transition-all group"
            >
              <XIcon class="w-3 h-3 group-hover:scale-110 transition-transform" />
              ОСТАНОВИТЬ АНАЛИЗ
            </button>
          </div>
          <div>{{ simulationId || 'БЕЗ_UUID' }}</div>
        </div>
      </div>
      <div class="h-40 overflow-y-auto p-4 space-y-1.5 custom-scrollbar font-mono text-[10px]" ref="logContent">
        <div v-for="(log, idx) in systemLogs" :key="idx" class="flex gap-4 group/log">
          <span class="text-white/20 group-hover/log:text-white/40 transition-colors shrink-0">{{ log.time }}</span>
          <span class="text-white/60 group-hover/log:text-white/80 transition-colors break-all">
            <span class="text-white/80 mr-1">>></span> {{ log.msg }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { startSimulation, stopSimulation, getRunStatus, getRunStatusDetail } from '../api/simulation'
import { generateReport } from '../api/report'
import GlassCard from './ui/GlassCard.vue'
import StatusBadge from './ui/StatusBadge.vue'
import PitchyButton from './ui/PitchyButton.vue'
import { 
  Globe as GlobeIcon, 
  Users as UsersIcon, 
  Zap as ZapIcon, 
  Activity as ActivityIcon,
  Heart as HeartIcon,
  Repeat as RepeatIcon,
  Quote as QuoteIcon,
  ArrowUp as ArrowUpIcon,
  ArrowDown as ArrowDownIcon,
  X as XIcon
} from 'lucide-vue-next'

const props = defineProps({
  simulationId: String,
  maxRounds: Number,
  minutesPerRound: { type: Number, default: 30 },
  projectData: Object,
  graphData: Object,
  systemLogs: Array
})

const emit = defineEmits(['go-back', 'next-step', 'add-log', 'update-status'])
const router = useRouter()

const isGeneratingReport = ref(false)
const phase = ref(0) 
const runStatus = ref({})
const allActions = ref([]) 
const actionIds = ref(new Set())
const logContent = ref(null)

const chronologicalActions = computed(() => [...allActions.value].reverse().slice(0, 50))

const formatElapsedTime = r => {
  if (!r) return '0ч 0м'; const m = r * props.minutesPerRound
  return `${Math.floor(m / 60)}ч ${m % 60}м`
}
const twitterElapsedTime = computed(() => formatElapsedTime(runStatus.value.twitter_current_round))
const redditElapsedTime = computed(() => formatElapsedTime(runStatus.value.reddit_current_round))

const addLog = (msg) => emit('add-log', msg)

const doStartSimulation = async () => {
  if (!props.simulationId) return
  addLog('Запуск последовательности симуляции мультивселенной...')
  emit('update-status', 'processing')
  try {
    const params = { simulation_id: props.simulationId, platform: 'parallel', force: true, enable_graph_memory_update: true, request_id: crypto.randomUUID() }
    if (props.maxRounds) params.max_rounds = props.maxRounds
    const res = await startSimulation(params)
    if (res.success) {
      addLog(`✓ Движок манифестирован с PID: ${res.data.process_pid}`)
      phase.value = 1; runStatus.value = res.data
      startPolling()
    }
  } catch (err) {
    const backendMsg = err?.response?.data?.error || err?.response?.data?.message
    const status = err?.response?.status
    const reason = backendMsg || err.message || 'неизвестная ошибка'
    addLog(`✗ Не удалось запустить симуляцию${status ? ` (HTTP ${status})` : ''}: ${reason}`)
    if (status === 400 && /not ready|prepare/i.test(reason)) {
      addLog('⚠ Среда не готова. Вернитесь на Шаг 2 и завершите подготовку агентов.')
    }
    emit('update-status', 'error')
  }
}

let statusTimer, detailTimer
let lastActionTimestamp = ''
let detailRequestActive = false
const startPolling = () => {
  statusTimer = setInterval(fetchRunStatus, 5000)
  detailTimer = setInterval(fetchRunStatusDetail, 8000)
}
const stopPolling = () => { clearInterval(statusTimer); clearInterval(detailTimer) }

const fetchRunStatus = async () => {
  try {
    const res = await getRunStatus(props.simulationId)
    if (res.success) {
      runStatus.value = res.data
      if (res.data.runner_status === 'completed' || res.data.twitter_completed) {
        addLog('✓ Мультивселенная стабилизирована. Циклы завершены.')
        phase.value = 2; stopPolling(); emit('update-status', 'completed')
      }
    }
  } catch (e) {}
}

const fetchRunStatusDetail = async () => {
  if (detailRequestActive) return
  detailRequestActive = true
  try {
    const res = await getRunStatusDetail(props.simulationId, { since: lastActionTimestamp })
    if (res.success && res.data.all_actions) {
      res.data.all_actions.forEach(action => {
        const id = action.id || `${action.timestamp}-${action.agent_id}`
        if (!actionIds.value.has(id)) {
          actionIds.value.add(id)
          allActions.value.push({ ...action, _uniqueId: id })
        }
      })
      const timestamps = res.data.all_actions.map(action => action.timestamp).filter(Boolean)
      if (timestamps.length) {
        timestamps.sort()
        lastActionTimestamp = timestamps[timestamps.length - 1]
      }
    }
  } catch (e) {}
  finally { detailRequestActive = false }
}

const getActionTypeLabel = t => ({
  'CREATE_POST': 'ПОСТ', 'REPOST': 'РЕПОСТ', 'LIKE_POST': 'ЛАЙК',
  'CREATE_COMMENT': 'КОММЕНТАРИЙ', 'DO_NOTHING': 'ОЖИДАНИЕ', 'QUOTE_POST': 'ЦИТАТА',
  'UPVOTE_POST': 'АПВОУТ', 'DOWNVOTE_POST': 'ДАУНВОУТ'
}[t] || t)

const formatActionTime = ts => ts ? new Date(ts).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' }) : ''

const handleNextStep = async () => {
  isGeneratingReport.value = true
  addLog('Запуск аналитического синтеза...')
  try {
    const res = await generateReport({ simulation_id: props.simulationId })
    if (res.success) router.push({ name: 'Report', params: { reportId: res.data.report_id } })
  } catch (e) { isGeneratingReport.value = false }
}

const handleStopSimulation = async () => {
  if (!props.simulationId) return
  if (!confirm('Вы уверены, что хотите остановить анализ?')) return
  
  addLog('Запрос на принудительную остановку анализа...')
  try {
    const res = await stopSimulation({ simulation_id: props.simulationId })
    if (res.success) {
      addLog('✓ Анализ остановлен пользователем.')
      stopPolling()
      emit('update-status', 'stopped')
      // Refresh status to show ended state
      await fetchRunStatus()
    } else {
      addLog(`✗ Не удалось остановить: ${res.message || 'Ошибка сервера'}`)
    }
  } catch (err) {
    addLog(`✗ Ошибка при остановке: ${err.message}`)
  }
}

watch(() => props.systemLogs?.length, () => nextTick(() => { if (logContent.value) logContent.value.scrollTop = logContent.value.scrollHeight }))
onMounted(() => { if (props.simulationId) doStartSimulation() })
onUnmounted(stopPolling)
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
.action-fade-enter-active { transition: all 0.6s ease-out; }
.action-fade-enter-from { opacity: 0; transform: translateY(20px); filter: blur(10px); }
.animate-spin-slow { animation: spin 10s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
