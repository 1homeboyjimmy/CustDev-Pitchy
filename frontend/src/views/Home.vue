<template>
  <AppLayout>
    <div class="flex-1 overflow-y-auto">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-24 space-y-24">
      <!-- Hero Section -->
      <section class="relative space-y-12">
        <div class="space-y-8 text-center">
          <div class="flex items-center justify-center gap-3">
            <StatusBadge type="primary">Общество агентов</StatusBadge>
          </div>

          <h1 class="font-serif text-5xl md:text-8xl tracking-tight text-white leading-[1.05]">
            Анализируй реальность.<br />
            <span class="text-gradient italic">Симулируй будущее.</span>
          </h1>

          <p class="text-xl md:text-2xl text-white/60 leading-relaxed mx-auto">
            <span class="text-white font-semibold">Pitchy.Pro</span> анализирует ваши инвестиционные презентации и рыночные гипотезы. Мы строим цифровую модель рынка, населенную автономными ИИ-агентами (инвесторами, экспертами, клиентами). Наблюдайте, как они реагируют на ваш питч, предсказывайте рыночные барьеры и тестируйте стратегии — быстро и эффективно.
          </p>

          <div class="pt-4 flex flex-col sm:flex-row items-center justify-center gap-6 uppercase tracking-[0.2em] text-[10px] font-bold text-white/40">
            <div class="flex items-center gap-2">
              <ShieldCheckIcon class="w-4 h-4 text-white/80" />
              <span>100% Приватно</span>
            </div>
            <div class="hidden sm:block text-white/10">•</div>
            <div class="flex items-center gap-2">
              <SparklesIcon class="w-4 h-4 text-white animate-pulse" />
              <span>Технология GraphRAG + LLM</span>
            </div>
            <div class="hidden sm:block text-white/10">•</div>
            <div class="flex items-center gap-2">
              <ZapIcon class="w-4 h-4 text-white/80" />
              <span>Мгновенный инсайт</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Dashboard Grid -->
      <section class="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start pt-12 border-t border-white/5">
        <!-- Left: Status & Workflow -->
        <div class="lg:col-span-5 space-y-8">
          <div class="space-y-4">
            <h2 class="font-serif text-3xl text-white tracking-tight">Режим ожидания</h2>
            <p class="text-white/50 leading-relaxed">
              Локальный движок предсказаний инициализирован. Загрузите ваш питч-дек (PDF, MD, TXT), чтобы засеять новую рыночную симуляцию и проверить жизнеспособность вашего стартапа.
            </p>
          </div>



          <GlassCard class="space-y-6">
            <h3 class="text-sm font-bold text-white/40 uppercase tracking-widest flex items-center gap-2">
              <LayersIcon class="w-4 h-4" />
              Последовательность процесса
            </h3>
            <div class="space-y-6">
              <div v-for="(step, i) in steps" :key="i" class="flex gap-4 group">
                <span class="text-2xl font-bold text-white/10 group-hover:text-white transition-colors">{{ step.num }}</span>
                <div class="space-y-1">
                  <div class="text-sm font-bold text-white/80 transition-colors">{{ step.title }}</div>
                  <div class="text-xs text-white/40 leading-relaxed">{{ step.desc }}</div>
                </div>
              </div>
            </div>
          </GlassCard>
        </div>

        <!-- Right: Interactive Console -->
        <div class="lg:col-span-7">
          <div class="rounded-3xl border border-white/[0.08] bg-white/[0.015] p-8 md:p-10 space-y-10">
            <!-- Step 01: Upload -->
            <div class="space-y-5">
              <div class="flex items-end justify-between">
                <div class="space-y-1">
                  <span class="text-[10px] font-bold text-white/30 uppercase tracking-[0.25em] font-sans">01 / Источник</span>
                  <h3 class="font-serif text-3xl text-white leading-none">Ваш питч-дек</h3>
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
                <h3 class="font-serif text-3xl text-white leading-none">Цели анализа</h3>
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

            <!-- Action -->
            <button
              type="button"
              @click="startSimulation"
              :disabled="!canSubmit || loading"
              class="w-full inline-flex items-center justify-center gap-2 bg-white text-black px-8 py-4 rounded-full text-[12px] font-bold uppercase tracking-[0.15em] font-sans hover:bg-neutral-200 transition-colors disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer shadow-[0_0_30px_rgba(255,255,255,0.08)]"
            >
              <span v-if="loading" class="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin"></span>
              <ZapIcon v-else class="w-4 h-4 fill-current" />
              Запустить симуляцию
            </button>
          </div>
        </div>
      </section>

      <!-- History DB Placeholder -->
      <HistoryDatabase v-if="projectData?.projects?.length" />
    </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
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
  Sparkles as SparklesIcon
} from 'lucide-vue-next'

const steps = [
  { num: '01', title: 'Анализ Питча', desc: 'Извлечение ключевых инсайтов, рыночных сущностей и связей из вашего питча. Построение структурного графа знаний.' },
  { num: '02', title: 'Общество агентов', desc: 'Генерация профилей инвесторов, конкурентов и целевой аудитории специально под ваш проект.' },
  { num: '03', title: 'Симуляция', desc: 'Запуск живого обсуждения вашего продукта в симулированной среде общества. Наблюдение за возражениями и поддержкой.' },
  { num: '04', title: 'Прогноз Выживаемости', desc: 'Агрегация мнений всех агентов в единый аналитический отчет с оценкой перспектив и рекомендациями по улучшению.' },
  { num: '05', title: 'Интервью с Рынком', desc: 'Личное интервью с любым агентом общества или уточнение деталей прогноза у аналитического агента.' },
]

const router = useRouter()
const projectData = ref(null) 
const formData = ref({ simulationRequirement: '' })
const files = ref([])
const loading = ref(false)
const isDragOver = ref(false)
const fileInput = ref(null)

const canSubmit = computed(() => {
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

const startSimulation = async () => {
  if (!canSubmit.value || loading.value) return
  loading.value = true
  try {
    const { setPendingUpload } = await import('../store/pendingUpload.js')
    setPendingUpload(files.value, formData.value.simulationRequirement)
    router.push({ name: 'Process', params: { projectId: 'new' } })
  } catch (err) {
    console.error('Failed to start simulation:', err)
  } finally {
    loading.value = false
  }
}
</script>
