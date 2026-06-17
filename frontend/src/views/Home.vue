<template>
  <AppLayout>
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-24 space-y-24">
      <!-- Hero Section -->
      <section class="relative space-y-12">
        <div class="space-y-8 text-center">
          <motion.div
            class="flex items-center justify-center gap-3"
            :initial="{ opacity: 0, y: 16 }"
            :animate="{ opacity: 1, y: 0 }"
            :transition="{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }"
          >
            <StatusBadge type="primary">Общество агентов</StatusBadge>
          </motion.div>

          <motion.h1
            class="font-serif text-5xl md:text-8xl tracking-tight text-white leading-[1.05]"
            :initial="{ opacity: 0, y: 24 }"
            :animate="{ opacity: 1, y: 0 }"
            :transition="{ duration: 0.8, delay: 0.1, ease: [0.16, 1, 0.3, 1] }"
          >
            Нужен ли рынку<br />
            <span class="text-gradient italic">ваш продукт?</span>
          </motion.h1>

          <motion.p
            class="text-xl md:text-2xl text-white/60 leading-relaxed mx-auto"
            :initial="{ opacity: 0, y: 24 }"
            :animate="{ opacity: 1, y: 0 }"
            :transition="{ duration: 0.8, delay: 0.25, ease: [0.16, 1, 0.3, 1] }"
          >
            <span class="text-white font-semibold">Pitchy.Pro</span> проверяет спрос до того, как вы потратите месяцы на разработку. Мы собираем <span class="text-white">реальные сигналы боли</span> из сообществ (Хабр, vc.ru, Пикабу) и прогоняем вашу гипотезу через <span class="text-white">симуляцию общества ИИ-агентов</span> — а затем выдаём честный вердикт: стоит ли строить.
          </motion.p>

          <motion.div
            class="pt-4 flex flex-col sm:flex-row items-center justify-center gap-6 uppercase tracking-[0.2em] text-[10px] font-bold text-white/40"
            :initial="{ opacity: 0, y: 16 }"
            :animate="{ opacity: 1, y: 0 }"
            :transition="{ duration: 0.8, delay: 0.4, ease: [0.16, 1, 0.3, 1] }"
          >
            <div class="flex items-center gap-2">
              <ShieldCheckIcon class="w-4 h-4 text-white/80" />
              <span>Реальные сигналы рынка</span>
            </div>
            <div class="hidden sm:block text-white/10">•</div>
            <div class="flex items-center gap-2">
              <SparklesIcon class="w-4 h-4 text-white animate-pulse" />
              <span>Симуляция общества агентов</span>
            </div>
            <div class="hidden sm:block text-white/10">•</div>
            <div class="flex items-center gap-2">
              <ZapIcon class="w-4 h-4 text-white/80" />
              <span>Честный вердикт</span>
            </div>
          </motion.div>
        </div>
      </section>

      <!-- Dashboard Grid -->
      <section class="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start pt-12 border-t border-white/5">
        <!-- Left: Status & Workflow -->
        <div class="lg:col-span-5 space-y-8">
          <motion.div
            class="space-y-4"
            :initial="{ opacity: 0, y: 32 }"
            :while-in-view="{ opacity: 1, y: 0 }"
            :viewport="{ once: true, amount: 0.4 }"
            :transition="{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }"
          >
            <h2 class="text-3xl font-semibold text-white tracking-tight">С чего начать</h2>
            <p class="text-white/50 leading-relaxed">
              Опишите гипотезу стартапа вручную или сгенерируйте её из паспорта проекта Pitchy. Дальше система сама соберёт сигналы рынка, проведёт фокус-группу и сведёт всё в вердикт.
            </p>
          </motion.div>

          <motion.div
            :initial="{ opacity: 0, y: 32 }"
            :while-in-view="{ opacity: 1, y: 0 }"
            :viewport="{ once: true, amount: 0.2 }"
            :transition="{ duration: 0.8, delay: 0.1, ease: [0.16, 1, 0.3, 1] }"
          >
            <GlassCard class="space-y-6">
              <h3 class="text-sm font-bold text-white/40 uppercase tracking-widest flex items-center gap-2">
                <LayersIcon class="w-4 h-4" />
                Последовательность процесса
              </h3>
              <div class="space-y-6">
                <motion.div
                  v-for="(step, i) in steps"
                  :key="i"
                  class="flex gap-4 group"
                  :initial="{ opacity: 0, x: -16 }"
                  :while-in-view="{ opacity: 1, x: 0 }"
                  :viewport="{ once: true, amount: 0.6 }"
                  :transition="{ duration: 0.5, delay: i * 0.08, ease: [0.16, 1, 0.3, 1] }"
                >
                  <span class="text-2xl font-bold text-white/10 group-hover:text-white transition-colors">{{ step.num }}</span>
                  <div class="space-y-1">
                    <div class="text-sm font-bold text-white/80 transition-colors">{{ step.title }}</div>
                    <div class="text-xs text-white/40 leading-relaxed">{{ step.desc }}</div>
                  </div>
                </motion.div>
              </div>
            </GlassCard>
          </motion.div>
        </div>

        <!-- Right: Interactive Console -->
        <motion.div
          class="lg:col-span-7"
          :initial="{ opacity: 0, y: 40 }"
          :while-in-view="{ opacity: 1, y: 0 }"
          :viewport="{ once: true, amount: 0.15 }"
          :transition="{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }"
        >
          <div class="rounded-3xl border border-white/[0.08] bg-white/[0.015] p-8 md:p-10 space-y-10">
            <!-- Переключатель режимов входа -->
            <div class="grid grid-cols-2 gap-2 p-1 bg-white/[0.04] rounded-2xl">
              <button
                type="button"
                @click="entryMode = 'hypothesis'"
                class="flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-bold transition-all"
                :class="entryMode === 'hypothesis' ? 'bg-white/10 text-white border border-white/15' : 'text-white/40 hover:text-white/70'"
              >
                <LightbulbIcon class="w-4 h-4" /> Описать гипотезу
              </button>
              <button
                type="button"
                @click="entryMode = 'deck'"
                class="flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-bold transition-all"
                :class="entryMode === 'deck' ? 'bg-white/10 text-white border border-white/15' : 'text-white/40 hover:text-white/70'"
              >
                <UploadIcon class="w-4 h-4" /> Загрузить дек
              </button>
            </div>

            <!-- Режим: Гипотеза -->
            <template v-if="entryMode === 'hypothesis'">
              <div class="space-y-5">
                <div class="space-y-1">
                  <span class="text-[10px] font-bold text-white/30 uppercase tracking-[0.25em] font-sans">01 / Гипотеза</span>
                  <h3 class="text-3xl font-semibold text-white leading-none tracking-tight">Гипотеза стартапа</h3>
                </div>

                <!-- Явный путь: подтянуть из паспорта проекта Pitchy -->
                <button
                  type="button"
                  @click="generateFromFolder"
                  :disabled="loading"
                  class="w-full flex items-center gap-4 rounded-2xl border border-white/15 bg-white/[0.04] hover:bg-white/[0.07] hover:border-white/30 px-5 py-4 text-left transition-all group"
                  :title="folderHint"
                >
                  <div class="w-11 h-11 rounded-xl bg-white/10 border border-white/15 flex items-center justify-center shrink-0">
                    <FolderInputIcon class="w-5 h-5 text-white" />
                  </div>
                  <div class="min-w-0">
                    <div class="text-sm font-semibold text-white">Сгенерировать из паспорта проекта</div>
                    <div class="text-[12px] text-white/45">Подтянуть боль, решение и сегменты из вашего проекта Pitchy</div>
                  </div>
                  <ArrowRightIcon class="w-4 h-4 text-white/30 ml-auto shrink-0 group-hover:translate-x-0.5 transition-transform" />
                </button>
                <div v-if="folderOpen" class="rounded-2xl border border-white/12 bg-white/[0.03] p-4 space-y-2">
                  <div v-if="folderLoading" class="text-[12px] text-white/50 flex items-center gap-2"><LoaderIcon class="w-3.5 h-3.5 animate-spin" /> Загружаю ваши проекты…</div>
                  <div v-else-if="folderError" class="text-[12px] text-amber-300/80 leading-relaxed">{{ folderError }}</div>
                  <template v-else>
                    <div v-if="folderProjects.length" class="space-y-1.5">
                      <div class="text-[10px] uppercase tracking-widest text-white/30 mb-1">Выберите проект</div>
                      <button v-for="p in folderProjects" :key="p.id" type="button" @click="pickProject(p)" :disabled="folderImporting"
                        class="w-full flex items-center justify-between gap-3 rounded-xl bg-white/[0.04] border border-white/10 hover:border-white/30 px-4 py-2.5 text-left transition-all disabled:opacity-50">
                        <span class="text-sm text-white truncate">{{ p.name }}</span>
                        <span class="text-[11px] text-white/40 shrink-0">{{ p.readiness_index ?? 0 }}%</span>
                      </button>
                    </div>
                    <div v-else class="text-[12px] text-white/40">Проектов не найдено.</div>
                  </template>
                </div>

                <div class="flex items-center gap-3 text-[10px] uppercase tracking-[0.3em] text-white/25">
                  <div class="h-px flex-1 bg-white/10"></div> или заполните вручную <div class="h-px flex-1 bg-white/10"></div>
                </div>

                <div class="space-y-4">
                  <input v-model="hyp.name" type="text" :disabled="loading" placeholder="Название / суть — напр.: сервис подбора грантов" class="w-full rounded-2xl border border-white/10 bg-white/[0.02] px-5 py-3 text-[14px] text-white/90 placeholder:text-white/25 outline-none focus:border-white/30 focus:bg-white/[0.04] transition-colors" />
                  <textarea v-model="hyp.problem" :disabled="loading" placeholder="Проблема (боль клиента) — какую боль решаете?" class="w-full min-h-[80px] resize-none rounded-2xl border border-white/10 bg-white/[0.02] px-5 py-3 text-[14px] leading-relaxed text-white/90 placeholder:text-white/25 outline-none focus:border-white/30 focus:bg-white/[0.04] transition-colors"></textarea>
                  <textarea v-model="hyp.solution" :disabled="loading" placeholder="Решение — что предлагаете и чем лучше альтернатив?" class="w-full min-h-[80px] resize-none rounded-2xl border border-white/10 bg-white/[0.02] px-5 py-3 text-[14px] leading-relaxed text-white/90 placeholder:text-white/25 outline-none focus:border-white/30 focus:bg-white/[0.04] transition-colors"></textarea>

                  <div class="space-y-2">
                    <div v-if="segments.length" class="flex flex-wrap gap-2">
                      <span v-for="(s, i) in segments" :key="i" class="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-white/10 text-white border border-white/15">
                        {{ s }}
                        <button type="button" @click="removeSegment(i)" class="hover:text-white/60"><XIcon class="w-3 h-3" /></button>
                      </span>
                    </div>
                    <input v-model="segmentDraft" @keydown.enter.prevent="addSegment" type="text" :disabled="loading" placeholder="Сегменты ЦА — добавьте и нажмите Enter (напр.: фаундеры на ранней стадии)" class="w-full rounded-2xl border border-white/10 bg-white/[0.02] px-5 py-3 text-[14px] text-white/90 placeholder:text-white/25 outline-none focus:border-white/30 focus:bg-white/[0.04] transition-colors" />
                  </div>

                  <div class="space-y-1.5">
                    <span class="text-[10px] font-bold text-white/50 uppercase tracking-[0.2em] flex items-center gap-1.5"><TargetIcon class="w-3.5 h-3.5" /> Ключевая гипотеза для проверки</span>
                    <textarea v-model="hyp.question" :disabled="loading" placeholder="Что именно проверяем у рынка? Напр.: «фаундеры готовы платить 2000 ₽/мес за автоподбор грантов»" class="w-full min-h-[80px] resize-none rounded-2xl border border-white/10 bg-white/[0.02] px-5 py-3 text-[14px] leading-relaxed text-white/90 placeholder:text-white/25 outline-none focus:border-white/30 focus:bg-white/[0.04] transition-colors"></textarea>
                  </div>
                </div>
              </div>
            </template>

            <!-- Режим: Питч-дек -->
            <template v-else>
            <!-- Step 01: Upload -->
            <div class="space-y-5">
              <div class="flex items-end justify-between">
                <div class="space-y-1">
                  <span class="text-[10px] font-bold text-white/30 uppercase tracking-[0.25em] font-sans">01 / Источник</span>
                  <h3 class="text-3xl font-semibold text-white leading-none tracking-tight">Ваш питч-дек</h3>
                </div>
                <span class="text-[10px] font-mono text-white/30 hidden sm:block">PDF · MD · TXT</span>
              </div>

              <div
                class="relative rounded-2xl border border-white/10 hover:border-white/30 bg-white/[0.015] hover:bg-white/[0.03] h-52 flex flex-col items-center justify-center cursor-pointer transition-all duration-300 group"
                :class="{ 'border-white/30 bg-white/[0.04]': isDragOver }"
                @dragover.prevent="handleDragOver"
                @dragleave.prevent="handleDragLeave"
                @drop.prevent="handleDrop"
                @click="triggerFileInput"
              >
                <input ref="fileInput" type="file" multiple accept=".pdf,.md,.txt" @change="handleFileSelect" class="hidden" :disabled="loading" />

                <div v-if="files.length === 0" class="text-center space-y-4">
                  <div class="w-12 h-12 rounded-full border border-white/15 flex items-center justify-center mx-auto group-hover:border-white/40 transition-all">
                    <UploadIcon class="w-5 h-5 text-white/70" />
                  </div>
                  <div class="space-y-1">
                    <div class="text-sm text-white/80">Перетащите файлы сюда</div>
                    <div class="text-[10px] text-white/30 uppercase tracking-[0.25em] font-medium">или кликните для выбора</div>
                  </div>
                </div>

                <div v-else class="w-full h-full p-4 overflow-y-auto space-y-2">
                  <div v-for="(file, index) in files" :key="index" class="flex items-center justify-between p-3 bg-white/[0.03] border border-white/5 rounded-xl group/item hover:bg-white/[0.06] transition-colors">
                    <div class="flex items-center gap-3">
                      <FileTextIcon class="w-4 h-4 text-white/70" />
                      <span class="text-xs font-mono text-white/70 truncate max-w-[200px]">{{ file.name }}</span>
                    </div>
                    <button @click.stop="removeFile(index)" class="p-1 text-white/40 hover:text-red-300 transition-colors">
                      <XIcon class="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Subtle divider -->
            <div class="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent"></div>

            <!-- Step 02: Prompt -->
            <div class="space-y-5">
              <div class="space-y-1">
                <span class="text-[10px] font-bold text-white/30 uppercase tracking-[0.25em] font-sans">02 / Запрос</span>
                <h3 class="text-3xl font-semibold text-white leading-none tracking-tight">Цели анализа</h3>
              </div>

              <div class="relative group">
                <textarea
                  v-model="formData.simulationRequirement"
                  class="w-full min-h-[160px] resize-none rounded-2xl border border-white/10 bg-white/[0.02] px-5 py-4 text-[14px] leading-relaxed text-white/90 placeholder:text-white/25 placeholder:font-mono placeholder:text-[13px] outline-none focus:border-white/30 focus:bg-white/[0.04] transition-colors"
                  placeholder="// Укажите ваши вопросы к рынку: например, 'какие основные возражения будут у инвесторов?' или 'насколько конкурентоспособен продукт?'"
                  :disabled="loading"
                ></textarea>
              </div>
            </div>

            </template>

            <!-- Action -->
            <button
              type="button"
              @click="startSimulation"
              :disabled="!canSubmit || loading"
              class="w-full inline-flex items-center justify-center gap-2 bg-white text-black px-8 py-4 rounded-full text-[12px] font-bold uppercase tracking-[0.15em] font-sans hover:bg-neutral-200 transition-colors disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer shadow-[0_0_30px_rgba(255,255,255,0.08)]"
            >
              <span v-if="loading" class="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin"></span>
              <ZapIcon v-else class="w-4 h-4 fill-current" />
              {{ entryMode === 'hypothesis' ? 'Проверить гипотезу' : 'Запустить симуляцию' }}
            </button>
          </div>
        </motion.div>
      </section>

      <!-- Прогоны CustDev — всегда доступная секция результатов (грузит свою историю сама) -->
      <motion.div
        :initial="{ opacity: 0, y: 32 }"
        :while-in-view="{ opacity: 1, y: 0 }"
        :viewport="{ once: true, amount: 0.2 }"
        :transition="{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }"
      >
        <HistoryDatabase />
      </motion.div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { motion } from 'motion-v'
