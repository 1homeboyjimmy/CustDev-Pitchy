<template>
  <div class="h-full flex flex-col lg:flex-row gap-8 overflow-hidden animate-in fade-in slide-in-from-right-4 duration-700">
    <!-- LEFT: Persistent Report Context -->
    <div class="w-full lg:w-1/3 flex flex-col space-y-6 overflow-y-auto custom-scrollbar pr-2">
      <div v-if="reportOutline" class="space-y-6">
        <div class="space-y-2">
          <div class="text-[10px] font-bold text-white/90 uppercase tracking-[0.2em] opacity-60">Исходный документ</div>
          <h2 class="text-xl font-bold text-white tracking-tight leading-snug">{{ reportOutline.title }}</h2>
        </div>

        <div class="space-y-4">
          <div 
            v-for="(section, idx) in reportOutline.sections" 
            :key="idx"
            class="group"
          >
            <GlassCard 
              :class="[
                'transition-all duration-500 overflow-hidden text-left p-4',
                currentSectionIndex === idx + 1 ? 'border-white/40 bg-white/5' : 'border-white/5 opacity-80 hover:opacity-100'
              ]"
            >
              <div 
                class="flex items-center justify-between cursor-pointer" 
                @click="toggleSectionCollapse(idx)"
              >
                <div class="flex items-center gap-3">
                  <span class="text-lg font-black text-white/10 font-mono">{{ String(idx + 1).padStart(2, '0') }}</span>
                  <h3 class="text-sm font-bold text-white/80 group-hover:text-white transition-colors">{{ section.title }}</h3>
                </div>
                <ChevronDownIcon 
                  v-if="generatedSections[idx + 1]"
                  :class="['w-3.5 h-3.5 text-white/20 transition-transform duration-300', collapsedSections.has(idx) ? '-rotate-90' : '']" 
                />
              </div>

              <div v-show="!collapsedSections.has(idx)" class="mt-4 animate-in slide-in-from-top-1 duration-300">
                 <div v-if="generatedSections[idx + 1]" class="prose prose-invert prose-xs max-w-none text-white/40 leading-relaxed custom-markdown-small" v-html="renderMarkdown(generatedSections[idx + 1])"></div>
              </div>
            </GlassCard>
          </div>
        </div>
      </div>

      <div v-else class="flex flex-col items-center justify-center py-20 opacity-20">
        <Loader2Icon class="w-8 h-8 animate-spin mb-4" />
        <span class="text-[10px] font-bold uppercase tracking-widest">Ожидание синтеза...</span>
      </div>
    </div>

    <!-- RIGHT: Interaction Matrix -->
    <div class="flex-1 flex flex-col min-w-0 bg-[#0A0A0F]/30 rounded-3xl border border-white/5 overflow-hidden">
      <!-- Matrix Header / Tabs -->
      <div class="h-16 px-6 border-b border-white/5 flex items-center justify-between shrink-0 bg-white/[0.02]">
        <div class="flex items-center gap-2">
          <button 
            @click="selectReportAgentChat"
            :class="['px-4 py-2 rounded-xl text-[10px] font-bold uppercase tracking-widest transition-all flex items-center gap-2', activeTab === 'chat' && chatTarget === 'report_agent' ? 'bg-white/10 text-white shadow-[0_0_20px_rgba(255,255,255,0.15)]' : 'text-white/40 hover:text-white/60']"
          >
            <ZapIcon class="w-3 h-3" />
            Агент отчета
          </button>
          
          <div class="relative group">
            <button 
              @click="toggleAgentDropdown"
              :class="['px-4 py-2 rounded-xl text-[10px] font-bold uppercase tracking-widest transition-all flex items-center gap-2', chatTarget === 'agent' ? 'bg-white/8 text-[#0A0A0F] font-black' : 'text-white/40 hover:text-white/60']"
            >
              <UsersIcon class="w-3 h-3" />
              {{ selectedAgent ? selectedAgent.username : 'Сущности матрицы' }}
              <ChevronDownIcon class="w-3 h-3 opacity-50" />
            </button>
            <!-- Dropdown -->
            <div v-if="showAgentDropdown" class="absolute left-0 top-full mt-2 w-64 bg-[#12121A] border border-white/10 rounded-2xl shadow-2xl z-50 p-2 space-y-1 animate-in slide-in-from-top-2 duration-200">
               <div class="px-3 py-2 text-[9px] font-bold text-white/20 uppercase tracking-widest border-b border-white/5 mb-1">Выбрать след сущности</div>
               <button 
                v-for="(agent, idx) in profiles" 
                :key="idx"
                @click="selectAgent(agent, idx)"
                class="w-full flex items-center gap-3 p-2 rounded-xl hover:bg-white/5 transition-colors text-left"
               >
                 <div class="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center text-[10px] font-bold text-white/40 border border-white/10">{{ agent.username?.charAt(0) }}</div>
                 <div class="min-w-0">
                   <div class="text-[11px] font-bold text-white truncate">{{ agent.username }}</div>
                   <div class="text-[9px] text-white/30 truncate uppercase">{{ agent.profession }}</div>
                 </div>
               </button>
            </div>
          </div>

          <div class="w-px h-4 bg-white/10 mx-2"></div>

          <button 
            @click="selectSurveyTab"
            :class="['px-4 py-2 rounded-xl text-[10px] font-bold uppercase tracking-widest transition-all flex items-center gap-2', activeTab === 'survey' ? 'bg-white text-[#0A0A0F] font-black' : 'text-white/40 hover:text-white/60']"
          >
            <PieChartIcon class="w-3 h-3" />
            Массовый пульс
          </button>
        </div>

        <div class="hidden sm:flex items-center gap-4 text-[10px] font-mono text-white/20">
          <span class="flex items-center gap-1.5"><StatusBadge size="sm" type="cyan" dot /> {{ profiles.length }} Сущностей</span>
        </div>
      </div>

      <!-- Matrix Body -->
      <div class="flex-1 overflow-hidden flex flex-col relative">
        <!-- Chat Interface -->
        <div v-if="activeTab === 'chat'" class="flex-1 flex flex-col overflow-hidden">
          <!-- Chat Context Overlay -->
          <div v-if="chatTarget === 'report_agent' && showToolsDetail" class="px-6 py-3 bg-white/5 border-b border-white/10 flex items-center justify-between text-[10px]">
            <div class="flex items-center gap-6">
               <div v-for="t in ['InsightForge', 'Panorama', 'QuickSync', 'Interviews']" :key="t" class="flex items-center gap-1.5 text-white/90 font-bold uppercase tracking-tighter opacity-80">
                 <div class="w-1 h-1 rounded-full bg-current shadow-glow"></div>
                 {{ t }}
               </div>
            </div>
            <button @click="showToolsDetail = false" class="text-white/20 hover:text-white"><XIcon class="w-3 h-3" /></button>
          </div>

          <!-- Messages -->
          <div class="flex-1 overflow-y-auto px-6 py-8 space-y-6 custom-scrollbar" ref="chatMessages">
            <div v-if="chatHistory.length === 0" class="h-full flex flex-col items-center justify-center space-y-6 opacity-20">
               <MessageSquareIcon class="w-12 h-12" />
               <div class="text-sm font-bold uppercase tracking-[0.3em] text-center max-w-xs">
                 {{ chatTarget === 'report_agent' ? 'Выскажите свои соображения по результатам отчета' : 'Запросите сущность ' + selectedAgent?.username + ' для синтеза перспективы' }}
               </div>
            </div>

            <div v-for="(msg, idx) in chatHistory" :key="idx" :class="['flex gap-4 group', msg.role === 'user' ? 'flex-row-reverse' : '']">
              <div :class="['w-8 h-8 rounded-xl shrink-0 border flex items-center justify-center text-[11px] font-black uppercase shadow-glow transition-all duration-500', 
                msg.role === 'user' ? 'bg-white/5 border-white/20 text-white' : (chatTarget === 'report_agent' ? 'bg-white/10 border-white/30 text-white' : 'bg-white/8 border-white/30 text-[#0A0A0F]')]">
                {{ msg.role === 'user' ? 'U' : (chatTarget === 'report_agent' ? 'R' : (selectedAgent?.username?.charAt(0) || 'A')) }}
              </div>
              <div :class="['max-w-[85%] space-y-1', msg.role === 'user' ? 'text-right' : 'text-left']">
                <div class="text-[9px] font-bold text-white/20 uppercase tracking-widest px-1">
                  {{ msg.role === 'user' ? 'Оператор' : (chatTarget === 'report_agent' ? 'Оракул отчета' : selectedAgent?.username) }}
                  <span class="ml-2 opacity-50 font-mono font-normal">{{ formatTime(msg.timestamp) }}</span>
                </div>
                <div :class="['p-4 rounded-2xl text-[13px] leading-relaxed shadow-lg', 
                  msg.role === 'user' ? 'bg-white/[0.03] border border-white/10 text-white' : 'bg-[#12121A] border border-white/5 text-white/80']">
                  <div class="prose prose-invert prose-sm max-w-none custom-markdown-chat" v-html="renderMarkdown(msg.content)"></div>
                </div>
              </div>
            </div>

            <!-- Typing Indicator -->
            <div v-if="isSending" class="flex gap-4">
              <div :class="['w-8 h-8 rounded-xl shrink-0 border flex items-center justify-center shadow-glow animate-pulse', chatTarget === 'report_agent' ? 'bg-white/10 border-white/30' : 'bg-white/8 border-white/30']">
                <div class="w-4 h-4 rounded-full border-2 border-white/20 border-t-white animate-spin"></div>
              </div>
              <div class="px-4 py-3 rounded-2xl bg-[#12121A] border border-white/5">
                <div class="flex gap-1">
                  <div class="w-1.5 h-1.5 rounded-full bg-white/20 animate-bounce" style="animation-delay: 0s"></div>
                  <div class="w-1.5 h-1.5 rounded-full bg-white/20 animate-bounce" style="animation-delay: 0.1s"></div>
                  <div class="w-1.5 h-1.5 rounded-full bg-white/20 animate-bounce" style="animation-delay: 0.2s"></div>
                </div>
              </div>
            </div>
          </div>

          <!-- Input Area -->
          <div class="p-6 shrink-0 bg-white/[0.02] border-t border-white/5">
            <div :class="['relative group transition-all duration-500 rounded-2xl border bg-[#0A0A0F]/50 backdrop-blur-xl', 
              isSending ? 'opacity-50 pointer-events-none' : (focusInput ? (chatTarget === 'report_agent' ? 'border-white/50 shadow-[0_0_20px_rgba(255,255,255,0.15)]' : 'border-white/50 shadow-[0_0_20px_rgba(255,255,255,0.12)]') : 'border-white/10')]">
              <textarea 
                v-model="chatInput" 
                class="w-full bg-transparent border-none focus:ring-0 text-sm text-white px-5 py-4 min-h-[56px] max-h-40 custom-scrollbar placeholder:text-white/20"
                placeholder="Запрос к когнитивной матрице..."
                rows="1"
                @focus="focusInput = true" 
                @blur="focusInput = false"
                @keydown.enter.exact.prevent="sendMessage"
              ></textarea>
              <button 
                @click="sendMessage"
                :disabled="!chatInput.trim() || isSending"
                :class="['absolute right-3 bottom-3 w-10 h-10 rounded-xl flex items-center justify-center transition-all', 
                  chatInput.trim() ? (chatTarget === 'report_agent' ? 'bg-white/10 text-white shadow-[0_0_20px_rgba(255,255,255,0.15)]' : 'bg-white/8 text-[#0A0A0F] shadow-[0_0_20px_rgba(255,255,255,0.12)]') : 'bg-white/5 text-white/20']"
              >
                <SendHorizonalIcon class="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        <!-- Survey / Mass Pulse Mode -->
        <div v-if="activeTab === 'survey'" class="flex-1 flex flex-col overflow-hidden bg-white/[0.02]">
           <div class="flex-1 overflow-y-auto p-8 space-y-10 custom-scrollbar">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                <!-- Selection Panel -->
                <div class="space-y-6">
                  <div class="flex items-center justify-between">
                    <h3 class="text-xs font-bold text-white uppercase tracking-[0.2em]">Целевые кластеры</h3>
                    <div class="flex gap-4">
                      <button @click="selectAllAgents" class="text-[9px] font-bold text-white/80 uppercase hover:underline">Выбрать все</button>
                      <button @click="clearAgentSelection" class="text-[9px] font-bold text-white/30 uppercase hover:underline">Очистить</button>
                    </div>
                  </div>
                  <div class="grid grid-cols-1 gap-2 max-h-64 overflow-y-auto custom-scrollbar pr-2">
                    <button 
                      v-for="(agent, idx) in profiles" 
                      :key="idx"
                      @click="toggleAgentSelection(idx)"
                      :class="['flex items-center gap-3 p-3 rounded-2xl border transition-all text-left group', 
                        selectedAgents.has(idx) ? 'bg-white/10 border-white/30' : 'bg-white/[0.02] border-white/5 hover:border-white/10']"
                    >
                      <div :class="['w-8 h-8 rounded-lg flex items-center justify-center text-[10px] font-black transition-colors', 
                        selectedAgents.has(idx) ? 'bg-white/8 text-[#0A0A0F]' : 'bg-white/5 text-white/20 group-hover:bg-white/10']">
                        {{ agent.username?.charAt(0) }}
                      </div>
                      <div class="min-w-0 flex-1">
                        <div :class="['text-[11px] font-bold truncate transition-colors', selectedAgents.has(idx) ? 'text-white/80' : 'text-white/60']">{{ agent.username }}</div>
                        <div class="text-[8px] text-white/20 uppercase truncate">{{ agent.profession }}</div>
                      </div>
                      <div v-if="selectedAgents.has(idx)" class="w-4 h-4 rounded-full bg-white/8 flex items-center justify-center"><CheckIcon class="w-2.5 h-2.5 text-[#0A0A0F] font-bold" /></div>
                    </button>
                  </div>
                </div>

                <!-- Input Panel -->
                <div class="space-y-6">
                  <h3 class="text-xs font-bold text-white uppercase tracking-[0.2em]">Матричный запрос</h3>
                  <div class="relative group">
                    <textarea 
                      v-model="surveyQuestion"
                      class="w-full bg-[#0A0A0F]/50 border border-white/10 rounded-2xl p-4 text-sm text-white min-h-[160px] focus:ring-0 focus:border-white/50 transition-all placeholder:text-white/10"
                      placeholder="Введите векторизованный вопрос для распространения по всем выбранным сущностям..."
                    ></textarea>
                    <div class="absolute inset-0 pointer-events-none border border-white/20 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity"></div>
                  </div>
                  <PitchyButton 
                    variant="primary" 
                    class="w-full py-4 shadow-[0_0_20px_rgba(255,255,255,0.12)]" 
                    :disabled="selectedAgents.size === 0 || !surveyQuestion?.trim() || isSurveying"
                    @click="submitSurvey"
                  >
                    Транслировать вопрос
                    <template #icon><ZapIcon class="w-4 h-4" /></template>
                  </PitchyButton>
                </div>
              </div>

              <!-- Survey Results -->
              <div v-if="surveyResults.length > 0" class="space-y-6 animate-in slide-in-from-bottom-8 duration-700">
                <div class="flex items-center justify-between border-b border-white/5 pb-4">
                  <h3 class="text-xs font-bold text-white uppercase tracking-[0.2em]">Результаты синтеза</h3>
                  <span class="text-[10px] font-mono text-white/20">{{ surveyResults.length }} Ответов получено</span>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <GlassCard v-for="(res, idx) in surveyResults" :key="idx" class="p-5 hover:border-white/20 transition-all">
                    <div class="flex items-center gap-3 mb-4">
                      <div class="w-8 h-8 rounded-lg bg-white/10 text-white/80 flex items-center justify-center text-[10px] font-black border border-white/20">{{ res.agent_name?.charAt(0) }}</div>
                      <div>
                        <div class="text-[11px] font-bold text-white">{{ res.agent_name }}</div>
                        <div class="text-[8px] text-white/30 uppercase tracking-widest">{{ res.profession }}</div>
                      </div>
                    </div>
                    <div class="prose prose-invert prose-xs text-white/60 leading-relaxed custom-markdown-chat" v-html="renderMarkdown(res.answer)"></div>
                  </GlassCard>
                </div>
              </div>
           </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import { chatWithReport, getReport, getAgentLog } from '../api/report'
