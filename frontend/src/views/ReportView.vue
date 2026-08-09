<template>
  <StageShell active-id="custdev">
    <div class="flex-1 flex flex-col overflow-hidden">
      <header class="min-h-14 border-b border-white/5 flex items-center justify-between gap-2 px-3 py-2 sm:px-6 bg-pitchy-bg/50 backdrop-blur-md z-20">
        <div class="flex items-center gap-2 sm:gap-4 min-w-0">
          <button @click="router.push('/')" class="p-2 hover:bg-white/5 rounded-lg transition-colors text-white/40 hover:text-white">
            <HomeIcon class="w-4 h-4" />
          </button>
          <div class="h-4 w-px bg-white/10"></div>
          <div class="flex items-center gap-2 min-w-0">
            <span class="text-[10px] font-bold text-white/30 uppercase tracking-[0.2em]">Шаг 4/5 · итог</span>
            <span class="text-sm font-bold text-white tracking-tight truncate">Вердикт: нужен ли рынку продукт</span>
          </div>
        </div>
        <button v-if="!loading" @click="loadVerdict" class="text-white/30 hover:text-white transition-colors" title="Пересобрать отчёт">
          <RefreshIcon class="w-4 h-4" />
        </button>
      </header>

      <main class="flex-1 overflow-y-auto custom-scrollbar bg-pitchy-bg/30">
        <div class="p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto space-y-8">

          <!-- Загрузка -->
          <div v-if="loading" class="py-20 text-center space-y-4">
            <LoaderIcon class="w-7 h-7 animate-spin text-white/60 mx-auto" />
            <div class="text-white/55">Сводим сигналы рынка и симуляцию общества в вердикт…</div>
          </div>

          <template v-else>
            <!-- Верхний вердикт -->
            <div class="rounded-2xl border border-white/15 bg-white/[0.03] p-4 sm:p-6 flex flex-col min-[420px]:flex-row items-start gap-4 sm:gap-5">
              <div class="w-14 h-14 rounded-2xl shrink-0 flex items-center justify-center border" :class="verdictBox">
                <component :is="verdictIcon" class="w-7 h-7" />
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-xl font-semibold text-white">{{ v.verdict || 'Недостаточно данных' }}</div>
                <p v-if="v.summary" class="text-sm text-white/60 leading-relaxed mt-1">{{ v.summary }}</p>
                <div v-if="v.confidence != null" class="flex items-center gap-3 mt-3 max-w-sm">
                  <span class="text-[12px] text-white/45">Уверенность</span>
                  <div class="flex-1 h-1.5 bg-white/[0.08] rounded-full overflow-hidden">
                    <div class="h-full rounded-full" :class="verdictBar" :style="{ width: (v.confidence || 0) + '%' }"></div>
                  </div>
                  <span class="text-[12px] text-white/70 font-medium">{{ v.confidence }}%</span>
                </div>
              </div>
            </div>

            <!-- Согласие двух опор -->
            <div class="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] gap-3 items-stretch">
              <section class="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
                <div class="flex items-center gap-2 text-white/40 text-[10px] font-bold uppercase tracking-[0.2em] mb-2"><RadarIcon class="w-3.5 h-3.5" /> Сигналы рынка</div>
                <p class="text-sm text-white/75 leading-relaxed">{{ v.signals_side || `${signalsCount} реальных источников` }}</p>
              </section>
              <div class="flex md:flex-col items-center justify-center">
                <span class="text-[11px] font-bold px-3 py-1 rounded-full border" :class="agreeClass">{{ agreeLabel }}</span>
              </div>
              <section class="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
                <div class="flex items-center gap-2 text-white/40 text-[10px] font-bold uppercase tracking-[0.2em] mb-2"><UsersIcon class="w-3.5 h-3.5" /> Симуляция общества</div>
                <p class="text-sm text-white/75 leading-relaxed">{{ v.simulation_side || (custdevCount ? `${custdevCount} ответов фокус-группы` : 'интервью не проводилось') }}</p>
              </section>
            </div>

            <!-- Доказательства -->
            <div v-if="v.evidence" class="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <div class="rounded-2xl bg-white/[0.03] border border-white/8 p-4">
                <div class="text-[11px] uppercase tracking-wide text-white/40">Готовы платить</div>
                <div class="text-2xl font-bold mt-1" :class="(v.evidence.pay_pct||0) >= 5 ? 'text-emerald-400' : 'text-white'">{{ v.evidence.pay_pct ?? '—' }}%</div>
              </div>
              <div class="rounded-2xl bg-white/[0.03] border border-white/8 p-4">
                <div class="text-[11px] uppercase tracking-wide text-white/40">Горячие сегменты</div>
                <div class="text-sm font-semibold text-white mt-2 leading-snug">{{ v.evidence.hot_segments || '—' }}</div>
              </div>
              <div class="rounded-2xl bg-white/[0.03] border border-white/8 p-4">
                <div class="text-[11px] uppercase tracking-wide text-white/40">Загорелось персон</div>
                <div class="text-sm font-semibold text-white mt-2 leading-snug">{{ v.evidence.hot_personas || '—' }}</div>
              </div>
              <div class="rounded-2xl bg-white/[0.03] border border-white/8 p-4">
                <div class="text-[11px] uppercase tracking-wide text-white/40">Главная боль</div>
                <div class="text-sm font-semibold text-white mt-2 leading-snug">{{ v.evidence.top_pain || '—' }}</div>
              </div>
            </div>

            <!-- Красные флаги + рекомендация -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <section v-if="v.red_flags && v.red_flags.length" class="rounded-2xl border border-red-500/20 bg-red-500/[0.04] p-5 space-y-2">
                <div class="flex items-center gap-2 text-red-300 text-[10px] font-bold uppercase tracking-[0.2em]"><AlertIcon class="w-3.5 h-3.5" /> Красные флаги</div>
                <div v-for="(f, i) in v.red_flags" :key="i" class="text-[13px] text-white/75 leading-relaxed">— {{ f }}</div>
              </section>
              <section v-if="v.recommendation" class="rounded-2xl border border-white/10 bg-white/[0.02] p-5 space-y-2">
                <div class="flex items-center gap-2 text-white/40 text-[10px] font-bold uppercase tracking-[0.2em]"><TargetIcon class="w-3.5 h-3.5" /> Что делать дальше</div>
                <p class="text-[13px] text-white/75 leading-relaxed">{{ v.recommendation }}</p>
              </section>
            </div>

            <!-- Сигналы рынка — подсвечены -->
            <section class="rounded-2xl border border-white/12 bg-white/[0.03] p-6 space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2 text-white text-sm font-semibold"><RadarIcon class="w-4 h-4" /> Сигналы рынка — реальные голоса</div>
                <span class="text-[11px] text-white/35">{{ signalsCount }} источников</span>
              </div>
              <div v-if="signalSources.length" class="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                <a v-for="(s, i) in signalSources" :key="i" :href="s.url" target="_blank" rel="noopener noreferrer"
                   class="block rounded-xl bg-white/[0.03] border border-white/8 p-3 hover:border-white/25 transition-colors">
                  <div class="flex items-center gap-2 mb-1.5">
                    <span class="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-white/70 font-mono">{{ s.domain || 'web' }}</span>
                    <span class="text-[12px] font-bold text-white truncate">{{ s.title }}</span>
                  </div>
                  <p v-if="s.highlights && s.highlights.length" class="text-[12px] italic text-white/55 leading-relaxed">«{{ s.highlights[0] }}»</p>
                </a>
              </div>
              <div v-else class="text-white/30 text-sm py-3">Сигналов не найдено (или EXA/ddg недоступны).</div>
            </section>

            <!-- Масштабный разбор (markdown) -->
            <section v-if="reportMarkdown" class="rounded-2xl border border-white/10 bg-white/[0.02] p-6">
              <div class="prose prose-invert prose-sm max-w-none custom-markdown" v-html="renderedReport"></div>
            </section>

            <!-- Полный отчёт агента-аналитика (опционально) -->
            <details class="rounded-2xl border border-white/10 bg-white/[0.02] overflow-hidden">
              <summary class="cursor-pointer px-5 py-3 text-sm font-medium text-white/70 hover:text-white select-none">Полный отчёт агента-аналитика</summary>
              <div class="px-5 pb-5 pt-1">
                <Step4Report
                  :reportId="currentReportId"
                  :simulationId="simulationId"
                  :projectData="projectData"
                  :systemLogs="systemLogs"
                  @add-log="addLog"
                  @update-status="() => {}"
                />
              </div>
            </details>
          </template>
        </div>
      </main>
    </div>
  </StageShell>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { marked } from 'marked'
