<template>
  <div class="space-y-8 animate-in fade-in slide-in-from-right-4 duration-700">
    <!-- Introduction -->
    <div class="space-y-2">
      <h2 class="text-2xl font-bold text-white tracking-tight italic">
        <span class="text-pitchy-violet">02</span> / Манифестация среды
      </h2>
    <p class="text-xs text-white/40 leading-relaxed max-w-xl">
      Настройка общества агентов и динамики социальных платформ на основе синтезированного графа знаний.
    </p>
    </div>

    <!-- Step 01: Simulation Instance -->
    <GlassCard :class="{ 'border-pitchy-violet/30 bg-pitchy-violet/5': phase === 0 }">
      <div class="flex items-start justify-between mb-6">
        <div class="space-y-1">
          <div class="flex items-center gap-2 text-[10px] font-mono text-white/30 uppercase tracking-widest">
            <span>Протокол экземпляра</span>
            <span class="w-px h-2 bg-white/10"></span>
            <span class="text-pitchy-violet">POST /api/simulation/create</span>
          </div>
          <h3 class="text-lg font-bold text-white">Инициализация экземпляра</h3>
        </div>
        <StatusBadge :type="phase > 0 ? 'success' : 'primary'">
          {{ phase > 0 ? 'Инициализировано' : 'Создание' }}
        </StatusBadge>
      </div>

      <div v-if="simulationId" class="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 rounded-2xl bg-white/[0.02] border border-white/5">
        <div v-for="(v, k) in { 'Проект': projectData?.project_id, 'Граф': projectData?.graph_id, 'Симуляция': simulationId, 'Задача': taskId || 'SYNC' }" :key="k" class="space-y-1">
          <span class="text-[8px] font-bold text-white/20 uppercase tracking-widest">ID {{ k }}</span>
          <div class="text-[10px] font-mono text-white/60 truncate" :title="v">{{ v?.slice(0, 8) }}...</div>
        </div>
      </div>
    </GlassCard>

    <!-- Step 02: Agent Personas -->
    <GlassCard :class="{ 'border-pitchy-violet/30 bg-pitchy-violet/5': phase === 1 }">
      <div class="flex items-start justify-between mb-8">
        <div class="space-y-1">
          <div class="flex items-center gap-2 text-[10px] font-mono text-white/30 uppercase tracking-widest">
            <span>Активация агентов</span>
            <span class="w-px h-2 bg-white/10"></span>
            <span class="text-pitchy-violet">POST /api/simulation/prepare</span>
          </div>
          <h3 class="text-lg font-bold text-white">Генерация персон агентов</h3>
        </div>
        <StatusBadge :type="phase > 1 ? 'success' : (phase === 1 ? 'primary' : 'default')">
          {{ phase > 1 ? 'Заселено' : (phase === 1 ? `${prepareProgress}%` : 'Ожидание') }}
        </StatusBadge>
      </div>

      <div class="space-y-8">
        <!-- Stats Grid -->
        <div v-if="profiles.length > 0" class="grid grid-cols-3 gap-4">
          <div v-for="(val, label) in { 'Агенты': profiles.length, 'Цель': expectedTotal || '-', 'Темы': totalTopicsCount }" :key="label" 
            class="p-4 rounded-2xl bg-white/[0.01] border border-white/5 text-center">
            <div class="text-xl font-bold text-white font-mono">{{ val }}</div>
            <div class="text-[8px] font-bold text-white/20 uppercase tracking-widest">{{ label }}</div>
          </div>
        </div>

        <!-- Profiles List -->
        <div v-if="profiles.length > 0" class="space-y-4">
          <div class="flex items-center justify-between px-1">
            <span class="text-[9px] font-bold text-white/30 uppercase tracking-[0.2em]">Синтезированные персоны</span>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div 
              v-for="(profile, idx) in profiles" 
              :key="idx" 
              @click="selectProfile(profile)"
              class="group p-4 rounded-2xl bg-[#0A0A0F]/40 border border-white/5 hover:border-pitchy-violet/50 transition-all cursor-pointer space-y-3 relative overflow-hidden"
            >
              <!-- Delete Action -->
              <button 
                v-if="phase >= 2"
                @click.stop="handleDeleteProfile(idx)"
                class="absolute top-2 right-2 p-1.5 rounded-lg bg-red-500/10 text-red-500 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-500/20"
                title="Удалить агента"
              >
                <TrashIcon class="w-3 h-3" />
              </button>

              <div class="flex items-start justify-between">
                <div class="space-y-0.5">
                  <div class="text-sm font-bold text-white group-hover:text-pitchy-violet-light transition-colors">{{ profile.username }}</div>
                  <div class="text-[10px] font-mono text-white/30">@{{ profile.name }}</div>
                </div>
                <div class="text-[9px] px-2 py-0.5 rounded bg-white/5 border border-white/5 text-white/40 uppercase">{{ profile.profession?.slice(0, 12) }}</div>
              </div>
              <p class="text-[11px] text-white/50 line-clamp-2 leading-relaxed italic">"{{ profile.bio }}"</p>
              <div class="flex flex-wrap gap-1.5">
                <span v-for="topic in profile.interested_topics?.slice(0, 3)" :key="topic" class="px-2 py-0.5 rounded bg-pitchy-violet/5 text-[8px] font-bold text-pitchy-violet-light border border-pitchy-violet/10">
                  {{ topic }}
                </span>
                <span v-if="profile.interested_topics?.length > 3" class="text-[8px] text-white/20 align-middle leading-loose">+{{ profile.interested_topics.length - 3 }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </GlassCard>

    <!-- Step 03: Configuration Details -->
    <GlassCard v-if="simulationConfig" :class="{ 'border-pitchy-cyan/30 bg-pitchy-cyan/5': phase === 2 }">
      <div class="flex items-start justify-between mb-8">
        <div class="space-y-1">
          <div class="flex items-center gap-2 text-[10px] font-mono text-white/30 uppercase tracking-widest">
            <span>Параметры матрицы</span>
            <span class="w-px h-2 bg-white/10"></span>
            <span class="text-pitchy-cyan">DYNAMIC_CALCULATION</span>
          </div>
          <h3 class="text-lg font-bold text-white">Конфигурация платформ</h3>
        </div>
        <StatusBadge type="cyan">Сгенерировано</StatusBadge>
      </div>

      <div class="space-y-8">
        <!-- Time Config -->
        <div class="space-y-4">
          <div class="flex items-center gap-2 px-1">
            <ClockIcon class="w-3 h-3 text-pitchy-cyan" />
            <span class="text-[9px] font-bold text-white/30 uppercase tracking-[0.2em]">Темпоральная механика</span>
          </div>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div v-for="(v, k) in { 'Длительность': simulationConfig.time_config?.total_simulation_hours + 'ч', 'Раунд': simulationConfig.time_config?.minutes_per_round + 'м', 'Раундов': autoGeneratedRounds, 'Поток': simulationConfig.time_config?.peak_activity_multiplier + 'x' }" :key="k" 
              class="p-4 rounded-2xl bg-white/[0.01] border border-white/5 text-center">
              <div class="text-base font-bold text-white font-mono">{{ v }}</div>
              <div class="text-[8px] font-bold text-white/20 uppercase tracking-widest">{{ k }}</div>
            </div>
          </div>
        </div>

        <!-- Platform Config -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div v-for="plt in ['twitter', 'reddit']" :key="plt" class="p-6 rounded-3xl bg-white/[0.01] border border-white/5 space-y-4 relative overflow-hidden group/plt">
            <div class="absolute top-0 right-0 p-4 opacity-5 group-hover/plt:opacity-10 transition-opacity">
              <component :is="plt === 'twitter' ? TwitterIcon : LayoutIcon" class="w-20 h-20 text-white" />
            </div>
            <div class="text-[10px] font-bold text-pitchy-cyan uppercase tracking-widest">{{ plt === 'twitter' ? 'Квадратная матрица' : 'Кластер сообщества' }}</div>
            <div class="space-y-2">
              <div v-for="(v, k) in simulationConfig[`${plt}_config`]" :key="k" class="flex items-center justify-between text-[10px]">
                <span class="text-white/30 uppercase tracking-tighter">{{ k.replace('_weight', '').replace('_', ' ') }}</span>
                <span class="font-mono text-white/70">{{ v }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </GlassCard>

    <!-- Step 04: Narrative Arrangement -->
    <GlassCard v-if="simulationConfig?.event_config" :class="{ 'border-pitchy-violet/30 bg-pitchy-violet/5': phase === 3 }">
      <div class="flex items-start justify-between mb-8">
        <div class="space-y-1">
          <div class="flex items-center gap-2 text-[10px] font-mono text-white/30 uppercase tracking-widest">
            <span>Слой оркестрации</span>
            <span class="w-px h-2 bg-white/10"></span>
            <span class="text-pitchy-violet">INITIAL_PULSE</span>
          </div>
          <h3 class="text-lg font-bold text-white">Активация нарратива</h3>
        </div>
        <StatusBadge type="primary">Скомпоновано</StatusBadge>
      </div>

      <div class="space-y-8">
        <div class="p-6 rounded-3xl bg-gradient-to-br from-pitchy-violet/10 to-transparent border border-pitchy-violet/20 space-y-4">
          <div class="flex items-center gap-2">
            <div class="w-6 h-6 rounded-lg bg-pitchy-violet/20 flex items-center justify-center">
              <CompassIcon class="w-3.5 h-3.5 text-pitchy-violet" />
            </div>
            <span class="text-[10px] font-bold text-white uppercase tracking-widest">Направление вектора нарратива</span>
          </div>
          <p class="text-sm text-white/70 leading-relaxed italic">"{{ simulationConfig.event_config.narrative_direction }}"</p>
        </div>

        <div class="space-y-4">
          <span class="text-[9px] font-bold text-white/30 uppercase tracking-[0.2em] px-1">Хронология начальной активации</span>
          <div class="space-y-3 relative before:absolute before:left-3 before:top-2 before:bottom-2 before:w-px before:bg-white/5">
            <div v-for="(post, idx) in simulationConfig.event_config.initial_posts" :key="idx" class="relative pl-10 group/post">
              <div class="absolute left-2 top-2 w-2 h-2 rounded-full bg-pitchy-violet/20 border border-pitchy-violet/50 group-hover/post:bg-pitchy-violet transition-all"></div>
              <div class="p-4 rounded-2xl bg-white/[0.02] border border-white/5 hover:border-white/10 transition-colors space-y-2">
                <div class="flex items-center justify-between text-[10px]">
                  <div class="flex items-center gap-2">
                    <span class="px-1.5 py-0.5 rounded bg-pitchy-cyan/10 text-pitchy-cyan font-mono text-[8px] uppercase">{{ post.poster_type }}</span>
                    <span class="text-white/40 font-bold">Агент {{ post.poster_agent_id }}</span>
                  </div>
                  <span class="text-white/20 font-mono">@{{ getAgentUsername(post.poster_agent_id) }}</span>
                </div>
                <p class="text-[11px] text-white/60 leading-relaxed">{{ post.content }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </GlassCard>

    <!-- Step 05: Final Launch -->
    <GlassCard v-if="phase >= 4" class="border-pitchy-cyan bg-pitchy-cyan/10 shadow-glow-cyan/20 overflow-hidden">
      <div class="flex flex-col items-center text-center space-y-8 pt-4">
        <div class="w-16 h-16 rounded-full bg-pitchy-cyan/20 flex items-center justify-center text-pitchy-cyan shadow-glow shadow-pitchy-cyan relative">
          <RocketIcon class="w-8 h-8" />
          <div class="absolute inset-0 rounded-full border border-pitchy-cyan animate-ping opacity-20"></div>
        </div>
        
        <div class="space-y-2">
          <h3 class="text-2xl font-bold text-white tracking-tight">Среда синхронизирована</h3>
          <p class="text-xs text-white/50 max-w-sm">Модель мира и {{ profiles.length }} агентов готовы к запуску. Определите глубину симуляции ниже.</p>
        </div>

        <!-- Custom Slider -->
        <div class="w-full max-w-md bg-white/5 p-6 rounded-3xl border border-white/5 space-y-6">
          <div class="flex items-center justify-between">
            <div class="text-left space-y-1">
              <span class="text-[10px] font-bold text-white/30 uppercase tracking-[0.2em]">Глубина симуляции</span>
              <div class="text-lg font-bold text-white font-mono">{{ useCustomRounds ? customMaxRounds : autoGeneratedRounds }} <span class="text-xs text-white/40">РАУНДОВ</span></div>
            </div>
            <label class="flex items-center gap-2 cursor-pointer group">
              <span class="text-[9px] font-bold text-white/30 group-hover:text-white/60">КАСТОМНЫЙ_ЛИМИТ</span>
              <input type="checkbox" v-model="useCustomRounds" class="sr-only peer" />
              <div class="w-8 h-5 bg-white/10 rounded-full peer peer-checked:bg-pitchy-cyan relative after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-3"></div>
            </label>
          </div>

          <div v-if="useCustomRounds" class="space-y-4 animate-in slide-in-from-top-2 duration-300">
            <input 
              type="range" v-model.number="customMaxRounds" min="10" :max="autoGeneratedRounds" step="5"
              class="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-pitchy-cyan"
            />
            <div class="flex justify-between text-[8px] font-mono text-white/20">
              <span>10 РНД (БЫСТРО)</span>
              <span>АВТО_ЛИМИТ: {{ autoGeneratedRounds }} РНД</span>
            </div>
          </div>
          
          <p v-else class="text-[10px] text-pitchy-cyan/60 font-medium animate-pulse cursor-pointer" @click="useCustomRounds = true">
            >> Рекомендуется ручное переопределение глубины для быстрого прототипирования.
          </p>
        </div>
        
        <div class="grid grid-cols-2 gap-4 w-full pt-4">
          <PitchyButton variant="secondary" @click="$emit('go-back')">Сбросить матрицу</PitchyButton>
          <PitchyButton variant="primary" @click="handleStartSimulation" shadow class="shadow-glow-cyan shadow-pitchy-cyan/20">
            Запустить симуляцию мультивселенной
          </PitchyButton>
        </div>
      </div>
    </GlassCard>

    <!-- Profile Modal (Redesigned) -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="selectedProfile" class="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <div class="absolute inset-0 bg-pitchy-bg/90 backdrop-blur-md" @click="selectedProfile = null"></div>
          <GlassCard class="relative z-10 w-full max-w-2xl bg-[#0A0A0F] border-white/10 shadow-2xl p-0 overflow-hidden animate-in zoom-in duration-300">
            <div class="p-6 border-b border-white/5 flex items-start justify-between bg-white/[0.02]">
              <div class="flex items-center gap-4">
                <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-pitchy-violet to-pitchy-cyan flex items-center justify-center text-white font-bold text-xl">
                  {{ selectedProfile.username?.charAt(0) }}
                </div>
                <div class="space-y-1">
                  <h4 class="text-xl font-bold text-white">{{ selectedProfile.username }}</h4>
                  <div class="flex items-center gap-2">
                    <span class="text-xs font-mono text-white/30">@{{ selectedProfile.name }}</span>
                    <span class="w-1 h-1 rounded-full bg-white/20"></span>
                    <span class="text-[10px] font-bold text-pitchy-violet uppercase">{{ selectedProfile.profession }}</span>
                  </div>
                </div>
              </div>
              <button @click="selectedProfile = null" class="p-2 text-white/40 hover:text-white transition-colors"><XIcon class="w-6 h-6" /></button>
            </div>

            <div class="p-8 space-y-8 overflow-y-auto max-h-[70vh] custom-scrollbar">
              <!-- Stats Grid -->
              <div class="grid grid-cols-4 gap-4">
                <div v-for="(v, k) in { 'Возраст': selectedProfile.age, 'Пол': selectedProfile.gender, 'Регион': selectedProfile.country, 'MBTI': selectedProfile.mbti }" :key="k" class="p-3 rounded-2xl bg-white/5 border border-white/5 text-center space-y-1">
                  <div class="text-[8px] font-bold text-white/20 uppercase tracking-widest">{{ k }}</div>
                  <div class="text-xs font-bold text-white">{{ v || '-' }}</div>
                </div>
              </div>

              <div class="space-y-4">
                <div class="space-y-2">
                  <span class="text-[10px] font-bold text-white/30 uppercase tracking-[0.2em]">Персона контекста</span>
                  <p class="text-sm text-white/70 leading-relaxed italic">"{{ selectedProfile.bio }}"</p>
                </div>

                <div v-if="selectedProfile.persona" class="p-6 rounded-3xl bg-white/[0.02] border border-white/5 space-y-4">
                  <span class="text-[10px] font-bold text-pitchy-cyan uppercase tracking-widest">Когнитивный бэкграунд</span>
                  <p class="text-xs text-white/60 leading-relaxed">{{ selectedProfile.persona }}</p>
                </div>

                <div v-if="selectedProfile.interested_topics?.length" class="space-y-3">
                   <span class="text-[10px] font-bold text-white/30 uppercase tracking-[0.2em]">Каналы архитектуры общества</span>
                   <div class="flex flex-wrap gap-2">
                     <span v-for="topic in selectedProfile.interested_topics" :key="topic" class="px-3 py-1.5 rounded-xl bg-pitchy-violet/5 border border-pitchy-violet/10 text-[10px] text-pitchy-violet-light font-medium italic">
                        #{{ topic }}
                     </span>
                   </div>
                </div>
              </div>
            </div>

            <div class="p-4 border-t border-white/5 bg-white/[0.01] text-[9px] font-mono text-white/20 text-center">
              AGENT_ID: {{ profiles.indexOf(selectedProfile) }} | СТАТУС: СТАБИЛЬНЫЙ
            </div>
          </GlassCard>
        </div>
      </Transition>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { 
  prepareSimulation, 
  getPrepareStatus, 
  getSimulationProfilesRealtime,
  getSimulationConfigRealtime,
  updateSimulationProfiles
} from '../api/simulation'
import GlassCard from './ui/GlassCard.vue'
import StatusBadge from './ui/StatusBadge.vue'
import PitchyButton from './ui/PitchyButton.vue'
import { 
  X as XIcon, 
  Clock as ClockIcon,
  Twitter as TwitterIcon,
  Layout as LayoutIcon,
  Compass as CompassIcon,
  Rocket as RocketIcon,
  Trash2 as TrashIcon
} from 'lucide-vue-next'

const props = defineProps({
  simulationId: String,
  projectData: Object,
  graphData: Object
})

const emit = defineEmits(['go-back', 'next-step', 'add-log', 'update-status'])

const phase = ref(0)
const taskId = ref(null)
const prepareProgress = ref(0)
const currentStage = ref('')
const profiles = ref([])
const expectedTotal = ref(null)
const simulationConfig = ref(null)
const selectedProfile = ref(null)
const logContent = ref(null)
const useCustomRounds = ref(false)
const customMaxRounds = ref(40)

watch(currentStage, (ns) => {
  if (ns === 'GenerateAgentPersona' || ns === 'generating_profiles') phase.value = 1
  else if (ns === 'Generate Simulation Configuration' || ns === 'generating_config') {
    phase.value = 2
    if (!configTimer) { addLog('Синтез механик двух платформ...'); startConfigPolling() }
  } else if (ns === 'Prepare simulation script' || ns === 'copying_scripts') phase.value = 3
})

const autoGeneratedRounds = computed(() => {
  if (!simulationConfig.value?.time_config) return null
  const { total_simulation_hours, minutes_per_round } = simulationConfig.value.time_config
  return Math.max(Math.floor((total_simulation_hours * 60) / minutes_per_round), 40)
})

let pollTimer, profilesTimer, configTimer

const getAgentUsername = (id) => profiles.value?.[id]?.username || `agent_${id}`
const totalTopicsCount = computed(() => profiles.value.reduce((s, p) => s + (p.interested_topics?.length || 0), 0))

const addLog = (msg) => emit('add-log', msg)

const handleStartSimulation = () => {
  const params = useCustomRounds.value ? { maxRounds: customMaxRounds.value } : {}
  emit('next-step', params)
}

const startPrepareSimulation = async () => {
  if (!props.simulationId) return
  phase.value = 1
  addLog(`Инициализация среды: ${props.simulationId}`)
  emit('update-status', 'processing')
  try {
    const res = await prepareSimulation({ simulation_id: props.simulationId, use_llm_for_profiles: true, parallel_profile_count: 5 })
    if (res.success && res.data) {
      if (res.data.already_prepared) { addLog('Обнаружена существующая матрица. Восстановление.'); await loadPreparedData(); return }
      taskId.value = res.data.task_id
      expectedTotal.value = res.data.expected_total_profiles
      startPolling()
      startProfilesPolling()
    }
  } catch (err) { console.error(err); emit('update-status', 'error') }
}

const loadPreparedData = async () => {
  try {
    const pRes = await getSimulationProfilesRealtime(props.simulationId)
    if (pRes.success) profiles.value = pRes.data
    const cRes = await getSimulationConfigRealtime(props.simulationId)
    if (cRes.success) {
      simulationConfig.value = cRes.data
      phase.value = 4
      emit('update-status', 'completed')
    }
  } catch (e) { console.error(e) }
}

const startPolling = () => { pollStatus(); pollTimer = setInterval(pollStatus, 3000) }
const startProfilesPolling = () => { pollProfiles(); profilesTimer = setInterval(pollProfiles, 5000) }
const startConfigPolling = () => { pollConfig(); configTimer = setInterval(pollConfig, 5000) }

const pollStatus = async () => {
  if (!taskId.value) return
  try {
    const res = await getPrepareStatus({ 
      task_id: taskId.value, 
      simulation_id: props.simulationId 
    })
    if (res.success) {
      const task = res.data
      if (task.message) addLog(task.message)
      prepareProgress.value = task.progress || 0
      currentStage.value = task.stage || ''
      if (task.status === 'completed') {
        stopAllTimers()
        phase.value = 4
        emit('update-status', 'completed')
        addLog('Общество агентов полностью манифестировано.')
      } else if (task.status === 'failed') {
        stopAllTimers()
        addLog(`Ошибка манифестации: ${task.error}`)
        emit('update-status', 'error')
      }
    }
  } catch (e) { console.error(e) }
}

const pollProfiles = async () => {
  try {
    const res = await getSimulationProfilesRealtime(props.simulationId)
    if (res.success && res.data.length > profiles.value.length) {
      profiles.value = res.data
      addLog(`Новые агенты материализованы: ${res.data.length}/${expectedTotal.value || '?'}`)
    }
  } catch (e) { console.error(e) }
}

const pollConfig = async () => {
  try {
    const res = await getSimulationConfigRealtime(props.simulationId)
    if (res.success && res.data) {
      simulationConfig.value = res.data
      if (res.data.status === 'completed') stopConfigPolling()
    }
  } catch (e) { console.error(e) }
}

const stopAllTimers = () => { clearInterval(pollTimer); clearInterval(profilesTimer); clearInterval(configTimer) }
const stopConfigPolling = () => clearInterval(configTimer)
const stopProfilesPolling = () => clearInterval(profilesTimer)

const handleDeleteProfile = async (idx) => {
  const removed = profiles.value.splice(idx, 1)[0]
  addLog(`Агент ${removed.username} удален из архитектуры.`)
  
  try {
    await updateSimulationProfiles(props.simulationId, {
      platform: 'reddit', // Currently primarily reddit-based profiles in display
      profiles: profiles.value
    })
  } catch (e) {
    console.error('Failed to sync deleted profile:', e)
    addLog('Ошибка синхронизации при удалении агента.')
  }
}


onMounted(startPrepareSimulation)
onUnmounted(stopAllTimers)
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.shadow-glow-cyan { filter: drop-shadow(0 0 10px rgba(6, 182, 212, 0.15)); }
</style>
