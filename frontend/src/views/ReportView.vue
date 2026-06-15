<template>
  <StageShell active-id="custdev">
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Header -->
      <header class="h-14 border-b border-white/5 flex items-center justify-between px-6 bg-pitchy-bg/50 backdrop-blur-md z-20">
        <div class="flex items-center gap-4">
          <button @click="router.push('/')" class="p-2 hover:bg-white/5 rounded-lg transition-colors text-white/40 hover:text-white">
            <HomeIcon class="w-4 h-4" />
          </button>
          <div class="h-4 w-px bg-white/10"></div>
          <div class="flex items-center gap-3">
            <span class="text-[10px] font-bold text-white/30 uppercase tracking-[0.2em]">Шаг 4/5</span>
            <span class="text-sm font-bold text-white tracking-tight">Вердикт: нужен ли рынку продукт</span>
          </div>
        </div>

        <div class="flex items-center gap-4">
          <div class="flex flex-col items-end">
            <span class="text-[10px] font-mono text-white/20 uppercase">{{ currentReportId?.slice(0, 8) }}</span>
            <StatusBadge :type="currentStatus === 'error' ? 'danger' : (currentStatus === 'completed' ? 'success' : 'primary')" :dot="currentStatus === 'processing'">
              {{ currentStatus === 'error' ? 'Ошибка синтеза' : (currentStatus === 'completed' ? 'Завершено' : 'Генерация') }}
            </StatusBadge>
          </div>
        </div>
      </header>

      <!-- Main -->
      <main class="flex-1 overflow-y-auto custom-scrollbar bg-pitchy-bg/30">
        <div class="p-6 lg:p-8 max-w-7xl mx-auto space-y-8">
          <!-- Баннер совмещённого вердикта -->
          <div class="rounded-2xl border border-white/10 bg-white/[0.02] p-5 flex items-start gap-4">
            <div class="w-10 h-10 rounded-xl shrink-0 flex items-center justify-center bg-white/10 text-white border border-white/15">
              <ScaleIcon class="w-5 h-5" />
            </div>
            <div class="space-y-1">
              <h2 class="text-lg font-semibold text-white">Честный вердикт по двум источникам</h2>
              <p class="text-sm text-white/55 leading-relaxed">
                Слева — <span class="text-white/80">сигналы рынка</span> из реальных сообществ (Хабр, vc.ru, Пикабу). Справа — <span class="text-white/80">симуляция общества</span> ИИ-агентов. Совпадение источников усиливает вывод, расхождение — повод копать глубже, прежде чем строить продукт.
              </p>
            </div>
          </div>

          <!-- Два блока: Сигналы vs Симуляция -->
          <div class="grid grid-cols-1 lg:grid-cols-5 gap-8 items-start">
            <!-- Сигналы рынка -->
            <section class="lg:col-span-2 rounded-2xl border border-white/10 bg-white/[0.02] p-6 space-y-5">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2 text-white/40 text-[10px] font-bold uppercase tracking-[0.2em]">
                  <RadarIcon class="w-3.5 h-3.5" /> Сигналы рынка
                </div>
                <span v-if="signalsLoading" class="text-[10px] text-white flex items-center gap-1.5">
                  <LoaderIcon class="w-3 h-3 animate-spin" /> сканирую…
                </span>
                <button v-else @click="loadSignals" class="text-white/30 hover:text-white transition-colors" title="Пересканировать">
                  <RefreshIcon class="w-3.5 h-3.5" />
                </button>
              </div>

              <!-- Загрузка -->
              <div v-if="signalsLoading && !signals.length" class="space-y-2.5">
                <div v-for="n in 3" :key="n" class="h-16 rounded-xl bg-white/[0.03] border border-white/8 animate-pulse"></div>
              </div>

              <!-- Реальные источники -->
              <div v-else-if="signals.length" class="space-y-2.5">
                <a
                  v-for="(s, i) in signals"
                  :key="i"
                  :href="s.url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="block rounded-xl bg-white/[0.03] border border-white/8 p-3 hover:border-white/25 transition-colors"
                >
                  <div class="flex items-center gap-2 mb-1.5">
                    <span class="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-white/80 font-mono">{{ s.domain || 'web' }}</span>
                    <span class="text-[12px] font-bold text-white truncate">{{ s.title }}</span>
                  </div>
                  <ul v-if="s.highlights && s.highlights.length" class="space-y-1">
                    <li v-for="(h, hi) in s.highlights.slice(0, 2)" :key="hi" class="text-[11px] italic text-white/55 border-l-2 border-white/20 pl-2">«{{ h }}»</li>
                  </ul>
                </a>
              </div>

              <!-- Ключ не задан (gated) -->
              <div v-else-if="signalsReady && !signalsAvailable" class="rounded-xl border border-dashed border-white/12 p-5 text-center space-y-3">
                <div class="w-10 h-10 rounded-xl mx-auto flex items-center justify-center bg-white/5 border border-white/10 text-white/40">
                  <PlugZapIcon class="w-5 h-5" />
                </div>
                <p class="text-sm text-white/60 leading-relaxed">Поиск сигналов отключён — не задан <code class="text-white/70">EXA_API_KEY</code> на сервере CustDev.</p>
                <div class="flex flex-wrap justify-center gap-2 pt-1">
                  <span v-for="src in signalSources" :key="src" class="text-[11px] px-2.5 py-1 rounded-full bg-white/[0.04] text-white/45 border border-white/8">{{ src }}</span>
                </div>
              </div>

              <!-- Пусто -->
              <div v-else-if="signalsReady" class="text-white/30 text-sm py-6 text-center border border-white/5 rounded-2xl">
                По этой гипотезе сигналов в сообществах не нашлось.
              </div>

              <p class="text-[11px] text-white/30 leading-relaxed">
                Реальные обсуждения боли из {{ signalSources.join(', ') }} — отдельно от симуляции, чтобы вердикт опирался на данные, а не только на модель.
              </p>
            </section>

            <!-- Симуляция общества -->
            <section class="lg:col-span-3 rounded-2xl border border-white/10 bg-white/[0.02] p-6 space-y-5">
              <div class="flex items-center gap-2 text-white/40 text-[10px] font-bold uppercase tracking-[0.2em]">
                <UsersIcon class="w-3.5 h-3.5" /> Симуляция общества
              </div>
              <Step4Report
                :reportId="currentReportId"
                :simulationId="simulationId"
                :projectData="projectData"
                :systemLogs="systemLogs"
                @add-log="addLog"
                @update-status="updateStatus"
              />
            </section>
          </div>
        </div>
      </main>
    </div>
  </StageShell>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import StageShell from '../components/layout/StageShell.vue'