import AppLayout from '../components/layout/AppLayout.vue'
import GlassCard from '../components/ui/GlassCard.vue'
import PitchyButton from '../components/ui/PitchyButton.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import HistoryDatabase from '../components/HistoryDatabase.vue'
import {
  ShieldCheck as ShieldCheckIcon,
  Cpu as CpuIcon,
  Database as DatabaseIcon,
  Layers as LayersIcon,
  Upload as UploadIcon,
  FileText as FileTextIcon,
  X as XIcon,
  Zap as ZapIcon,
  Sparkles as SparklesIcon,
  Lightbulb as LightbulbIcon,
  Target as TargetIcon,
  FolderInput as FolderInputIcon,
  ArrowRight as ArrowRightIcon,
  Loader as LoaderIcon
} from 'lucide-vue-next'
import { listProjects, getProjectPassport } from '../api/projects'

const steps = [
  { num: '01', title: 'Гипотеза', desc: 'Опишите боль, решение и сегменты ЦА — вручную или сгенерируйте из паспорта проекта Pitchy.' },
  { num: '02', title: 'Сигналы рынка', desc: 'Сбор реальных обсуждений боли из Хабр, vc.ru и Пикабу: цитаты пользователей, текущие решения, готовность платить.' },
  { num: '03', title: 'Фокус-группа', desc: 'Общество ИИ-агентов отвечает на стандартные CustDev-вопросы. Можно поговорить один на один с любой персоной.' },
  { num: '04', title: 'Вердикт', desc: 'Сводим сигналы рынка и симуляцию общества в честный вывод: нужен ли рынку продукт и стоит ли его строить.' },
  { num: '05', title: 'Глубинное интервью', desc: 'Уточняйте детали у любого агента общества или у аналитика по итогам прогона.' },
]

