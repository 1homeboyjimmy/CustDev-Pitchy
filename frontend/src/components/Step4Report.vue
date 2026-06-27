<template>
  <div class="space-y-12 animate-in fade-in slide-in-from-right-4 duration-700 pb-20">
    <!-- Main Analytical Dashboard -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
      <!-- LEFT: The Report Document -->
      <div class="space-y-8">
        <div v-if="reportOutline" class="space-y-8">
          <!-- Report Header -->
          <div class="space-y-4">
            <div class="flex items-center gap-3">
              <span class="px-2 py-0.5 rounded bg-white/20 border border-white/30 text-[9px] font-bold text-white/90 uppercase tracking-widest">Прогностический отчет</span>
              <span class="text-[9px] font-mono text-white/20 uppercase tracking-widest">ID: {{ reportId?.slice(0, 12) }}</span>
            </div>
            <h1 class="text-4xl font-bold text-white tracking-tight leading-tight">{{ reportOutline.title }}</h1>
            <p class="text-sm text-white/50 leading-relaxed italic border-l-2 border-white/25 pl-4">{{ reportOutline.summary }}</p>
          </div>

          <!-- Section Iteration -->
          <div class="space-y-4">
            <div 
              v-for="(section, idx) in reportOutline.sections" 
              :key="idx"
              class="group"
            >
              <GlassCard 
                :class="[
                  'transition-all duration-500 overflow-hidden',
                  currentSectionIndex === idx + 1 ? 'border-white/40 bg-white/5' : 'border-white/5'
                ]"
              >
                <div 
                  class="flex items-center justify-between cursor-pointer py-2" 
                  @click="toggleSectionCollapse(idx)"
                >
                  <div class="flex items-center gap-4">
                    <span class="text-2xl font-black text-white/5 font-mono group-hover:text-white/20 transition-colors">{{ String(idx + 1).padStart(2, '0') }}</span>
                    <h3 class="text-lg font-bold text-white group-hover:text-white/90 transition-colors">{{ section.title }}</h3>
                  </div>
                  <div class="flex items-center gap-4">
                    <StatusBadge :type="generatedSections[idx + 1] ? 'success' : (currentSectionIndex === idx + 1 ? 'primary' : 'default')" :dot="currentSectionIndex === idx + 1">
                      {{ generatedSections[idx + 1] ? 'Синтезировано' : (currentSectionIndex === idx + 1 ? 'Генерация' : 'В очереди') }}
                    </StatusBadge>
                    <ChevronDownIcon 
                      v-if="generatedSections[idx + 1]"
                      :class="['w-4 h-4 text-white/20 transition-transform duration-300', collapsedSections.has(idx) ? '-rotate-90' : '']" 
                    />
                  </div>
                </div>

                <div v-show="!collapsedSections.has(idx)" class="mt-6 animate-in slide-in-from-top-2 duration-500">
                  <div v-if="generatedSections[idx + 1]" class="prose prose-invert prose-sm max-w-none text-white/70 leading-relaxed custom-markdown" v-html="renderMarkdown(generatedSections[idx + 1])"></div>
                  <div v-else-if="currentSectionIndex === idx + 1" class="py-8 flex flex-col items-center justify-center space-y-4">
                    <div class="w-12 h-1 border-2 border-white/20 rounded-full overflow-hidden relative">
                      <div class="absolute inset-0 bg-white/10 animate-progress-ind"></div>
                    </div>
                    <span class="text-[10px] font-bold text-white/90 uppercase tracking-[0.3em] animate-pulse whitespace-nowrap">Анализ потоков...</span>
                  </div>
                </div>
              </GlassCard>
            </div>
          </div>
        </div>

        <!-- Waiting for First Section -->
        <div v-if="!reportOutline" class="py-40 flex flex-col items-center justify-center space-y-6">
           <div class="relative">
             <div class="w-20 h-20 rounded-full border-2 border-white/10 animate-spin border-t-white"></div>
             <div class="absolute inset-4 rounded-full border-2 border-white/10 animate-spin-slow border-t-white/80"></div>
           </div>
           <div class="text-xs font-bold text-white/20 uppercase tracking-[0.4em] animate-pulse whitespace-nowrap">Установка аналитического ядра...</div>
        </div>
      </div>

      <!-- RIGHT: Agent Workflow Timeline -->
      <div class="space-y-6 sticky top-8">
        <GlassCard class="bg-[#0A0A0F]/50 border-white/10 backdrop-blur-xl">
           <div class="flex items-center justify-between mb-8 border-b border-white/5 pb-4">
             <div class="flex items-center gap-3">
               <ActivityIcon class="w-4 h-4 text-white/80" />
               <span class="text-sm font-bold text-white uppercase tracking-widest">Метрики процесса</span>
             </div>
             <StatusBadge :type="isComplete ? 'success' : 'primary'" :dot="!isComplete">
               {{ isComplete ? 'Матрица стабильна' : 'Активный синтез' }}
             </StatusBadge>
           </div>

           <div class="grid grid-cols-3 gap-6 mb-8">
             <div v-for="(v, l) in { 'Разделы': completedSections + '/' + totalSections, 'Прошло': formatElapsedTime, 'Инструменты': totalToolCalls }" :key="l" class="text-center space-y-1">
                <div class="text-lg font-bold text-white font-mono tracking-tight">{{ v }}</div>
                <div class="text-[8px] font-bold text-white/20 uppercase tracking-widest">{{ l }}</div>
             </div>
           </div>

           <!-- Timeline Track -->
           <div class="space-y-6 relative max-h-[600px] overflow-y-auto custom-scrollbar pr-4">
             <div class="absolute left-3.5 top-2 bottom-2 w-px bg-gradient-to-b from-white/70 via-white/10 to-transparent"></div>
             
             <TransitionGroup name="log-fade">
               <div v-for="(log, idx) in displayLogs" :key="log.timestamp + '-' + idx" class="relative pl-10 group/log">
                  <div :class="['absolute left-2.5 top-1.5 w-2 h-2 rounded-full border-2 border-[#0A0A0F] z-10 transition-all shadow-glow', getLogColorClass(log.action)]"></div>
                  
                  <div class="space-y-2">
                    <div class="flex items-center justify-between">
                      <span class="text-[9px] font-bold text-white/60 uppercase tracking-widest">{{ getActionLabel(log.action) }}</span>
                      <span class="text-[8px] font-mono text-white/20">{{ formatTime(log.timestamp) }}</span>
                    </div>

                    <!-- Dynamic Log Content -->
                    <div 
                      :class="['p-3 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.04] transition-all cursor-pointer overflow-hidden', expandedLogs.has(log.timestamp) ? '' : 'max-h-20']"
                      @click="toggleLogExpand(log)"
                    >
                      <!-- Tool Call Display -->
                      <div v-if="log.action === 'tool_call'" class="flex items-center gap-2">
                        <component :is="getIconForTool(log.details?.tool_name)" class="w-3 h-3 text-white/80" />
                        <span class="text-[10px] font-bold text-white/85">{{ getToolDisplayName(log.details?.tool_name) }}</span>
                      </div>

                      <!-- Tool Result (Minimalist Preview) -->
                      <div v-if="log.action === 'tool_result'" class="space-y-2">
                        <div class="flex items-center justify-between text-[8px] font-bold text-white/40 uppercase">
                          <span>Поток данных получен</span>
                          <span>{{ formatResultSize(log.details?.result_length) }}</span>
                        </div>
                        <p class="text-[10px] text-white/30 line-clamp-3 leading-relaxed font-mono">{{ truncateText(log.details?.result, 200) }}</p>
                      </div>

                      <!-- Section Tags -->
                      <div v-if="log.action === 'section_start' || log.action === 'section_complete'" class="flex items-center gap-2">
                        <div class="text-[10px] font-black text-white px-1.5 py-0.5 rounded bg-white/10 border border-white/20">#{{ log.section_index }}</div>
                        <span class="text-[10px] font-bold text-white">{{ log.section_title }}</span>
                      </div>

                      <!-- LLM Iteration -->
                      <div v-if="log.action === 'llm_response'" class="space-y-1">
                         <div class="text-[9px] font-bold text-white/40 uppercase">Цикл когнитивного синтеза {{ log.details?.iteration }}</div>
                         <div v-if="log.details?.has_final_answer" class="text-[9px] text-white/80 font-bold italic">>> Последовательность завершена</div>
                      </div>
                    </div>
                    
                    <div v-if="log.elapsed_seconds" class="text-[8px] font-mono text-white/20 flex justify-end">+{{ log.elapsed_seconds.toFixed(1) }}s цикл</div>
                  </div>
               </div>
             </TransitionGroup>
           </div>

           <!-- Deep Interaction Button -->
           <div v-if="isComplete" class="mt-8 pt-6 border-t border-white/5 animate-in slide-in-from-bottom-4 duration-700">
              <PitchyButton variant="secondary" class="w-full text-xs py-4 group" @click="goToInteraction">
                Начать глубокий структурный диалог
                <template #icon><ArrowRightIcon class="w-4 h-4 group-hover:translate-x-1 transition-transform" /></template>
              </PitchyButton>
              <p class="text-[9px] text-white/20 text-center mt-3 uppercase tracking-widest">Запросить граф через манифестацию естественного языка</p>
           </div>
        </GlassCard>
      </div>
    </div>

    <!-- System Console Outlet -->
    <div class="rounded-2xl bg-[#0A0A0F]/90 border border-white/10 overflow-hidden shadow-2xl">
      <div class="h-10 bg-white/[0.02] border-b border-white/5 px-4 flex items-center justify-between text-[9px] font-mono font-bold tracking-[0.2em] text-white/30">
        <div class="flex items-center gap-2">
          <TerminalIcon class="w-3 h-3 text-white" />
          ГЕНЕРАТОР_ОТЧЕТОВ_СИМУЛЯЦИИ_V4
        </div>
        <div>{{ reportId || 'БЕЗ_СЕССИИ' }}</div>
      </div>
      <div class="h-40 overflow-y-auto p-4 space-y-1.5 custom-scrollbar font-mono text-[10px]" ref="logContent">
        <div v-for="(log, idx) in consoleLogs" :key="idx" class="flex gap-4 group/log">
          <span class="text-white/20 group-hover/log:text-white/40 transition-colors shrink-0">[{{ String(idx).padStart(3, '0') }}]</span>
          <span :class="['text-white/60 group-hover/log:text-white/80 transition-colors break-all', getLogLevelClass(log)]">
            <span class="text-white mr-1">>></span> {{ log }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { getAgentLog, getConsoleLog } from '../api/report'
import GlassCard from './ui/GlassCard.vue'
import StatusBadge from './ui/StatusBadge.vue'
import PitchyButton from './ui/PitchyButton.vue'
import { 
  ChevronDown as ChevronDownIcon, 
  ArrowRight as ArrowRightIcon,
  Activity as ActivityIcon,
  Terminal as TerminalIcon,
  Zap as ZapIcon,
  Globe as GlobeIcon, 
  Users as UsersIcon,
  Lightbulb as LightbulbIcon,
  Database as DatabaseIcon,
  PieChart as ChartIcon,
  Search as SearchIcon
} from 'lucide-vue-next'
import { marked } from 'marked'

const router = useRouter()
const props = defineProps({
  reportId: String,
  simulationId: String,
  projectData: Object,
  systemLogs: Array
})
const emit = defineEmits(['add-log', 'update-status'])

// State
const agentLogs = ref([])
const consoleLogs = ref([])
const agentLogLine = ref(0)
const consoleLogLine = ref(0)
const reportOutline = ref(null)
const currentSectionIndex = ref(null)
const generatedSections = ref({})
const expandedLogs = ref(new Set())
const collapsedSections = ref(new Set())
const isComplete = ref(false)
const startTime = ref(null)
const logContent = ref(null)

// Computed
const totalSections = computed(() => reportOutline.value?.sections?.length || 0)
const completedSections = computed(() => Object.keys(generatedSections.value).length)
const displayLogs = computed(() => [...agentLogs.value].reverse().slice(0, 40))
const totalToolCalls = computed(() => agentLogs.value.filter(l => l.action === 'tool_call').length)

const formatElapsedTime = computed(() => {
  if (!startTime.value) return '00:00'
  const elapsed = Math.floor((Date.now() - startTime.value) / 1000)
  return `${Math.floor(elapsed / 60)}м ${elapsed % 60}с`
})

// Methods
const toggleLogExpand = log => {
  const s = new Set(expandedLogs.value)
  if (s.has(log.timestamp)) s.delete(log.timestamp)
  else s.add(log.timestamp)
  expandedLogs.value = s
}
const toggleSectionCollapse = idx => {
  if (!generatedSections.value[idx + 1]) return
  const s = new Set(collapsedSections.value)
  if (s.has(idx)) s.delete(idx)
  else s.add(idx)
  collapsedSections.value = s
}

const renderMarkdown = content => content ? marked(content) : ''
const getLogLevelClass = log => log.includes('ERR') || log.includes('failed') ? 'text-red-400' : (log.includes('WARN') ? 'text-orange-400' : 'text-white/60')
const getActionLabel = a => ({ 'report_start': 'ПОДГОТОВКА', 'planning_start': 'ПЛАНИРОВАНИЕ', 'planning_complete': 'ПЛАН ГОТОВ', 'section_start': 'НОВЫЙ ЭТАП', 'section_content': 'АНАЛИЗ', 'section_complete': 'ОБРАБОТКА', 'tool_call': 'ДЕЙСТВИЕ', 'tool_result': 'ДАННЫЕ', 'llm_response': 'СИНТЕЗ ЗНАНИЙ', 'report_complete': 'ЗАВЕРШЕНО' }[a] || a)
const getLogColorClass = a => ({ 'report_start': 'bg-white', 'planning_start': 'bg-white/10', 'planning_complete': 'bg-green-500', 'section_start': 'bg-white/10', 'section_complete': 'bg-green-500', 'tool_call': 'bg-white/8', 'tool_result': 'bg-white/8', 'llm_response': 'bg-white', 'report_complete': 'bg-green-500' }[a] || 'bg-white/20')
const formatTime = ts => ts ? new Date(ts).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) : ''
const formatResultSize = s => s > 1024 ? (s / 1024).toFixed(1) + 'kb' : (s || 0) + 'b'
const truncateText = (t, l) => t && t.length > l ? t.substring(0, l) + '...' : (t || '')