import { interviewAgents, getSimulationProfilesRealtime } from '../api/simulation'
import GlassCard from './ui/GlassCard.vue'
import StatusBadge from './ui/StatusBadge.vue'
import PitchyButton from './ui/PitchyButton.vue'
import { 
  ChevronDown as ChevronDownIcon, 
  MessageSquare as MessageSquareIcon,
  Zap as ZapIcon,
  Users as UsersIcon,
  PieChart as PieChartIcon,
  SendHorizonal as SendHorizonalIcon,
  Check as CheckIcon,
  Loader2 as Loader2Icon,
  X as XIcon
} from 'lucide-vue-next'
import { marked } from 'marked'

const props = defineProps({
  reportId: String,
  simulationId: String
})
const emit = defineEmits(['add-log', 'update-status'])

// Layout State
const activeTab = ref('chat')
const chatTarget = ref('report_agent')
const showAgentDropdown = ref(false)
const selectedAgent = ref(null)
const selectedAgentIndex = ref(null)
const showToolsDetail = ref(true)
const focusInput = ref(false)

// Chat State
const chatInput = ref('')
const chatHistory = ref([])
const chatHistoryCache = ref({})
const isSending = ref(false)
const chatMessages = ref(null)

// Survey State
const selectedAgents = ref(new Set())
const surveyQuestion = ref('')
const surveyResults = ref([])
const isSurveying = ref(false)

