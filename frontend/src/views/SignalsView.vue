<template>
  <StageShell active-id="custdev">
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Header -->
      <header class="min-h-14 border-b border-white/5 flex flex-wrap items-center justify-between gap-2 px-3 py-2 sm:px-6 bg-pitchy-bg/50 backdrop-blur-md z-20">
        <div class="flex items-center gap-2 sm:gap-4 min-w-0">
          <button @click="router.push('/')" class="p-2 hover:bg-white/5 rounded-lg transition-colors text-white/40 hover:text-white">
            <ArrowLeftIcon class="w-4 h-4" />
          </button>
          <div class="h-4 w-px bg-white/10"></div>
          <div class="flex items-center gap-2 min-w-0">
            <span class="text-[10px] font-bold text-white/30 uppercase tracking-[0.2em]">Шаг 2/5</span>
            <span class="text-sm font-bold text-white tracking-tight truncate">Сигналы рынка</span>
          </div>
        </div>
        <div class="flex items-center gap-2 text-[10px] sm:text-[11px] text-white/40 bg-white/5 px-2 sm:px-3 py-1.5 rounded-lg shrink-0">
          <RadarIcon class="w-3.5 h-3.5" :class="done ? 'text-white/40' : 'text-white animate-pulse'" />
          {{ totalSources }} источников<template v-if="!done"> · {{ elapsedText }}</template>
        </div>
      </header>

      <main class="flex-1 overflow-y-auto custom-scrollbar bg-pitchy-bg/30">
        <div class="p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto space-y-8">

          <!-- Нет контекста -->
          <div v-if="!query" class="py-16 text-center text-white/40">
            Нет гипотезы для разведки. Вернитесь на главную и опишите гипотезу.
          </div>

          <!-- ФАЗА 1 — живой процесс -->
          <template v-else-if="!done">
            <div v-if="errorMessage" class="rounded-2xl border border-red-400/25 bg-red-500/10 px-4 py-3 text-sm text-red-200 flex items-center justify-between gap-3">
              <span>{{ errorMessage }}</span>
              <button @click="startResearch" class="text-xs underline hover:text-white">Повторить</button>
            </div>
            <div class="flex items-center gap-3">
              <LoaderIcon class="w-5 h-5 animate-spin text-white/70" />
              <div>
                <div class="text-lg font-semibold text-white">Разведка спроса идёт…</div>
                <div class="text-sm text-white/45">Рой агентов сканит сообщества по твоей гипотезе</div>
              </div>
            </div>

            <div class="space-y-2.5">
              <div v-for="a in agents" :key="a.id" class="rounded-2xl border border-white/10 bg-white/[0.02] p-4 flex items-center gap-4">
                <div class="w-9 h-9 rounded-xl shrink-0 flex items-center justify-center border"
                     :class="a.done ? 'bg-white/[0.06] border-white/15 text-white' : 'bg-white/[0.03] border-white/10 text-white/40'">
                  <CheckIcon v-if="a.done" class="w-4 h-4" />
                  <LoaderIcon v-else-if="a.status === 'searching'" class="w-4 h-4 animate-spin" />
                  <ClockIcon v-else class="w-4 h-4" />
                </div>
                <div class="min-w-0 flex-1">
                  <div class="text-sm font-bold text-white truncate">{{ a.name }}</div>
                  <div class="text-[12px] text-white/40 truncate">
                    <template v-if="a.done">Готово</template>
                    <template v-else-if="a.status === 'searching'">Ищу сигналы…</template>
                    <template v-else>В очереди</template>
                  </div>
                </div>
                <div v-if="a.sources" class="text-[12px] font-mono text-white/55 shrink-0">+{{ a.sources }}</div>
              </div>
            </div>
          </template>

          <!-- ФАЗА 2 — дашборд -->
          <template v-else>
            <!-- Метрики -->
            <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <div class="rounded-2xl bg-white/[0.03] border border-white/8 p-4">
                <div class="text-[11px] uppercase tracking-wide text-white/40">Источников</div>
                <div class="text-2xl font-bold text-white mt-1">{{ result.sources_count }}</div>
              </div>
              <div class="rounded-2xl bg-white/[0.03] border border-white/8 p-4">
                <div class="text-[11px] uppercase tracking-wide text-white/40">Горячих сегментов</div>
                <div class="text-2xl font-bold text-white mt-1">{{ hotCount }} / {{ segs.length || '—' }}</div>
              </div>
              <div class="rounded-2xl bg-white/[0.03] border border-white/8 p-4">
                <div class="text-[11px] uppercase tracking-wide text-white/40">Готовы платить</div>
                <div class="text-2xl font-bold mt-1" :class="payPct >= 5 ? 'text-emerald-400' : 'text-white'">{{ payPct }}%</div>
              </div>
              <div class="rounded-2xl bg-white/[0.03] border border-white/8 p-4">
                <div class="text-[11px] uppercase tracking-wide text-white/40">Спрос-вердикт</div>
                <div class="text-2xl font-bold mt-1" :class="verdictClass">{{ analysis.verdict || '—' }}</div>
              </div>
            </div>

            <p v-if="analysis.summary" class="text-sm text-white/65 leading-relaxed border-l-2 border-white/15 pl-4">{{ analysis.summary }}</p>

            <!-- Сегменты + источники -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <section class="rounded-2xl border border-white/10 bg-white/[0.02] p-5 space-y-4">
                <div class="text-white/40 text-[10px] font-bold uppercase tracking-[0.2em]">Спрос по сегментам</div>
                <div v-if="segs.length" class="space-y-3">
                  <div v-for="(s, i) in segs" :key="i">
                    <div class="flex items-center justify-between mb-1.5">
                      <span class="text-sm text-white flex items-center gap-2">
                        <component :is="tempIcon(s.temperature)" class="w-4 h-4" :class="tempColor(s.temperature)" />
                        {{ s.name }}
                      </span>
                      <span class="text-[12px] text-white/45">{{ tempLabel(s.temperature) }} · {{ s.pain_count || 0 }}</span>
                    </div>
                    <div class="h-2 rounded-full bg-white/[0.06] overflow-hidden">
                      <div class="h-full rounded-full" :class="tempBar(s.temperature)" :style="{ width: barW(s.pain_count) }"></div>
                    </div>
                  </div>
                </div>
                <div v-else class="text-white/30 text-sm py-4 text-center">Сегменты не выделены</div>
              </section>

              <section class="rounded-2xl border border-white/10 bg-white/[0.02] p-5 space-y-4">
                <div class="text-white/40 text-[10px] font-bold uppercase tracking-[0.2em]">Источники по площадкам</div>
                <div class="space-y-2.5">
                  <div v-for="(p, i) in result.sources_by_platform" :key="i" class="flex items-center gap-3">
                    <span class="text-[12px] text-white/55 w-32 truncate font-mono">{{ p.platform }}</span>
                    <div class="flex-1 h-2 rounded-full bg-white/[0.06] overflow-hidden">
                      <div class="h-full rounded-full bg-white/45" :style="{ width: p.percent + '%' }"></div>
                    </div>
                    <span class="text-[12px] text-white/45 w-10 text-right">{{ p.percent }}%</span>
                  </div>
                </div>
              </section>
            </div>

            <!-- Воронка готовности -->
            <section v-if="analysis.willingness" class="rounded-2xl border border-white/10 bg-white/[0.02] p-5 space-y-4">
              <div class="text-white/40 text-[10px] font-bold uppercase tracking-[0.2em]">Спрос ≠ жалобы — воронка готовности</div>
              <div class="space-y-2.5">
                <div v-for="row in funnel" :key="row.key" class="flex items-center gap-3">
                  <span class="text-[13px] w-32" :class="row.key === 'paying' ? 'text-emerald-400' : 'text-white/55'">{{ row.label }}</span>
                  <div class="flex-1 h-5 rounded bg-white/[0.06] overflow-hidden">
                    <div class="h-full rounded" :class="row.bar" :style="{ width: funnelW(row.value) }"></div>
                  </div>
                  <span class="text-[13px] text-white/55 w-10 text-right">{{ row.value }}</span>
                </div>
              </div>
            </section>

            <!-- Топ болей + конкуренты -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <section class="rounded-2xl border border-white/10 bg-white/[0.02] p-5 space-y-3">
                <div class="text-white/40 text-[10px] font-bold uppercase tracking-[0.2em]">Топ болей</div>
                <div v-if="analysis.top_pains && analysis.top_pains.length" class="space-y-2.5">
                  <div v-for="(p, i) in analysis.top_pains" :key="i" class="flex items-start justify-between gap-3">
                    <span class="text-[13px] text-white/80 leading-snug">{{ p.text }}</span>
                    <span class="text-[12px] font-mono shrink-0" :class="p.tag === 'pay' ? 'text-emerald-400' : 'text-orange-300'">{{ p.count }}</span>
                  </div>
                </div>
                <div v-else class="text-white/30 text-sm py-2">Боли не выделены</div>
              </section>

              <section class="rounded-2xl border border-white/10 bg-white/[0.02] p-5 space-y-3">
                <div class="text-white/40 text-[10px] font-bold uppercase tracking-[0.2em]">Конкуренты</div>
                <div v-if="analysis.competitors && analysis.competitors.length" class="space-y-2.5">
                  <div v-for="(c, i) in analysis.competitors" :key="i" class="text-[13px]">
                    <span class="text-white font-medium">{{ c.name }}</span>
                    <span class="text-white/40"> · слаб: {{ c.weakness }}</span>
                  </div>
                </div>
                <div v-else class="text-white/30 text-sm py-2">Конкуренты не выделены</div>
              </section>
            </div>

            <!-- Лента реальных голосов -->
            <section class="rounded-2xl border border-white/10 bg-white/[0.02] p-5 space-y-3">
              <div class="text-white/40 text-[10px] font-bold uppercase tracking-[0.2em]">Реальные голоса ({{ result.sources_count }})</div>
              <div class="space-y-2.5 max-h-[420px] overflow-y-auto custom-scrollbar pr-1">
                <a v-for="(s, i) in feed" :key="i" :href="s.url" target="_blank" rel="noopener noreferrer"
                   class="block rounded-xl bg-white/[0.03] border border-white/8 p-3 hover:border-white/25 transition-colors">
                  <div class="flex items-center gap-2 mb-1.5">
                    <span class="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-white/70 font-mono">{{ s.domain || 'web' }}</span>
                    <span class="text-[12px] font-bold text-white truncate">{{ s.title }}</span>
                  </div>
                  <p v-if="s.highlights && s.highlights.length" class="text-[12px] italic text-white/55 leading-relaxed">«{{ s.highlights[0] }}»</p>
                </a>
              </div>
            </section>

            <div v-if="!readonly" class="flex items-center justify-between pt-2">
              <button @click="rerun" class="text-[12px] text-white/40 hover:text-white flex items-center gap-1.5">
                <RefreshIcon class="w-3.5 h-3.5" /> Пересканировать
              </button>
              <button @click="goNext" class="bg-white text-black rounded-full px-6 py-3 text-sm font-bold inline-flex items-center gap-2 shadow-[0_0_30px_rgba(255,255,255,0.1)]">
                К фокус-группе <ArrowRightIcon class="w-4 h-4" />
              </button>
            </div>
            <div v-else class="flex justify-end pt-2">
              <button @click="router.push('/')" class="rounded-full border border-white/15 px-6 py-3 text-sm hover:bg-white/10 inline-flex items-center gap-2">
                <ArrowLeftIcon class="w-4 h-4" /> К истории прогонов
              </button>
            </div>
          </template>
        </div>
      </main>
    </div>
  </StageShell>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import StageShell from '../components/layout/StageShell.vue'
