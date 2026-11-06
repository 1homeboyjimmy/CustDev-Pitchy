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
            <span class="text-sm font-bold text-white tracking-tight truncate">Контекст продуктового исследования</span>
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
          <div v-if="readonly && !done" class="py-16 text-center text-white/40 space-y-4">
            <p>{{ errorMessage || 'Загружаем сохранённое исследование…' }}</p>
            <button v-if="errorMessage" @click="loadSaved" class="text-xs underline hover:text-white">Повторить загрузку</button>
          </div>
          <div v-else-if="!query" class="py-16 text-center text-white/40">
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
                <div class="text-lg font-semibold text-white">{{ progressMessage }}</div>
                <div class="text-sm text-white/45">Контекст, опыт и возражения для кастдев-интервью · обычно до 3 минут</div>
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
                    <template v-if="a.done">{{ a.status }}</template>
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
            <div v-if="result.market === 'russia'" class="rounded-2xl border border-white/10 bg-white/[0.02] p-4 text-sm text-white/60 space-y-2">
              <p>Российский контекст: {{ result.russian_market_sources || 0 }} источников · зарубежный опыт: {{ result.international_reference_sources || 0 }} · комментариев и ответов: {{ result.comments_count || 0 }}.</p>
              <p>Публичные материалы помогают подготовить синтетические интервью. Они не являются репрезентативным опросом общества.</p>
              <p v-if="result.unknown_scope_sources">География не установлена или смешана у {{ result.unknown_scope_sources }} источников.</p>
              <p v-if="result.extraction_unavailable_count">У {{ result.extraction_unavailable_count }} страниц не удалось извлечь проверяемые утверждения. Их содержание не используется как подтверждённый факт.</p>
              <p v-if="unavailableSearches.length">Поиск недоступен: {{ unavailableSearches.map(item => item.name || item.id).join(', ') }}. Отсутствие результатов здесь не означает отсутствие спроса.</p>
              <p v-if="result.unread_sources_count">Не удалось прочитать {{ result.unread_sources_count }} страниц. Они не включены в доказательства спроса.</p>
              <p v-if="!result.analysis_available">Аналитический вывод недоступен. Ниже показаны собранные материалы.</p>
            </div>
            <!-- Метрики -->
            <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <div class="rounded-2xl bg-white/[0.03] border border-white/8 p-4">
                <div class="text-[11px] uppercase tracking-wide text-white/40">Источников</div>
                <div class="text-2xl font-bold text-white mt-1">{{ result.sources_count }}</div>
              </div>
              <div class="rounded-2xl bg-white/[0.03] border border-white/8 p-4">
                <div class="text-[11px] uppercase tracking-wide text-white/40">{{ semanticResearch ? 'Групп для интервью' : 'Горячих сегментов' }}</div>
                <div class="text-2xl font-bold text-white mt-1">{{ semanticResearch ? analysis.affected_groups?.length || 0 : `${hotCount} / ${segments.length || '—'}` }}</div>
              </div>
              <div class="rounded-2xl bg-white/[0.03] border border-white/8 p-4">
                <div class="text-[11px] uppercase tracking-wide text-white/40">{{ semanticResearch ? 'Утверждений с цитатами' : 'Сигналы оплаты · РФ' }}</div>
                <div class="text-2xl font-bold mt-1 text-white">{{ semanticResearch ? result.claims_count || 0 : analysis.willingness?.paying ?? '—' }}</div>
              </div>
              <div class="rounded-2xl bg-white/[0.03] border border-white/8 p-4">
                <div class="text-[11px] uppercase tracking-wide text-white/40">{{ semanticResearch ? 'Вопросов для интервью' : 'Спрос-вердикт' }}</div>
                <div class="text-2xl font-bold mt-1" :class="verdictClass">{{ semanticResearch ? analysis.interview_questions?.length || 0 : analysis.verdict || '—' }}</div>
              </div>
            </div>

            <p v-if="analysis.summary" class="text-sm text-white/65 leading-relaxed border-l-2 border-white/15 pl-4"><span v-if="semanticResearch" class="block text-xs text-white/40 mb-1">Аналитическая сводка модели</span>{{ analysis.summary }}</p>
            <p v-if="semanticResearch && !result.claims_count" class="text-sm text-amber-200/70">Подтверждающие цитаты не извлечены. Выводы и гипотезы требуют дополнительной проверки.</p>

            <section v-if="semanticResearch" class="rounded-2xl border border-white/10 p-5 space-y-4">
              <h2 class="font-semibold text-white">Контекст для синтетических интервью</h2>
              <div v-for="(finding, i) in analysis.findings || []" :key="i" class="text-sm text-white/70 space-y-1">
                <p class="font-medium text-white">{{ finding.question }}</p>
                <p>{{ finding.conclusion }}</p>
                <span class="text-xs text-white/40">{{ findingStatus(finding.status) }}</span>
                <div v-for="id in finding.claim_ids || []" :key="id" class="border-l border-white/15 pl-3 mt-2">
                  <template v-if="claimById[id]">
                    <p class="text-xs italic">«{{ claimById[id].quote }}»</p>
                    <a :href="sourceLink(claimById[id].source_url)" target="_blank" rel="noopener noreferrer" class="text-xs underline">{{ locatorLabel(claimById[id].locator) }} · {{ evidenceLabel(claimById[id].evidence_type) }}</a>
                  </template>
                </div>
              </div>
              <div v-for="section in interviewSections" :key="section.key" class="space-y-2">
                <h3 class="text-sm font-medium text-white">{{ section.label }}</h3>
                <ul class="list-disc pl-5 text-sm text-white/60 space-y-1">
                  <li v-for="(item, i) in analysis[section.key] || []" :key="i">{{ item }}</li>
                </ul>
              </div>
              <p class="text-xs text-white/40">Гипотезы и предполагаемые риски требуют проверки. Ответы будущих синтетических респондентов не задаются заранее.</p>
            </section>

            <!-- Сегменты + источники -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <section v-if="!semanticResearch" class="rounded-2xl border border-white/10 bg-white/[0.02] p-5 space-y-4">
                <div class="text-white/40 text-[10px] font-bold uppercase tracking-[0.2em]">Спрос по сегментам</div>
                <div v-if="segments.length" class="space-y-3">
                  <div v-for="(s, i) in segments" :key="i">
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
            <section v-if="!semanticResearch && analysis.willingness" class="rounded-2xl border border-white/10 bg-white/[0.02] p-5 space-y-4">
              <div class="text-white/40 text-[10px] font-bold uppercase tracking-[0.2em]">Что подтверждают российские источники</div>
              <p class="text-xs text-white/40">Считаем страницы, а не людей. Один источник может подтверждать несколько наблюдений.</p>
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
            <div v-if="!semanticResearch" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <section class="rounded-2xl border border-white/10 bg-white/[0.02] p-5 space-y-3">
                <div class="text-white/40 text-[10px] font-bold uppercase tracking-[0.2em]">Топ болей</div>
                <div v-if="analysis.top_pains && analysis.top_pains.length" class="space-y-2.5">
                  <div v-for="(p, i) in analysis.top_pains" :key="i" class="flex items-start justify-between gap-3">
                    <div class="text-[13px] text-white/80 leading-snug">
                      <span>{{ p.text }}</span>
                      <div v-if="p.evidence?.length" class="mt-1 flex flex-wrap gap-2">
                        <a v-for="index in p.evidence" :key="index" :href="sourceLink(result.sources?.[index]?.url)" target="_blank" rel="noopener noreferrer" class="text-[11px] text-white/45 underline hover:text-white">Источник {{ index + 1 }}</a>
                      </div>
                    </div>
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
              <div class="text-white/40 text-[10px] font-bold uppercase tracking-[0.2em]">Прочитанные источники ({{ result.sources_count }})</div>
              <div class="space-y-2.5 max-h-[420px] overflow-y-auto custom-scrollbar pr-1">
                <div v-for="(s, i) in feed" :key="i" class="rounded-xl bg-white/[0.03] border border-white/8 p-3">
                  <a :href="sourceLink(s.url)" target="_blank" rel="noopener noreferrer" class="block hover:opacity-80">
                  <div class="flex items-center gap-2 mb-1.5">
                    <span class="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-white/70 font-mono">{{ s.domain || 'web' }}</span>
                    <span v-if="s.market_scope === 'international_reference'" class="text-[10px] text-amber-300 shrink-0">Зарубежный опыт</span>
                    <span class="text-[12px] font-bold text-white truncate">{{ s.title }}</span>
                  </div>
                  <p v-if="s.highlights && s.highlights.length" class="text-[12px] italic text-white/55 leading-relaxed">«{{ s.highlights[0] }}»</p>
                  </a>
                  <details v-if="s.claims?.length" class="mt-2 border-t border-white/10 pt-2 space-y-2">
                    <summary class="text-xs cursor-pointer text-white/60">Утверждения и ограничения · {{ s.claims.length }}</summary>
                    <p v-if="s.extraction_excerpted || s.content_truncated" class="text-xs text-amber-200/70">Проанализированы фрагменты материала. Условия и контекст могут быть неполными.</p>
                    <div v-for="claim in s.claims" :key="claim.id" class="text-xs text-white/60 space-y-1 py-2">
                      <p class="text-white/80">{{ claim.statement }}</p>
                      <p class="italic">«{{ claim.quote }}»</p>
                      <p>{{ evidenceLabel(claim.evidence_type) }} · {{ locatorLabel(claim.locator) }}</p>
                      <p v-if="claim.limitations">Ограничение: {{ claim.limitations }}</p>
                    </div>
                  </details>
                  <details v-if="s.comments?.length" class="mt-2 space-y-2 border-t border-white/10 pt-2">
                    <summary class="text-[11px] text-white/50 cursor-pointer">Комментарии и ответы · {{ s.comments.length }}<span v-if="s.discussion_status === 'partial'"> · часть обсуждения</span></summary>
                    <a v-for="(comment, ci) in s.comments" :key="ci" :href="sourceLink(comment.url) || sourceLink(s.url)" target="_blank" rel="noopener noreferrer" class="block text-[12px] text-white/55 leading-relaxed hover:text-white">«{{ comment.text }}»</a>
                  </details>
                </div>
              </div>
            </section>

            <details v-if="unreadSources.length" class="rounded-2xl border border-white/10 p-4 text-sm text-white/60">
              <summary class="cursor-pointer">Непрочитанные страницы · {{ unreadSources.length }}</summary>
              <div v-for="(source, i) in unreadSources" :key="i" class="mt-3 flex flex-wrap justify-between gap-2 text-xs">
                <a :href="sourceLink(source.url)" target="_blank" rel="noopener noreferrer" class="break-all hover:text-white">{{ source.title || source.url }}</a>
                <span>{{ unreadReason(source.crawl_status) }}</span>
              </div>
            </details>
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
import { sourceLink, unreadReason, searchProblems, locatorLabel } from '../utils/marketEvidence'
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
const progressMessage = ref('Исследование контекста идёт…')
const result = ref({ sources_count: 0, sources: [], sources_by_platform: [], analysis: {} })
let timer = null
let taskId = null
let elapsedTimer = null
let requestId = null
let generation = 0
let disposed = false
let consecutivePollErrors = 0

