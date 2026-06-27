<template>
  <div class="space-y-8 animate-in fade-in slide-in-from-right-4 duration-700">
    <!-- Introduction -->
    <div class="block">
      <span class="block text-[10px] font-bold text-white/30 uppercase tracking-[0.25em] font-sans mb-2">Подготовка</span>
      <h2 class="block font-sans not-italic text-2xl font-semibold text-white tracking-tight mb-3">
        Собираем персон
      </h2>
      <p class="block text-sm text-white/55 leading-relaxed max-w-2xl">
        Генерируем представителей ваших сегментов на основе карты рынка. Кликните по любой персоне — увидите её характеристики.
      </p>
    </div>

    <!-- Step 01: Simulation Instance -->
    <GlassCard :class="{ 'border-white/30 bg-white/5': phase === 0 }">
      <div class="flex items-start justify-between mb-6">
        <div class="space-y-1">
          <h3 class="text-lg font-bold text-white">Окружение фокус-группы</h3>
          <div class="text-[11px] text-white/35">готовим среду для общества персон</div>
        </div>
        <StatusBadge :type="phase > 0 ? 'success' : 'primary'">
          {{ phase > 0 ? 'Готово' : 'Создаём' }}
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
    <GlassCard :class="{ 'border-white/30 bg-white/5': phase === 1 }">
      <div class="flex items-start justify-between mb-8">
        <div class="space-y-1">
          <h3 class="text-lg font-bold text-white">Персоны общества</h3>
          <div class="text-[11px] text-white/35">генерируем представителей сегментов</div>
        </div>
        <div class="flex items-center gap-3">
          <button
            v-if="phase === 1"
            @click="stopAllTimers(); addLog('Генерация остановлена пользователем.'); phase = 0;"
            class="text-[10px] text-white/30 hover:text-red-400 uppercase tracking-wide"
          >
            стоп
          </button>
          <StatusBadge :type="phase > 1 ? 'success' : (phase === 1 ? 'primary' : 'default')">
            {{ phase > 1 ? 'Готово' : (phase === 1 ? `${prepareProgress}%` : 'Ожидание') }}
          </StatusBadge>
        </div>
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
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div
              v-for="(profile, idx) in profiles"
              :key="idx"
              @click="selectProfile(profile)"
              class="group p-4 rounded-2xl bg-white/[0.03] border border-white/10 hover:border-white/25 transition-all cursor-pointer relative"
            >
              <button
                v-if="phase >= 2"
                @click.stop="handleDeleteProfile(idx)"
                class="absolute top-2 right-2 p-1.5 rounded-lg text-white/25 opacity-0 group-hover:opacity-100 transition-opacity hover:text-red-400"
                title="Удалить персону"
              >
                <TrashIcon class="w-3.5 h-3.5" />
              </button>
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-full shrink-0 flex items-center justify-center text-sm font-black bg-white/10 text-white border border-white/15">
                  {{ (profile.username || '?').charAt(0).toUpperCase() }}
                </div>
                <div class="min-w-0 flex-1">
                  <div class="text-sm font-bold text-white truncate">{{ profile.username }}</div>
                  <div class="text-[11px] text-white/40 truncate">{{ profile.profession || '—' }}<span v-if="profile.age"> · {{ profile.age }}</span></div>
                </div>
              </div>
              <p v-if="profile.bio" class="text-[12px] text-white/55 line-clamp-2 leading-relaxed mt-3">{{ profile.bio }}</p>
              <div class="flex flex-wrap gap-1.5 mt-3">
                <span v-for="topic in profile.interested_topics?.slice(0, 3)" :key="topic" class="px-2 py-0.5 rounded-full bg-white/[0.06] text-[10px] text-white/55">{{ topic }}</span>
                <span v-if="profile.interested_topics?.length > 3" class="text-[10px] text-white/25 leading-loose">+{{ profile.interested_topics.length - 3 }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </GlassCard>

    <!-- Step 03: Configuration Details -->
    <GlassCard v-if="simulationConfig" :class="{ 'border-white/30 bg-white/5': phase === 2 }">
      <div class="flex items-start justify-between mb-8">
        <div class="space-y-1">
          <div class="flex items-center gap-2 text-[10px] font-mono text-white/30 uppercase tracking-widest">
            <span>Параметры матрицы</span>
            <span class="w-px h-2 bg-white/10"></span>
            <span class="text-white/80">DYNAMIC_CALCULATION</span>
          </div>
          <h3 class="text-lg font-bold text-white">Конфигурация платформ</h3>
        </div>
        <StatusBadge type="cyan">Сгенерировано</StatusBadge>
      </div>

      <div class="space-y-8">
        <!-- Time Config -->
        <div class="space-y-4">
          <div class="flex items-center gap-2 px-1">
            <ClockIcon class="w-3 h-3 text-white/80" />
            <span class="text-[9px] font-bold text-white/30 uppercase tracking-[0.2em]">Темпоральная механика</span>
          </div>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div v-for="(v, k) in { 'Длительность': (simulationConfig.time_config?.total_simulation_hours || 0) + 'ч', 'Раунд': (simulationConfig.time_config?.minutes_per_round || 0) + 'м', 'Раундов': autoGeneratedRounds || 0, 'Поток': (simulationConfig.time_config?.peak_activity_multiplier || 0) + 'x' }" :key="k" 
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
            <div class="text-[10px] font-bold text-white/80 uppercase tracking-widest">{{ plt === 'twitter' ? 'Квадратная матрица' : 'Кластер сообщества' }}</div>
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
    <GlassCard v-if="simulationConfig?.event_config" :class="{ 'border-white/30 bg-white/5': phase === 3 }">
      <div class="flex items-start justify-between mb-8">
        <div class="space-y-1">
          <div class="flex items-center gap-2 text-[10px] font-mono text-white/30 uppercase tracking-widest">
            <span>Слой оркестрации</span>
            <span class="w-px h-2 bg-white/10"></span>
            <span class="text-white">INITIAL_PULSE</span>
          </div>
          <h3 class="text-lg font-bold text-white">Активация нарратива</h3>
        </div>
        <StatusBadge type="primary">Скомпоновано</StatusBadge>
      </div>

      <div class="space-y-8">
        <div class="p-6 rounded-3xl bg-gradient-to-br from-white/10 to-transparent border border-white/20 space-y-4">
          <div class="flex items-center gap-2">
            <div class="w-6 h-6 rounded-lg bg-white/20 flex items-center justify-center">
              <CompassIcon class="w-3.5 h-3.5 text-white" />
            </div>
            <span class="text-[10px] font-bold text-white uppercase tracking-widest">Направление вектора нарратива</span>
          </div>
          <p class="text-sm text-white/70 leading-relaxed italic">"{{ simulationConfig.event_config.narrative_direction }}"</p>
        </div>

        <div class="space-y-4">
          <span class="text-[9px] font-bold text-white/30 uppercase tracking-[0.2em] px-1">Хронология начальной активации</span>
          <div class="space-y-3 relative before:absolute before:left-3 before:top-2 before:bottom-2 before:w-px before:bg-white/5">
            <div v-for="(post, idx) in simulationConfig.event_config.initial_posts" :key="idx" class="relative pl-10 group/post">
              <div class="absolute left-2 top-2 w-2 h-2 rounded-full bg-white/20 border border-white/50 group-hover/post:bg-white/10 transition-all"></div>
              <div class="p-4 rounded-2xl bg-white/[0.02] border border-white/5 hover:border-white/10 transition-colors space-y-2">
                <div class="flex items-center justify-between text-[10px]">
                  <div class="flex items-center gap-2">
                    <span class="px-1.5 py-0.5 rounded bg-white/10 text-white/80 font-mono text-[8px] uppercase">{{ post.poster_type }}</span>
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
    <GlassCard v-if="phase >= 4" class="border-white/20 bg-white/10 shadow-[0_0_20px_rgba(255,255,255,0.12)]/20 overflow-hidden">
      <div class="flex flex-col items-stretch text-center space-y-8 pt-4 w-full">
        <div class="w-16 h-16 rounded-full bg-white/20 flex items-center justify-center text-white/80 shadow-glow shadow-white/25 relative mx-auto shrink-0">
          <RocketIcon class="w-8 h-8" />
          <div class="absolute inset-0 rounded-full border border-white/20 animate-ping opacity-20"></div>
        </div>

        <div class="w-full max-w-md mx-auto">
          <h3 class="text-2xl font-bold text-white tracking-tight mb-2">Среда синхронизирована</h3>
          <p class="text-sm text-white/50 leading-relaxed">Модель мира и {{ profiles.length }} агентов готовы к запуску. Определите глубину симуляции ниже.</p>
        </div>

        <!-- Custom Slider -->
        <div class="w-full max-w-md mx-auto bg-white/5 p-6 rounded-3xl border border-white/5 space-y-6">
          <div class="flex items-center justify-between">
            <div class="text-left space-y-1">
              <span class="text-[10px] font-bold text-white/30 uppercase tracking-[0.2em]">Глубина симуляции</span>
              <div class="text-lg font-bold text-white font-mono">{{ useCustomRounds ? customMaxRounds : autoGeneratedRounds }} <span class="text-xs text-white/40">РАУНДОВ</span></div>
            </div>
            <label class="flex items-center gap-2 cursor-pointer group">
              <span class="text-[9px] font-bold text-white/30 group-hover:text-white/60">КАСТОМНЫЙ_ЛИМИТ</span>
              <input type="checkbox" v-model="useCustomRounds" class="sr-only peer" />
              <div class="w-8 h-5 bg-white/10 rounded-full peer peer-checked:bg-white/8 relative after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-3"></div>
            </label>
          </div>

          <div v-if="useCustomRounds" class="space-y-4 animate-in slide-in-from-top-2 duration-300">
            <input 
              type="range" v-model.number="customMaxRounds" min="10" :max="autoGeneratedRounds" step="5"
              class="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-white"
            />
            <div class="flex justify-between text-[8px] font-mono text-white/20">
              <span>10 РНД (БЫСТРО)</span>
              <span>АВТО_ЛИМИТ: {{ autoGeneratedRounds }} РНД</span>
            </div>
          </div>
          
          <p v-else class="text-[10px] text-white/60 font-medium animate-pulse cursor-pointer" @click="useCustomRounds = true">
            >> Рекомендуется ручное переопределение глубины для быстрого прототипирования.
          </p>
        </div>
        
        <div class="grid grid-cols-2 gap-4 w-full pt-4">
          <PitchyButton variant="secondary" @click="$emit('go-back')">Сбросить матрицу</PitchyButton>
          <PitchyButton variant="primary" @click="handleStartSimulation" shadow class="shadow-[0_0_20px_rgba(255,255,255,0.12)] shadow-white/20">
            Запустить симуляцию
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
                <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-white to-white/70 flex items-center justify-center text-white font-bold text-xl">
                  {{ selectedProfile.username?.charAt(0) }}
                </div>
                <div class="space-y-1">
                  <h4 class="text-xl font-bold text-white">{{ selectedProfile.username }}</h4>
                  <div class="flex items-center gap-2">
                    <span class="text-xs font-mono text-white/30">@{{ selectedProfile.name }}</span>
                    <span class="w-1 h-1 rounded-full bg-white/20"></span>
                    <span class="text-[10px] font-bold text-white uppercase">{{ selectedProfile.profession }}</span>
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
                  <span class="text-[10px] font-bold text-white/80 uppercase tracking-widest">Когнитивный бэкграунд</span>
                  <p class="text-xs text-white/60 leading-relaxed">{{ selectedProfile.persona }}</p>
                </div>

                <div v-if="selectedProfile.interested_topics?.length" class="space-y-3">
                   <span class="text-[10px] font-bold text-white/30 uppercase tracking-[0.2em]">Каналы архитектуры общества</span>
                   <div class="flex flex-wrap gap-2">
                     <span v-for="topic in selectedProfile.interested_topics" :key="topic" class="px-3 py-1.5 rounded-xl bg-white/5 border border-white/10 text-[10px] text-white/90 font-medium italic">
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

const startPolling = () => { pollStatus(); pollTimer = setInterval(pollStatus, 5000) }
const startProfilesPolling = () => { pollProfiles(); profilesTimer = setInterval(pollProfiles, 8000) }
const startConfigPolling = () => { pollConfig(); configTimer = setInterval(pollConfig, 8000) }

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
      if (task.status === 'completed' || task.status === 'ready') {
        stopAllTimers()
        phase.value = 4
        emit('update-status', 'completed')
        addLog('Общество агентов полностью активировано.')
      } else if (task.status === 'failed') {
        stopAllTimers()
        addLog(`Ошибка активации: ${task.error}`)
        emit('update-status', 'error')
      }
    }
  } catch (e) {
    console.error(e)
  }
}

const pollProfiles = async () => {
  try {
    const res = await getSimulationProfilesRealtime(props.simulationId)
    if (res.success && res.data.length > 0) {
      if (res.data.length > profiles.value.length) {
        addLog(`Новые агенты материализованы: ${res.data.length}/${expectedTotal.value || '?'}`)
      }
      profiles.value = res.data
    }
  } catch (e) {
    console.error(e)
  }
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
.shadow-glow-cyan-fx { filter: drop-shadow(0 0 10px rgba(6, 182, 212, 0.15)); }
</style>