// Report Data
const reportOutline = ref(null)
const generatedSections = ref({})
const collapsedSections = ref(new Set())
const currentSectionIndex = ref(null)
const profiles = ref([])

// Methods
const addLog = (msg) => emit('add-log', msg)

const toggleSectionCollapse = idx => {
  if (!generatedSections.value[idx + 1]) return
  const s = new Set(collapsedSections.value)
  if (s.has(idx)) s.delete(idx)
  else s.add(idx)
  collapsedSections.value = s
}

const selectReportAgentChat = () => {
  saveChatHistory(); activeTab.value = 'chat'; chatTarget.value = 'report_agent'; 
  selectedAgent.value = null; selectedAgentIndex.value = null; showAgentDropdown.value = false
  chatHistory.value = chatHistoryCache.value['report_agent'] || []
}

const selectAgent = (agent, idx) => {
  saveChatHistory(); selectedAgent.value = agent; selectedAgentIndex.value = idx; 
  chatTarget.value = 'agent'; showAgentDropdown.value = false
  chatHistory.value = chatHistoryCache.value[`agent_${idx}`] || []
  addLog(`Когнитивная связь установлена с сущностью: ${agent.username}`)
}

const toggleAgentDropdown = () => (showAgentDropdown.value = !showAgentDropdown.value)
const selectSurveyTab = () => { activeTab.value = 'survey'; showAgentDropdown.value = false }