import {
  ArrowLeft as ArrowLeftIcon, ArrowRight as ArrowRightIcon, Radar as RadarIcon,
  Loader as LoaderIcon, Check as CheckIcon, Clock as ClockIcon, RefreshCw as RefreshIcon,
  Flame as FlameIcon, Thermometer as ThermoIcon, Snowflake as SnowIcon,
} from 'lucide-vue-next'
import { getPendingUpload, setSignalsResult } from '../store/pendingUpload'
import { startSignalsResearch, getSignalsResearchStatus, getSavedSignals } from '../api/signals'

const router = useRouter()
const route = useRoute()
// Read-only просмотр сигналов прошлого прогона из истории (?sim=<simulation_id>).
const savedSim = route.query.sim || null
const readonly = ref(!!savedSim)
const pending = getPendingUpload()
const query = ref(pending.signalQuery || pending.simulationRequirement || '')
const segs = ref(pending.segments || [])

const agents = ref([])
const totalSources = ref(0)
const elapsed = ref(0)
const done = ref(false)
const errorMessage = ref('')
const result = ref({ sources_count: 0, sources: [], sources_by_platform: [], analysis: {} })
let timer = null
let taskId = null

const analysis = computed(() => result.value.analysis || {})
const elapsedText = computed(() => {
  const m = Math.floor(elapsed.value / 60), s = elapsed.value % 60
  return m > 0 ? `${m}м ${s}с` : `${s}с`
})