const unavailableSearches = computed(() => searchProblems(result.value.search_status))
const unreadSources = computed(() => (result.value.discovered_sources || []).filter(item => item.crawl_status !== 'fetched'))
const analysis = computed(() => result.value.analysis || {})
const semanticResearch = computed(() => result.value.evidence_version === 2)
const claimById = computed(() => Object.fromEntries((result.value.sources || []).flatMap(s => (s.claims || []).map(c => [c.id, c]))))
const interviewSections = [
  { key: 'affected_groups', label: 'Затронутые группы' },
  { key: 'interview_questions', label: 'Вопросы для интервью' },
  { key: 'interview_hypotheses', label: 'Гипотезы для проверки' },
  { key: 'risks', label: 'Предполагаемые риски' },
  { key: 'gaps', label: 'Чего пока не знаем' },
]
function findingStatus(value) { return ({ supported: 'Есть подтверждающая цитата', conditional: 'Есть условия и ограничения', gap: 'Недостаточно данных', conflicting: 'Противоречивые свидетельства' })[value] || 'Недостаточно данных' }
function evidenceLabel(value) { return ({ observation: 'Наблюдение', self_report: 'Со слов участника', vendor_statement: 'Заявление поставщика', calculation: 'Расчёт', assumption: 'Допущение', synthetic: 'Синтетический пример' })[value] || 'Тип не установлен' }
const elapsedText = computed(() => {
  const m = Math.floor(elapsed.value / 60), s = elapsed.value % 60
  return m > 0 ? `${m}м ${s}с` : `${s}с`
})

