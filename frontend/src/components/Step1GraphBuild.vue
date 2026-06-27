<template>
  <div class="space-y-6 animate-in fade-in slide-in-from-right-4 duration-700">
    <!-- Intro -->
    <div>
      <span class="block text-[10px] font-bold text-white/30 uppercase tracking-[0.25em] font-sans mb-2">Подготовка</span>
      <h2 class="font-sans text-2xl font-semibold text-white tracking-tight mb-2">Готовим фокус-группу</h2>
      <p class="text-sm text-white/55 leading-relaxed max-w-2xl">
        Анализируем вашу гипотезу, строим карту рынка и готовим общество персон. Это займёт минуту.
      </p>
    </div>

    <!-- Шаги (на языке ценности, без инженерной кухни) -->
    <div class="space-y-3">
      <!-- 1. Анализ гипотезы / онтология -->
      <div class="rounded-2xl border p-4 flex items-center gap-4 transition-all"
        :class="currentPhase === 0 ? 'bg-white/[0.05] border-white/25' : 'bg-white/[0.02] border-white/10'">
        <div class="w-9 h-9 rounded-xl shrink-0 flex items-center justify-center border"
          :class="currentPhase > 0 ? 'bg-white/[0.06] border-white/15 text-white' : 'bg-white/[0.03] border-white/10 text-white/50'">
          <CheckIcon v-if="currentPhase > 0" class="w-4 h-4" />
          <LoaderIcon v-else-if="currentPhase === 0" class="w-4 h-4 animate-spin" />
          <ClockIcon v-else class="w-4 h-4" />
        </div>
        <div class="min-w-0">
          <div class="text-sm font-semibold text-white">Анализируем гипотезу</div>
          <div class="text-[12px] text-white/45 truncate">
            {{ currentPhase === 0 ? (ontologyProgress?.message || 'выделяем боли, сегменты и решения…') : 'боли, сегменты и решения' }}
          </div>
        </div>
        <button v-if="currentPhase === 0 || currentPhase === 1" @click="$emit('stop-task')"
          class="ml-auto text-[10px] text-white/30 hover:text-red-400 uppercase tracking-wide shrink-0">стоп</button>
      </div>

      <!-- 2. Карта рынка / граф -->
      <div class="rounded-2xl border p-4 transition-all"
        :class="currentPhase === 1 ? 'bg-white/[0.05] border-white/25' : 'bg-white/[0.02] border-white/10'">
        <div class="flex items-center gap-4">
          <div class="w-9 h-9 rounded-xl shrink-0 flex items-center justify-center border"
            :class="currentPhase > 1 ? 'bg-white/[0.06] border-white/15 text-white' : (currentPhase === 1 ? 'bg-white/[0.03] border-white/10 text-white' : 'bg-white/[0.03] border-white/10 text-white/50')">
            <CheckIcon v-if="currentPhase > 1" class="w-4 h-4" />
            <LoaderIcon v-else-if="currentPhase === 1" class="w-4 h-4 animate-spin" />
            <ClockIcon v-else class="w-4 h-4" />
          </div>
          <div class="min-w-0 flex-1">
            <div class="text-sm font-semibold text-white">Строим карту рынка</div>
            <div class="text-[12px] text-white/45">связи болей, сегментов и решений</div>
          </div>
          <span v-if="currentPhase === 1" class="text-[12px] font-mono text-white/55 shrink-0">{{ buildProgress?.progress || 0 }}%</span>
        </div>
        <div v-if="currentPhase === 1" class="mt-3 h-1.5 w-full bg-white/[0.06] rounded-full overflow-hidden">
          <div class="h-full bg-white/60 rounded-full transition-all duration-500" :style="{ width: `${buildProgress?.progress || 0}%` }"></div>
        </div>
        <div v-if="currentPhase >= 1 && (graphStats.nodes || graphStats.edges)" class="mt-3 flex gap-4 text-[12px] text-white/45">
          <span><span class="text-white/80 font-mono">{{ graphStats.nodes }}</span> узлов</span>
          <span><span class="text-white/80 font-mono">{{ graphStats.edges }}</span> связей</span>
        </div>
      </div>
    </div>

    <!-- Что выявили на рынке -->
    <div v-if="projectData?.ontology?.entity_types" class="rounded-2xl border border-white/10 bg-white/[0.02] p-5 space-y-4">
      <div class="text-white/40 text-[10px] font-bold uppercase tracking-[0.2em]">Кого нашли на рынке</div>
      <div class="flex flex-wrap gap-2">
        <button v-for="entity in projectData.ontology.entity_types" :key="entity.name"
          @click="selectOntologyItem(entity, 'entity')" :title="entity.name"
          class="px-3 py-1.5 rounded-full bg-white/[0.05] border border-white/10 text-[12px] text-white/65 hover:text-white hover:border-white/30 transition-all">
          {{ translateType(entity.name) }}
        </button>
      </div>
      <template v-if="projectData?.ontology?.edge_types">
        <div class="text-white/40 text-[10px] font-bold uppercase tracking-[0.2em] pt-1">Связи</div>
        <div class="flex flex-wrap gap-2">
          <button v-for="rel in projectData.ontology.edge_types" :key="rel.name"
            @click="selectOntologyItem(rel, 'relation')" :title="rel.name"
            class="px-3 py-1.5 rounded-full bg-white/[0.05] border border-white/10 text-[12px] text-white/65 hover:text-white hover:border-white/30 transition-all">
            {{ translateType(rel.name) }}
          </button>
        </div>
      </template>
    </div>

    <!-- Готово -->
    <div v-if="currentPhase >= 2" class="rounded-2xl border border-white/20 bg-white/[0.05] p-6 text-center space-y-5 animate-in zoom-in duration-500">
      <div class="w-12 h-12 rounded-full bg-white/15 border border-white/20 flex items-center justify-center text-white mx-auto">
        <CheckIcon class="w-6 h-6" />
      </div>
      <div class="max-w-md mx-auto">
        <h3 class="text-xl font-semibold text-white tracking-tight mb-2">Карта рынка готова</h3>
        <p class="text-sm text-white/50 leading-relaxed">Дальше соберём общество персон и проведём фокус-группу.</p>
      </div>
      <PitchyButton variant="primary" class="w-full max-w-xs mx-auto shadow-[0_0_20px_rgba(255,255,255,0.15)] text-sm py-4"
        @click="handleEnterEnvSetup" :loading="creatingSimulation">
        Перейти к персонам
        <template #icon><ZapIcon class="w-4 h-4 fill-current" /></template>
      </PitchyButton>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { createSimulation } from '../api/simulation'