// --- дашборд computed ---
const segments = computed(() => analysis.value.segments || [])
const hotCount = computed(() => segments.value.filter(s => s.temperature === 'hot').length)
const payPct = computed(() => {
  const w = analysis.value.willingness
  if (!w) return 0
  // Это воронка, а не три независимые группы: доля платящих считается
  // относительно тех, кто явно жалуется на проблему.
  return w.complaining ? Math.min(100, Math.round((w.paying || 0) * 100 / w.complaining)) : 0
})
const verdictClass = computed(() => {
  const v = (analysis.value.verdict || '').toLowerCase()
  if (v.includes('есть')) return 'text-emerald-400'
  if (v.includes('слаб')) return 'text-amber-300'
  if (v.includes('нет')) return 'text-red-400'
  return 'text-white'
})
const maxPain = computed(() => Math.max(1, ...segments.value.map(s => s.pain_count || 0)))
const barW = (v) => `${Math.round((v || 0) * 100 / maxPain.value)}%`

const funnel = computed(() => {
  const w = analysis.value.willingness || {}
  return [
    { key: 'complaining', label: 'Жалуются', value: w.complaining || 0, bar: 'bg-white/30' },
    { key: 'seeking', label: 'Ищут решение', value: w.seeking || 0, bar: 'bg-amber-300/70' },
    { key: 'paying', label: 'Готовы платить', value: w.paying || 0, bar: 'bg-emerald-400/80' },
  ]
})
const funnelMax = computed(() => Math.max(1, ...funnel.value.map(r => r.value)))
const funnelW = (v) => `${Math.round((v || 0) * 100 / funnelMax.value)}%`