import Step4Report from '../components/Step4Report.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import {
  Home as HomeIcon,
  Scale as ScaleIcon,
  Radar as RadarIcon,
  Users as UsersIcon,
  PlugZap as PlugZapIcon,
  Loader as LoaderIcon,
  RefreshCw as RefreshIcon,
} from 'lucide-vue-next'
import { getProject } from '../api/graph'
import { getSimulation } from '../api/simulation'
import { getReport } from '../api/report'
import { scanSignals } from '../api/signals'

const route = useRoute()
const router = useRouter()

const props = defineProps({
  reportId: String
})

// Состояние
const currentStatus = ref('processing')
const currentReportId = ref(route.params.reportId)
const simulationId = ref(null)
const projectData = ref(null)
const systemLogs = ref([])

// Источники сигналов (RU-сегмент).
const signalSources = ['Хабр', 'vc.ru', 'Пикабу']
const signals = ref([])
const signalsLoading = ref(false)
const signalsReady = ref(false)
const signalsAvailable = ref(false)

// Запрос для pain-mining: цель/гипотеза проекта.
const signalQuery = () =>
  (projectData.value?.simulation_requirement || projectData.value?.name || '').trim()

const loadSignals = async () => {
  const q = signalQuery()
  if (!q || signalsLoading.value) return
  signalsLoading.value = true
  try {
    const res = await scanSignals({ query: q })
    if (res.success && res.data) {
      signals.value = res.data.sources || []
      signalsAvailable.value = !!res.data.available
    }
  } catch (e) {
    addLog(`Сигналы недоступны: ${e.message}`)
  } finally {
    signalsLoading.value = false
    signalsReady.value = true
  }
}

const addLog = (msg) => {
  const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
  systemLogs.value.unshift({ time, msg })
  if (systemLogs.value.length > 200) systemLogs.value.pop()
}

const updateStatus = (status) => {
  currentStatus.value = status
}

const loadReportData = async () => {
  try {
    addLog(`Расшифровка вердикта: ${currentReportId.value}`)
    const reportRes = await getReport(currentReportId.value)
    if (reportRes.success && reportRes.data) {
      simulationId.value = reportRes.data.simulation_id
      if (simulationId.value) {
        const simRes = await getSimulation(simulationId.value)
        if (simRes.success && simRes.data?.project_id) {
          const projRes = await getProject(simRes.data.project_id)
          if (projRes.success && projRes.data) {
            projectData.value = projRes.data
            loadSignals() // pain-mining реальных сигналов по гипотезе проекта
          }
        }
      }
    }
  } catch (err) {
    addLog(`Ошибка расшифровки: ${err.message}`)
  }
}

watch(() => route.params.reportId, (newId) => {
  if (newId && newId !== currentReportId.value) {
    currentReportId.value = newId
    loadReportData()
  }
}, { immediate: true })

onMounted(() => {
  addLog('Панель вердикта манифестирована.')
  loadReportData()
})
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.05); border-radius: 10px; }
</style>