import StageShell from '../components/layout/StageShell.vue'
import Step4Report from '../components/Step4Report.vue'
import {
  Home as HomeIcon, Radar as RadarIcon, Users as UsersIcon, Target as TargetIcon,
  Loader as LoaderIcon, RefreshCw as RefreshIcon, AlertTriangle as AlertIcon,
  Flame as FlameIcon, Thermometer as ThermoIcon, Snowflake as SnowIcon,
} from 'lucide-vue-next'
import { getProject } from '../api/graph'
import { getSimulation } from '../api/simulation'
import { getReport } from '../api/report'
import { generateVerdict } from '../api/verdict'

const route = useRoute()
const router = useRouter()
const props = defineProps({ reportId: String })

const currentReportId = ref(route.params.reportId)
const simulationId = ref(null)
const projectData = ref(null)
const systemLogs = ref([])

const loading = ref(true)
const v = ref({})            // структурный вердикт
const signals = ref({})      // результат скана сигналов
const custdevCount = ref(0)
const reportMarkdown = ref('')

const signalSources = computed(() => (signals.value?.sources || []).filter(s => s.highlights && s.highlights.length).slice(0, 12))
const signalsCount = computed(() => signals.value?.sources_count ?? signals.value?.sources?.length ?? 0)
const renderedReport = computed(() => reportMarkdown.value ? marked(reportMarkdown.value) : '')