import { attachSignals } from '../api/signals'
import { getPendingUpload } from '../store/pendingUpload'
import GlassCard from './ui/GlassCard.vue'
import StatusBadge from './ui/StatusBadge.vue'
import PitchyButton from './ui/PitchyButton.vue'
import {
  Check as CheckIcon,
  Zap as ZapIcon,
  Loader as LoaderIcon,
  Clock as ClockIcon
} from 'lucide-vue-next'

const router = useRouter()

const props = defineProps({
  currentPhase: { type: Number, default: 0 },
  projectData: Object,
  ontologyProgress: Object,
  buildProgress: Object,
  graphData: Object
})

const emit = defineEmits(['next-step', 'stop-task'])

const selectedOntologyItem = ref(null)
const creatingSimulation = ref(false)

const handleEnterEnvSetup = async () => {
  if (!props.projectData?.project_id || !props.projectData?.graph_id) return
  creatingSimulation.value = true
  try {
    const res = await createSimulation({
      project_id: props.projectData.project_id,
      graph_id: props.projectData.graph_id,
      enable_twitter: true,
      enable_reddit: true
    })
    if (res.success && res.data?.simulation_id) {
      // Прикрепляем результат разведки сигналов к прогону (фон, не блокируем переход).
      const signalsResult = getPendingUpload().signalsResult
      if (signalsResult) {
        attachSignals({ simulation_id: res.data.simulation_id, result: signalsResult })
          .catch(() => { /* не критично: сигналы просто не будут доступны из истории */ })
      }
      router.push({ name: 'Simulation', params: { simulationId: res.data.simulation_id } })
    }
  } catch (err) {
    console.error(err)
  } finally {
    creatingSimulation.value = false
  }
}

const selectOntologyItem = (item, type) => {
  selectedOntologyItem.value = { ...item, itemType: type }
}

const graphStats = computed(() => ({
  nodes: props.graphData?.node_count || props.graphData?.nodes?.length || 0,
  edges: props.graphData?.edge_count || props.graphData?.edges?.length || 0,
  types: props.projectData?.ontology?.entity_types?.length || 0
}))

const LABEL_MAP = {
  // Entity types
  'Organization': 'Организация',
  'Entity': 'Сущность',
  'Person': 'Человек',
  'StartupFounder': 'Фаундер',
  'MarketplaceSeller': 'Селлер',
  'BusinessConsultant': 'Консультант',
  'Investor': 'Инвестор',
  'UniversityStudent': 'Студент',
  'GovernmentAgency': 'Гос. орган',
  'TechStartup': 'IT-стартап',
  'MarketplacePlatform': 'Маркетплейс',
  'Seller': 'Продавец',
  'Founder': 'Основатель',
  'Consultant': 'Консультант',
  'Student': 'Студент',
  'Agency': 'Агентство',
  'Platform': 'Платформа',
  // Edge (relationship) types
  'FOUNDERS_OF': 'Основатель',
  'CONSULTS_FOR': 'Консультирует',
  'INVESTS_IN': 'Инвестирует',
  'SELLS_ON': 'Продаёт на',
  'STUDIES_AT': 'Учится в',
  'PROVIDES_SUPPORT': 'Поддерживает',
  'COMPETES_WITH': 'Конкурирует с',
  'USES_TOOL': 'Использует',
  'REPORTS_TO': 'Подчиняется',
  'COLLABORATES_WITH': 'Сотрудничает с',
  'WORKS_AT': 'Работает в',
  'MANAGES': 'Управляет',
  'PARTNERS_WITH': 'Партнёр',
  'RELATED_TO': 'Связан с',
  'BELONGS_TO': 'Принадлежит',
  'PART_OF': 'Часть',
  'CREATED_BY': 'Создан',
  'LOCATED_IN': 'Расположен в',
  'KNOWS': 'Знает',
  'HIRES': 'Нанимает',
  'MENTORS': 'Наставляет',
  'SUPPLIES_TO': 'Поставляет',
  'BUYS_FROM': 'Покупает у',
}

const translateType = (type) => LABEL_MAP[type] || type


</script>
