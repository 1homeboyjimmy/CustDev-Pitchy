<template>
  <div class="space-y-8 animate-in fade-in slide-in-from-right-4 duration-700">
    <!-- Introduction -->
    <div class="block">
      <span class="block text-[10px] font-bold text-white/30 uppercase tracking-[0.25em] font-sans mb-2">01 / Этап</span>
      <h2 class="block font-sans not-italic text-2xl font-semibold text-white tracking-tight mb-3">
        Синтез знаний
      </h2>
      <p class="block text-sm text-white/55 leading-relaxed max-w-2xl">
        Движок извлекает архитектуру общества из ваших неструктурированных данных. Этот процесс создает фундаментальную онтологию и многомерный граф знаний, который станет основой симуляции.
      </p>
    </div>

    <!-- Step 01: Ontology -->
    <GlassCard :class="{ 'border-white/30 bg-white/5 shadow-[0_0_20px_rgba(255,255,255,0.15)]/5': currentPhase === 0 }">
      <div class="flex items-start justify-between mb-6">
        <div class="space-y-1">
          <div class="flex items-center gap-2 text-[10px] font-mono text-white/30 uppercase tracking-widest">
            <span>Метод синтеза</span>
            <span class="w-px h-2 bg-white/10"></span>
            <span class="text-white">POST /api/graph/ontology/generate</span>
          </div>
          <h3 class="text-lg font-bold text-white">Генерация онтологии</h3>
        </div>
        <div class="flex items-center gap-3">
          <button 
            v-if="currentPhase === 0 || currentPhase === 1" 
            @click="$emit('stop-task');" 
            class="px-2 py-1 rounded bg-red-500/10 text-red-500 text-[9px] font-bold border border-red-500/20 hover:bg-red-500/20 transition-all uppercase"
          >
            Остановить
          </button>
          <StatusBadge :type="currentPhase > 0 ? 'success' : (currentPhase === 0 ? 'primary' : 'default')">
            {{ currentPhase > 0 ? 'Синтезировано' : (currentPhase === 0 ? 'Анализ' : 'В очереди') }}
          </StatusBadge>
        </div>
      </div>

      <div class="space-y-6">
        <p class="text-xs text-white/50 leading-relaxed italic">
          "LLM анализирует контекст для идентификации эмерджентных типов сущностей и структур связей, подходящих для высокоточной симуляции."
        </p>

        <!-- Progress Indicator -->
        <div v-if="currentPhase === 0 && ontologyProgress" class="flex items-center gap-3 p-3 rounded-xl bg-white/10 border border-white/20 animate-pulse">
          <div class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
          <span class="text-[10px] font-bold text-white/90 uppercase tracking-widest">
            {{ ontologyProgress.message || 'Синтез архитектуры общества...' }}
          </span>
        </div>

        <!-- Entity Tags -->
        <div v-if="projectData?.ontology?.entity_types" class="space-y-3">
          <span class="text-[9px] font-bold text-white/20 uppercase tracking-[0.2em] px-1">Обнаруженные классы сущностей</span>
          <div class="flex flex-wrap gap-2">
            <button 
              v-for="entity in projectData.ontology.entity_types" 
              :key="entity.name"
              @click="selectOntologyItem(entity, 'entity')"
              :title="entity.name"
              class="px-3 py-1.5 rounded-lg bg-white/5 border border-white/5 text-[10px] font-mono text-white/60 hover:text-white hover:border-white/50 transition-all"
            >
              {{ translateType(entity.name) }}
            </button>
          </div>
        </div>

        <!-- Relation Tags -->
        <div v-if="projectData?.ontology?.edge_types" class="space-y-3">
          <span class="text-[9px] font-bold text-white/20 uppercase tracking-[0.2em] px-1">Установленные связи</span>
          <div class="flex flex-wrap gap-2">
            <button 
              v-for="rel in projectData.ontology.edge_types" 
              :key="rel.name" 
              @click="selectOntologyItem(rel, 'relation')"
              :title="rel.name"
              class="px-3 py-1.5 rounded-lg bg-white/5 border border-white/5 text-[10px] font-mono text-white/60 hover:text-white hover:border-white/25 transition-all"
            >
              {{ translateType(rel.name) }}
            </button>
          </div>
        </div>
      </div>
    </GlassCard>

    <!-- Step 02: Graph Build -->
    <GlassCard :class="{ 'border-white/30 bg-white/5 shadow-[0_0_20px_rgba(255,255,255,0.12)]/5': currentPhase === 1 }">
      <div class="flex items-start justify-between mb-8">
        <div class="space-y-1">
          <div class="flex items-center gap-2 text-[10px] font-mono text-white/30 uppercase tracking-widest">
            <span>Экземпляр процесса</span>
            <span class="w-px h-2 bg-white/10"></span>
            <span class="text-white/80">POST /api/graph/build</span>
          </div>
          <h3 class="text-lg font-bold text-white">Построение GraphRAG</h3>
        </div>
        <StatusBadge :type="currentPhase > 1 ? 'success' : (currentPhase === 1 ? 'cyan' : 'default')">
          {{ currentPhase > 1 ? 'Построено' : (currentPhase === 1 ? `${buildProgress?.progress || 0}%` : 'Ожидание') }}
        </StatusBadge>
      </div>

      <div class="space-y-8">
        <p class="text-xs text-white/50 leading-relaxed italic">
          "Движок наносит архитектуру общества на карту графа Neo4j. Сущности связываются через временные факты, формируются кластеры сообществ."
        </p>
        
        <!-- Progress Bar -->
        <div v-if="currentPhase === 1" class="space-y-2">
          <div class="h-1 w-full bg-white/5 rounded-full overflow-hidden">
            <div 
              class="h-full bg-gradient-to-r from-white to-white/70 transition-all duration-500 shadow-glow shadow-white/25" 
              :style="{ width: `${buildProgress?.progress || 0}%` }"
            ></div>
          </div>
          <div class="flex justify-between text-[8px] font-mono text-white/20 uppercase tracking-tighter">
            <span>Секвенирование фрагментов...</span>
            <span>{{ buildProgress?.progress || 0 }}% УСПЕШНО</span>
          </div>
        </div>

        <!-- Stats Grid -->
        <div class="grid grid-cols-3 gap-4">
          <div v-for="(val, label) in { 'Сущности': graphStats.nodes, 'Связи': graphStats.edges, 'Схема': graphStats.types }" :key="label" 
            class="p-4 rounded-2xl bg-white/[0.02] border border-white/5 text-center space-y-1">
            <div class="text-xl font-bold text-white font-mono">{{ val }}</div>
            <div class="text-[8px] font-bold text-white/20 uppercase tracking-widest">{{ label }}</div>
          </div>
        </div>
      </div>
    </GlassCard>

    <!-- Step 03: Complete -->
    <GlassCard v-if="currentPhase >= 2" class="border-white/20 bg-white/10 animate-in zoom-in duration-500 shadow-[0_0_20px_rgba(255,255,255,0.12)]/20">
      <div class="flex flex-col items-stretch text-center space-y-6 w-full">
        <div class="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center text-white/80 shadow-glow shadow-white/25 mx-auto shrink-0">
          <CheckIcon class="w-6 h-6" />
        </div>
        <div class="w-full max-w-md mx-auto">
          <h3 class="text-xl font-bold text-white tracking-tight mb-2">Архитектура общества готова</h3>
          <p class="text-sm text-white/50 leading-relaxed">
            Архитектура общества успешно секвенирована. Модель мира теперь стабильна и готова к активации агентов.
          </p>
        </div>

        <PitchyButton
          variant="primary"
          class="w-full max-w-xs mx-auto shadow-[0_0_20px_rgba(255,255,255,0.15)] text-sm py-4"
          @click="handleEnterEnvSetup"
          :loading="creatingSimulation"
        >
          Активировать модель общества
          <template #icon>
            <ZapIcon class="w-4 h-4 fill-current" />
          </template>
        </PitchyButton>
      </div>
    </GlassCard>

  </div>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { createSimulation } from '../api/simulation'
import GlassCard from './ui/GlassCard.vue'
import StatusBadge from './ui/StatusBadge.vue'
import PitchyButton from './ui/PitchyButton.vue'
import { 
  Check as CheckIcon,
  Zap as ZapIcon
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