const saveChatHistory = () => {
  if (chatTarget.value === 'report_agent') chatHistoryCache.value['report_agent'] = [...chatHistory.value]
  else if (selectedAgentIndex.value !== null) chatHistoryCache.value[`agent_${selectedAgentIndex.value}`] = [...chatHistory.value]
}

const renderMarkdown = c => c ? marked(c) : ''
const formatTime = ts => ts ? new Date(ts).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' }) : ''
const scrollToBottom = () => nextTick(() => { if (chatMessages.value) chatMessages.value.scrollTop = chatMessages.value.scrollHeight })

const sendMessage = async () => {
  if (!chatInput.value.trim() || isSending.value) return
  const msg = chatInput.value.trim(); chatInput.value = ''; isSending.value = true
  chatHistory.value.push({ role: 'user', content: msg, timestamp: new Date().toISOString() })
  scrollToBottom()
  try {
    if (chatTarget.value === 'report_agent') {
      const res = await chatWithReport({ simulation_id: props.simulationId, message: msg, chat_history: chatHistory.value.slice(-6).map(m => ({ role: m.role, content: m.content })) })
      if (res.success && res.data) {
        const responseData = res.data.response || res.data.answer || res.data;
        chatHistory.value.push({ role: 'assistant', content: responseData, timestamp: new Date().toISOString() })
      }
    } else {
      const res = await interviewAgents({ simulation_id: props.simulationId, interviews: [{ agent_id: selectedAgentIndex.value, prompt: msg }] })
      if (res.success && res.data) {
        const results = res.data.results || res.data; 
        const agentRes = results[`reddit_${selectedAgentIndex.value}`] || results[`twitter_${selectedAgentIndex.value}`] || Object.values(results)[0];
        if (agentRes) {
          chatHistory.value.push({ role: 'assistant', content: agentRes.response || agentRes.answer || agentRes, timestamp: new Date().toISOString() })
        }
      }
    }
  } catch (e) { addLog(`Сбой связи с матрицей: ${e.message}`) }
  finally { isSending.value = false; scrollToBottom(); saveChatHistory() }
}