const feed = computed(() => (result.value.sources || []).filter(s => s.highlights && s.highlights.length).slice(0, 40))

const tempIcon = (t) => (t === 'hot' ? FlameIcon : t === 'warm' ? ThermoIcon : SnowIcon)
const tempColor = (t) => (t === 'hot' ? 'text-orange-400' : t === 'warm' ? 'text-amber-300' : 'text-sky-400')
const tempBar = (t) => (t === 'hot' ? 'bg-orange-400/70' : t === 'warm' ? 'bg-amber-300/60' : 'bg-sky-400/50')
const tempLabel = (t) => (t === 'hot' ? 'Горит' : t === 'warm' ? 'Тепло' : 'Холодно')

// --- логика опроса ---
const applyStatus = (task) => {
  const d = task.progress_detail || {}
  agents.value = d.agents || agents.value
  totalSources.value = d.total_sources ?? totalSources.value
  elapsed.value = d.elapsed ?? elapsed.value
  if (task.status === 'completed' && task.result) {
    result.value = task.result
    totalSources.value = task.result.sources_count || totalSources.value
    done.value = true
    // Сохраняем итог разведки, чтобы прикрепить его к прогону (доступ из истории).
    setSignalsResult(task.result)
    stopPoll()
  } else if (task.status === 'failed') {
    errorMessage.value = task.error || 'Разведка не завершилась. Попробуйте повторить.'
    stopPoll()
  }
}

const poll = async () => {
  if (!taskId) return
  try {
    const res = await getSignalsResearchStatus(taskId)
    if (res.success && res.data) applyStatus(res.data)
  } catch (e) { /* мягко игнорируем сетевые сбои опроса */ }
}

const stopPoll = () => { if (timer) { clearInterval(timer); timer = null } }

const startResearch = async () => {
  if (!query.value) return
  done.value = false
  errorMessage.value = ''
  try {
    const res = await startSignalsResearch({ query: query.value, segments: segs.value })
    if (res.success && res.data?.task_id) {
      taskId = res.data.task_id
      poll()
      timer = setInterval(poll, 2500)
    }
  } catch (e) {
    errorMessage.value = e?.response?.data?.error || e?.message || 'Не удалось запустить разведку.'
  }
}

const rerun = () => { result.value = { sources_count: 0, sources: [], sources_by_platform: [], analysis: {} }; agents.value = []; totalSources.value = 0; startResearch() }
const goNext = () => router.push({ name: 'Process', params: { projectId: 'new' } })

// Read-only: грузим сохранённые сигналы прогона (без повторной разведки).
const loadSaved = async () => {
  try {
    const res = await getSavedSignals(savedSim)
    if (res.success && res.data) {
      result.value = res.data
      totalSources.value = res.data.sources_count || 0
      query.value = '(сохранённый прогон)'
      done.value = true
    } else {
      query.value = ''
    }
  } catch (e) {
    query.value = ''
  }
}

onMounted(() => { readonly.value ? loadSaved() : startResearch() })
onUnmounted(stopPoll)
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.06); border-radius: 10px; }
</style>