const router = useRouter()
const projectData = ref(null)
const formData = ref({ simulationRequirement: '' })
const files = ref([])
const loading = ref(false)
const isDragOver = ref(false)
const fileInput = ref(null)

// Режим входа: гипотеза (ручной CustDev-ввод) или загрузка дека.
const entryMode = ref('hypothesis')
const hyp = ref({ name: '', problem: '', solution: '', question: '' })
const segments = ref([])
const segmentDraft = ref('')
const folderHint = 'Подтянуть данные из паспорта проекта Pitchy'
const folderOpen = ref(false)
const folderLoading = ref(false)
const folderImporting = ref(false)
const folderError = ref('')
const folderProjects = ref([])

const addSegment = () => {
  const s = segmentDraft.value.trim()
  if (s && !segments.value.includes(s)) segments.value.push(s)
  segmentDraft.value = ''
}
const removeSegment = (i) => segments.value.splice(i, 1)

// «Из паспорта проекта»: тянем список проектов пользователя с главного сервера.
const generateFromFolder = async () => {
  folderOpen.value = true
  folderError.value = ''
  if (folderProjects.value.length) return
  folderLoading.value = true
  try {
    const res = await listProjects()
    if (res.success) folderProjects.value = res.data?.projects || []
    else folderError.value = res.error || 'Не удалось загрузить проекты'
  } catch (e) {
    folderError.value = 'Паспорт-сервис ещё не развёрнут на главном сервере.'
  } finally {
    folderLoading.value = false
  }
}