// --- дашборд computed ---
const segments = computed(() => Array.isArray(analysis.value.segments) ? analysis.value.segments.filter(item => item && typeof item === 'object') : [])
const hotCount = computed(() => segments.value.filter(s => s.temperature === 'hot').length)
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

const feed = computed(() => (result.value.sources || []).filter(s => s.highlights && s.highlights.length))

const tempIcon = (t) => (t === 'hot' ? FlameIcon : t === 'warm' ? ThermoIcon : SnowIcon)
const tempColor = (t) => (t === 'hot' ? 'text-orange-400' : t === 'warm' ? 'text-amber-300' : 'text-sky-400')
const tempBar = (t) => (t === 'hot' ? 'bg-orange-400/70' : t === 'warm' ? 'bg-amber-300/60' : 'bg-sky-400/50')
const tempLabel = (t) => (t === 'hot' ? 'Горит' : t === 'warm' ? 'Тепло' : t === 'cold' ? 'Холодно' : 'Недостаточно данных')

// Poll serially, discard stale responses, and stop all timers on navigation.
const stopPoll = () => {
  clearTimeout(timer)
  clearInterval(elapsedTimer)
  timer = null
  elapsedTimer = null
}
const applyStatus = (task) => {
  progressMessage.value = task.message || 'Исследование контекста идёт…'
  const d = task.progress_detail || {}
  agents.value = d.agents || agents.value
  totalSources.value = d.total_sources ?? totalSources.value
  elapsed.value = Math.max(elapsed.value, d.elapsed || 0)
  if (task.status === 'completed' && task.result) {
    result.value = task.result
    totalSources.value = task.result.sources_count ?? 0
    done.value = true
    setSignalsResult(task.result)
    stopPoll()
  } else if (task.status === 'failed') {
    errorMessage.value = 'Исследование не завершилось. Можно повторить запуск.'
    requestId = null
    stopPoll()
  }
}
const poll = async (token) => {
  if (!taskId || token !== generation || disposed) return
  try {
    const res = await getSignalsResearchStatus(taskId)
    if (token !== generation || disposed) return
    if (res.success && res.data) {
      errorMessage.value = ''
      consecutivePollErrors = 0
      applyStatus(res.data)
    }
  } catch (error) {
    if (token !== generation || disposed) return
    errorMessage.value = 'Не удалось получить статус. Повторяем запрос…'
    if (++consecutivePollErrors >= 5) {
      errorMessage.value = 'Связь с исследованием потеряна. Нажмите «Повторить», чтобы получить результат той же задачи.'
      stopPoll()
      return
    }
    if ([401, 403, 404].includes(error?.response?.status)) {
      errorMessage.value = 'Задача недоступна. Проверьте вход и повторите запуск.'
      taskId = null
      stopPoll()
      return
    }
  }
  if (token === generation && !disposed && !done.value && elapsedTimer) timer = setTimeout(() => poll(token), 2500)
}
const startResearch = async () => {
  if (!query.value || disposed) return
  stopPoll()
  const token = ++generation
  taskId = null
  done.value = false
  elapsed.value = 0
  consecutivePollErrors = 0
  errorMessage.value = ''
  requestId ||= crypto.randomUUID()
  try {
    const res = await startSignalsResearch({ query: query.value, segments: segs.value, request_id: requestId })
    if (token !== generation || disposed) return
    if (!res.success || !res.data?.task_id) throw new Error('Не удалось запустить исследование')
    taskId = res.data.task_id
    elapsedTimer = setInterval(() => elapsed.value++, 1000)
    poll(token)
  } catch (error) {
    if (token === generation && !disposed) errorMessage.value = error?.message || 'Не удалось запустить разведку.'
  }
}
const rerun = () => {
  requestId = null
  result.value = { sources_count: 0, sources: [], sources_by_platform: [], analysis: {} }
  agents.value = []
  totalSources.value = 0
  startResearch()
}
const goNext = () => router.push({ name: 'Process', params: { projectId: 'new' } })

// Read-only: грузим сохранённые сигналы прогона (без повторной разведки).
const loadSaved = async () => {
  errorMessage.value = ''
  try {
    const res = await getSavedSignals(savedSim)
    if (disposed) return
    if (res.success && res.data) {
      result.value = res.data
      totalSources.value = res.data.sources_count || 0
      query.value = '(сохранённый прогон)'
      done.value = true
    } else {
      errorMessage.value = 'Сохранённое исследование недоступно.'
    }
  } catch (e) {
    if (!disposed) errorMessage.value = 'Не удалось загрузить сохранённое исследование. Попробуйте ещё раз.'
  }
}

onMounted(() => { readonly.value ? loadSaved() : startResearch() })
onUnmounted(() => { disposed = true; generation++; stopPoll() })
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.06); border-radius: 10px; }
</style>