const getIconForTool = name => ({
  'insight_forge': LightbulbIcon,
  'panorama_search': GlobeIcon,
  'interview_agents': UsersIcon,
  'quick_search': SearchIcon,
  'get_graph_statistics': ChartIcon,
  'get_entities_by_type': DatabaseIcon
}[name] || ZapIcon)

const getToolDisplayName = n => ({ 'insight_forge': 'Глубинный инсайт', 'panorama_search': 'Панорамный поиск', 'interview_agents': 'Интервью с агентами', 'quick_search': 'Быстрый поиск', 'get_graph_statistics': 'Статистика графа', 'get_entities_by_type': 'Запрос сущностей' }[n] || n)

// Polling
let pollingTimer = null
const startPolling = () => { poll(); pollingTimer = setInterval(poll, 6000) }
const stopPolling = () => clearInterval(pollingTimer)

const poll = async () => {
  if (!props.reportId || isComplete.value) return
  try {
    const aRes = await getAgentLog(props.reportId, agentLogLine.value)
    if (aRes.success && aRes.data.logs.length > 0) {
      aRes.data.logs.forEach(processLog)
      agentLogLine.value = aRes.data.next_line
    }
    const cRes = await getConsoleLog(props.reportId, consoleLogLine.value)
    if (cRes.success && cRes.data.logs.length > 0) {
      consoleLogs.value.push(...cRes.data.logs)
      consoleLogLine.value = cRes.data.next_line
    }
  } catch (e) {}
}

