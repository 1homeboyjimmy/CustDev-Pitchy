<template>
  <AppLayout>
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-24 space-y-24">
      <!-- Hero Section -->
      <section class="relative space-y-12">
        <div class="space-y-8 text-center">
          <div class="flex items-center justify-center gap-3">
            <StatusBadge type="primary">Автономный рой агентов</StatusBadge>
          </div>

          <h1 class="text-5xl md:text-8xl font-bold tracking-tight text-white leading-[1.1]">
            Анализируй реальность.<br />
            <span class="text-gradient">Симулируй будущее.</span>
          </h1>

          <p class="text-xl md:text-2xl text-white/60 leading-relaxed mx-auto">
            <span class="text-white font-semibold">Pitchy.Pro</span> анализирует ваши инвестиционные презентации и рыночные гипотезы. Мы строим цифровую модель рынка, населенную автономными ИИ-агентами (инвесторами, экспертами, клиентами). Наблюдайте, как они реагируют на ваш питч, предсказывайте рыночные барьеры и тестируйте стратегии — быстро и эффективно.
          </p>

          <div class="pt-4 flex flex-col sm:flex-row items-center justify-center gap-6 uppercase tracking-[0.2em] text-[10px] font-bold text-white/40">
            <div class="flex items-center gap-2">
              <ShieldCheckIcon class="w-4 h-4 text-pitchy-cyan" />
              <span>100% Приватно</span>
            </div>
            <div class="hidden sm:block text-white/10">•</div>
            <div class="flex items-center gap-2">
              <SparklesIcon class="w-4 h-4 text-pitchy-violet animate-pulse" />
              <span>Технология GraphRAG + LLM</span>
            </div>
            <div class="hidden sm:block text-white/10">•</div>
            <div class="flex items-center gap-2">
              <ZapIcon class="w-4 h-4 text-pitchy-cyan" />
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
            <div class="flex items-center gap-2 text-white/30 text-[10px] font-bold uppercase tracking-widest">
              <div class="w-1.5 h-1.5 bg-pitchy-cyan rounded-full animate-pulse shadow-glow shadow-pitchy-cyan"></div>
              Статус движка системы
            </div>
            <h2 class="text-3xl font-bold text-white">Режим ожидания</h2>
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
                <span class="text-2xl font-bold text-white/10 group-hover:text-pitchy-violet transition-colors">{{ step.num }}</span>
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
          <GlassCard class="space-y-8 border-white/10">
            <!-- Step 01: Upload -->
            <div class="space-y-4">
              <div class="flex items-center justify-between">
                <h3 class="text-sm font-bold text-white/80 flex items-center gap-2 italic">
                  Ваш Питч-дек
                </h3>
                <span class="text-[10px] font-mono text-white/30">ПОДДЕРЖИВАЮТСЯ: PDF, MD, TXT</span>
              </div>
              
              <div
                class="relative border-2 border-dashed border-white/10 rounded-2xl h-48 flex flex-col items-center justify-center cursor-pointer hover:bg-white/5 hover:border-pitchy-violet/30 transition-all duration-300 group"
                :class="{ 'border-pitchy-violet bg-pitchy-violet/5': isDragOver }"
                @dragover.prevent="handleDragOver"
                @dragleave.prevent="handleDragLeave"
                @drop.prevent="handleDrop"
                @click="triggerFileInput"
              >
                <input ref="fileInput" type="file" multiple accept=".pdf,.md,.txt" @change="handleFileSelect" class="hidden" :disabled="loading" />
                
                <div v-if="files.length === 0" class="text-center space-y-4">
                  <div class="w-12 h-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center mx-auto group-hover:border-pitchy-violet group-hover:text-pitchy-violet transition-all">
                    <UploadIcon class="w-6 h-6 border-none" />
                  </div>
                  <div class="space-y-1">
                    <div class="text-sm font-bold text-white/70">Перетащите файлы сюда</div>
                    <div class="text-[10px] text-white/30 uppercase tracking-widest font-bold">или нажмите для выбора в хранилище</div>
                  </div>
                </div>

                <div v-else class="w-full h-full p-4 overflow-y-auto space-y-2">
                  <div v-for="(file, index) in files" :key="index" class="flex items-center justify-between p-3 bg-white/5 border border-white/5 rounded-xl group/item hover:bg-white/10 transition-colors">
                    <div class="flex items-center gap-3">
                      <FileTextIcon class="w-4 h-4 text-pitchy-cyan" />
                      <span class="text-xs font-mono text-white/70 truncate max-w-[200px]">{{ file.name }}</span>
                    </div>
                    <button @click.stop="removeFile(index)" class="p-1 hover:text-pitchy-score-red transition-colors">
                      <XIcon class="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div class="h-px bg-white/5 relative">
              <span class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-[#1A1A24] px-4 text-[10px] font-bold text-white/20 uppercase tracking-[0.3em]">Параметры</span>
            </div>

            <!-- Step 02: Prompt -->
            <div class="space-y-4">
              <div class="flex items-center justify-between">
                <h3 class="text-sm font-bold text-white/80 flex items-center gap-2 italic">
                  Цели анализа
                </h3>
              </div>
              
              <div class="relative group">
                <textarea 
                  v-model="formData.simulationRequirement" 
                  class="pitchy-input w-full min-h-[160px] resize-none pb-12" 
                  placeholder="// Укажите ваши вопросы к рынку: например, 'какие основные возражения будут у инвесторов?' или 'насколько конкурентоспособен продукт?'"
                  :disabled="loading"
                ></textarea>
                <div class="absolute bottom-4 right-4 flex items-center gap-2 text-[10px] font-mono text-white/30 uppercase tracking-widest">
                  <CpuIcon class="w-3 h-3" />
                  Локальный движок активен
                </div>
              </div>
            </div>

            <!-- Action -->
            <PitchyButton 
              size="lg" 
              class="w-full text-lg py-5 shadow-glow-primary" 
              @click="startSimulation" 
              :disabled="!canSubmit || loading"
              :loading="loading"
            >
              Запустить движок
              <template #icon>
                <ZapIcon class="w-5 h-5 fill-current" />
              </template>
            </PitchyButton>
          </GlassCard>
        </div>
      </section>

      <!-- History DB Placeholder -->
      <HistoryDatabase v-if="projectData?.projects?.length" />
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
  { num: '02', title: 'Генерация Рынков', desc: 'Генерация профилей инвесторов, конкурентов и целевой аудитории специально под ваш проект.' },
  { num: '03', title: 'Рыночная Симуляция', desc: 'Запуск живого обсуждения вашего продукта в симулированной рыночной среде. Наблюдение за возражениями и поддержкой.' },
  { num: '04', title: 'Прогноз Выживаемости', desc: 'Агрегация мнений всех ИИ-агентов в единый аналитический отчет с оценкой перспектив и рекомендациями по улучшению.' },
  { num: '05', title: 'Интервью с Рынком', desc: 'Личное интервью с любым ИИ-инвестором или уточнение деталей прогноза у аналитического агента.' },
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