// Выбор проекта → тянем паспорт → заполняем поля гипотезы.
const pickProject = async (p) => {
  folderImporting.value = true
  folderError.value = ''
  try {
    const res = await getProjectPassport(p.id)
    if (res.success) {
      const ps = res.data?.passport || {}
      const core = ps.core || {}
      hyp.value.name = core.name || p.name || hyp.value.name
      hyp.value.problem = core.problem || hyp.value.problem
      hyp.value.solution = core.solution || hyp.value.solution
      const ta = core.target_audience || ''
      if (ta) segments.value = String(ta).split(/[,;\n]+/).map(s => s.trim()).filter(Boolean).slice(0, 6)
      folderOpen.value = false
    } else folderError.value = res.error || 'Не удалось загрузить паспорт'
  } catch (e) {
    folderError.value = 'Не удалось загрузить паспорт проекта.'
  } finally {
    folderImporting.value = false
  }
}

const canSubmit = computed(() => {
  if (entryMode.value === 'hypothesis') {
    return hyp.value.problem.trim() !== '' && hyp.value.solution.trim() !== '' && hyp.value.question.trim() !== ''
  }
  return formData.value.simulationRequirement.trim() !== '' && files.value.length > 0
})

const triggerFileInput = () => { if (!loading.value) fileInput.value?.click() }
const handleFileSelect = (event) => { addFiles(Array.from(event.target.files)) }
const handleDragOver = (e) => { isDragOver.value = true }
const handleDragLeave = (e) => { isDragOver.value = false }
const handleDrop = (e) => { isDragOver.value = false; addFiles(Array.from(e.dataTransfer.files)) }