const processLog = log => {
  agentLogs.value.push(log)
  if (log.action === 'report_start' && !startTime.value) startTime.value = Date.now()
  if (log.action === 'planning_complete' && log.details?.outline) reportOutline.value = log.details.outline
  if (log.action === 'section_start') currentSectionIndex.value = log.section_index
  if (log.action === 'section_content') {
    generatedSections.value[log.section_index] = log.details.content
    collapsedSections.value.add(log.section_index - 2) // Auto-collapse previous
  }
  if (log.action === 'report_complete') {
    isComplete.value = true
    stopPolling()
    emit('update-status', 'completed')
  }
}

const goToInteraction = () => router.push({ name: 'Interaction', params: { reportId: props.reportId } })

watch(() => consoleLogs.value.length, () => nextTick(() => { if (logContent.value) logContent.value.scrollTop = logContent.value.scrollHeight }))
onMounted(() => { if (props.reportId) startPolling() })
onUnmounted(stopPolling)
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
.log-fade-enter-active { transition: all 0.5s ease-out; }
.log-fade-enter-from { opacity: 0; transform: translateX(-10px); }
.animate-progress-ind { animation: progress-ind 2s ease-in-out infinite; }
@keyframes progress-ind { 0% { left: -40%; width: 40%; } 100% { left: 100%; width: 40%; } }
.custom-markdown :deep(h2) { font-size: 1.25rem; font-weight: 700; color: #fff; margin-top: 2rem; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 0.5rem; }
.custom-markdown :deep(h3) { font-size: 1rem; font-weight: 700; color: rgba(255,255,255,0.9); margin-top: 1.5rem; }
.custom-markdown :deep(ul) { list-style: disc; padding-left: 1.5rem; margin: 1rem 0; }
.custom-markdown :deep(li) { margin: 0.5rem 0; }
.custom-markdown :deep(p) { margin: 1rem 0; line-height: 1.7; }
.custom-markdown :deep(strong) { color: #fff; font-weight: 700; }
</style>