const vtone = computed(() => {
  const s = (v.value?.verdict || '').toLowerCase()
  if (s.includes('нет')) return 'cold'
  if (s.includes('слаб')) return 'warm'
  if (s.includes('осторож')) return 'warm'
  if (s.includes('есть')) return 'hot'
  return 'neutral'
})
const verdictIcon = computed(() => vtone.value === 'hot' ? FlameIcon : vtone.value === 'cold' ? SnowIcon : ThermoIcon)
const verdictBox = computed(() => ({
  hot: 'bg-emerald-500/15 border-emerald-400/30 text-emerald-400',
  warm: 'bg-amber-500/15 border-amber-400/30 text-amber-300',
  cold: 'bg-red-500/15 border-red-400/30 text-red-400',
  neutral: 'bg-white/10 border-white/15 text-white',
}[vtone.value]))
const verdictBar = computed(() => ({
  hot: 'bg-emerald-400', warm: 'bg-amber-300', cold: 'bg-red-400', neutral: 'bg-white/50',
}[vtone.value]))

const agreeLabel = computed(() => {
  const a = (v.value?.agreement || '').toLowerCase()
  if (a.includes('согл')) return 'источники согласны'
  if (a.includes('расх')) return 'источники расходятся'
  if (a.includes('частич')) return 'частичное согласие'
  return 'две опоры'
})
const agreeClass = computed(() => {
  const a = (v.value?.agreement || '').toLowerCase()
  if (a.includes('согл')) return 'text-emerald-400 border-emerald-400/30 bg-emerald-500/10'
  if (a.includes('расх')) return 'text-red-400 border-red-400/30 bg-red-500/10'
  return 'text-white/60 border-white/15 bg-white/[0.04]'
})

const addLog = (msg) => { systemLogs.value.unshift({ time: new Date().toLocaleTimeString(), msg }); if (systemLogs.value.length > 200) systemLogs.value.pop() }

const loadVerdict = async () => {
  if (!simulationId.value) return
  loading.value = true
  try {
    const res = await generateVerdict({ simulation_id: simulationId.value, query: projectData.value?.simulation_requirement || projectData.value?.name || '' })
    if (res.success && res.data) {
      v.value = res.data.verdict || {}
      signals.value = res.data.signals || {}
      custdevCount.value = res.data.custdev_count || 0
      reportMarkdown.value = res.data.report_markdown || ''
    }
  } catch (e) {
    addLog(`Не удалось собрать вердикт: ${e.message}`)
  } finally {
    loading.value = false
  }
}

const loadReportData = async () => {
  try {
    const reportRes = await getReport(currentReportId.value)
    if (reportRes.success && reportRes.data) {
      simulationId.value = reportRes.data.simulation_id
      if (simulationId.value) {
        const simRes = await getSimulation(simulationId.value)
        if (simRes.success && simRes.data?.project_id) {
          const projRes = await getProject(simRes.data.project_id)
          if (projRes.success && projRes.data) projectData.value = projRes.data
        }
      }
    }
  } catch (e) { addLog(`Ошибка загрузки: ${e.message}`) }
  await loadVerdict()
}

loadReportData()
watch(() => route.params.reportId, (id) => { if (id && id !== currentReportId.value) { currentReportId.value = id; loadReportData() } })
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.05); border-radius: 10px; }
.custom-markdown :deep(h2) { font-size: 1.15rem; font-weight: 600; color: #fff; margin-top: 1.5rem; margin-bottom: 0.5rem; }
.custom-markdown :deep(h3) { font-size: 1rem; font-weight: 600; color: rgba(255,255,255,0.9); margin-top: 1rem; }
.custom-markdown :deep(p) { margin: 0.6rem 0; line-height: 1.7; color: rgba(255,255,255,0.7); }
.custom-markdown :deep(ul) { list-style: disc; padding-left: 1.4rem; margin: 0.6rem 0; color: rgba(255,255,255,0.7); }
.custom-markdown :deep(li) { margin: 0.3rem 0; }
.custom-markdown :deep(strong) { color: #fff; }
</style>