const addFiles = (newFiles) => {
  const allowed = ['.pdf', '.md', '.txt']
  const valid = newFiles.filter(f => allowed.some(ext => f.name.toLowerCase().endsWith(ext)))
  files.value = [...files.value, ...valid]
}

const removeFile = (index) => { files.value.splice(index, 1) }

// Собирает seed-файл и цель анализа из полей гипотезы (когда дек не загружают).
const buildHypothesisSeed = () => {
  const segLine = segments.value.length ? segments.value.join(', ') : 'не указаны'
  const seedText =
    `Название проекта: ${hyp.value.name || 'не указано'}\n` +
    `Проблема (боль клиента): ${hyp.value.problem}\n` +
    `Решение: ${hyp.value.solution}\n` +
    `Сегменты целевой аудитории: ${segLine}\n` +
    `Ключевая гипотеза для проверки: ${hyp.value.question}\n`
  const file = new File([seedText], 'Гипотеза.txt', { type: 'text/plain' })
  const requirement =
    `Цель CustDev: проверить, нужен ли рынку этот продукт. ` +
    `Ключевая гипотеза: ${hyp.value.question}. ` +
    `Сегменты ЦА: ${segLine}.`
  return { file, requirement }
}

const startSimulation = async () => {
  if (!canSubmit.value || loading.value) return
  loading.value = true
  try {
    const { setPendingUpload, setHypothesisContext } = await import('../store/pendingUpload.js')
    if (entryMode.value === 'hypothesis') {
      const { file, requirement } = buildHypothesisSeed()
      setPendingUpload([file], requirement)
      // Запрос для разведки сигналов — это боль/тема, плюс сегменты ЦА.
      const sigQuery = (hyp.value.problem || hyp.value.name || hyp.value.question).trim()
      setHypothesisContext(sigQuery, segments.value)
      router.push({ name: 'Signals' })
    } else {
      setPendingUpload(files.value, formData.value.simulationRequirement)
      router.push({ name: 'Process', params: { projectId: 'new' } })
    }
  } catch (err) {
    console.error('Failed to start simulation:', err)
  } finally {
    loading.value = false
  }
}
</script>