const toggleAgentSelection = idx => {
  const s = new Set(selectedAgents.value); if (s.has(idx)) s.delete(idx); else s.add(idx); selectedAgents.value = s
}
const selectAllAgents = () => { const s = new Set(); profiles.value.forEach((_, i) => s.add(i)); selectedAgents.value = s }
const clearAgentSelection = () => selectedAgents.value = new Set()

const submitSurvey = async () => {
  if (selectedAgents.value.size === 0 || !surveyQuestion.value?.trim() || isSurveying.value) return
  isSurveying.value = true; addLog('Распространение массового пульсового запроса...')
  try {
    const interviews = Array.from(selectedAgents.value).map(idx => ({ agent_id: idx, prompt: surveyQuestion.value }))
    const res = await interviewAgents({ simulation_id: props.simulationId, interviews })
    if (res.success) {
      const results = res.data.results || res.data; surveyResults.value = Object.entries(results).map(([k, v]) => ({
        agent_name: profiles.value[parseInt(k.split('_')[1])]?.username,
        profession: profiles.value[parseInt(k.split('_')[1])]?.profession,
        answer: v.response || v.answer
      }))
    }
  } catch (e) { addLog(`Ошибка массового пульса: ${e.message}`) }
  finally { isSurveying.value = false }
}

// Data Loading
const loadInitialData = async () => {
  if (!props.reportId) return
  const rRes = await getReport(props.reportId); if (rRes.success) {
    const aRes = await getAgentLog(props.reportId, 0)
    if (aRes.success) aRes.data.logs.forEach(l => {
      if (l.action === 'planning_complete') reportOutline.value = l.details.outline
      if (l.action === 'section_content') generatedSections.value[l.section_index] = l.details.content
    })
  }
  if (props.simulationId) {
    const pRes = await getSimulationProfilesRealtime(props.simulationId)
    if (pRes.success) profiles.value = pRes.data.profiles || []
  }
}

onMounted(loadInitialData)

watch(() => props.reportId, () => loadInitialData())
watch(() => props.simulationId, () => loadInitialData())
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
.shadow-glow-cyan-fx { box-shadow: 0 0 20px -5px rgba(34, 211, 238, 0.3); }
.custom-markdown-small :deep(p) { margin: 0.5rem 0; line-height: 1.5; }
.custom-markdown-chat :deep(p) { margin: 0.8rem 0; line-height: 1.6; }
.custom-markdown-chat :deep(ul) { list-style: disc; padding-left: 1.2rem; margin: 0.5rem 0; }
</style>
