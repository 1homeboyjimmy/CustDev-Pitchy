<template>
  <div class="space-y-8 pt-12 border-t border-white/5">
    <div class="flex items-center justify-between">
      <div class="space-y-1">
        <h2 class="text-2xl font-bold text-white uppercase tracking-tight">Прогоны CustDev</h2>
        <p class="text-xs text-white/30 font-mono">Сохранённые проверки гипотез — открой любой вердикт</p>
      </div>
      <div class="h-px flex-1 mx-8 bg-gradient-to-r from-white/10 to-transparent"></div>
    </div>

    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <div v-for="i in 4" :key="i" class="h-48 rounded-2xl bg-white/5 animate-pulse border border-white/5"></div>
    </div>

    <div v-else-if="projects.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <GlassCard 
        v-for="project in projects" 
        :key="project.simulation_id"
        hover
        class="group cursor-pointer border-white/5 hover:border-white/30 transition-all duration-500"
        @click="navigateToProject(project)"
      >
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-mono text-white/30 uppercase tracking-widest">
              {{ formatSimulationId(project.simulation_id) }}
            </span>
            <div class="flex gap-1.5 text-xs">
              <div 
                v-if="project.project_id" 
                class="w-1.5 h-1.5 rounded-full bg-white/8 shadow-glow shadow-white/25" 
                title="Graph Built"
              ></div>
              <div 
                v-if="project.report_id" 
                class="w-1.5 h-1.5 rounded-full bg-white/10 shadow-glow shadow-white/30" 
                title="Report Ready"
              ></div>
            </div>
          </div>

          <div class="space-y-2">
            <h3 class="text-sm font-bold text-white/90 group-hover:text-white transition-colors line-clamp-1">
              {{ getSimulationTitle(project.simulation_requirement) }}
            </h3>
            <p class="text-[11px] text-white/40 leading-relaxed line-clamp-2 italic">
              "{{ project.simulation_requirement }}"
            </p>
          </div>

          <div class="flex items-center justify-between pt-4 border-t border-white/5">
            <div class="flex flex-col gap-0.5">
              <span class="text-[10px] text-white/30">{{ formatDate(project.created_at) }}</span>
              <span class="text-[10px] font-mono text-white/20 uppercase tracking-tighter">{{ formatTime(project.created_at) }}</span>
            </div>
            <StatusBadge :type="getProgressType(project)" :dot="project.current_round < project.total_rounds">
              {{ formatRounds(project) }}
            </StatusBadge>
          </div>
        </div>
      </GlassCard>
    </div>

    <div v-else class="py-12 text-center space-y-4">
      <div class="text-white/20 italic text-sm">Прогонов пока нет — проверьте первую гипотезу выше.</div>
    </div>

    <!-- Modal remains mostly same but styled with Tailwind -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="selectedProject" class="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <div class="absolute inset-0 bg-pitchy-bg/80 backdrop-blur-sm" @click="closeModal"></div>
          <GlassCard class="relative z-10 w-full max-w-2xl bg-[#0A0A0F]/90 border-white/10 shadow-2xl space-y-8 animate-in fade-in zoom-in duration-300">
            <div class="flex items-start justify-between">
              <div class="space-y-1">
                <div class="flex items-center gap-3">
                  <span class="text-xs font-mono text-white uppercase tracking-widest">{{ formatSimulationId(selectedProject.simulation_id) }}</span>
                  <StatusBadge :type="getProgressType(selectedProject)">{{ formatRounds(selectedProject) }}</StatusBadge>
                </div>
                <h2 class="text-2xl font-bold text-white">{{ getSimulationTitle(selectedProject.simulation_requirement) }}</h2>
              </div>
              <button @click="closeModal" class="p-2 text-white/40 hover:text-white transition-colors">
                <XIcon class="w-6 h-6" />
              </button>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div class="space-y-4">
                <div class="space-y-1">
                  <span class="text-[10px] font-bold text-white/30 uppercase tracking-[0.2em]">Гипотеза</span>
                  <p class="text-sm text-white/70 leading-relaxed">{{ selectedProject.simulation_requirement }}</p>
                </div>
                <div class="space-y-3">
                  <span class="text-[10px] font-bold text-white/30 uppercase tracking-[0.2em]">Файлы</span>
                  <div class="space-y-2">
                    <div v-for="file in selectedProject.files" :key="file.filename" class="flex items-center gap-2 p-2 rounded-lg bg-white/5 border border-white/5">
                      <FileTextIcon class="w-3.5 h-3.5 text-white/80" />
                      <span class="text-xs font-mono text-white/60 truncate">{{ file.filename }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div class="space-y-4 flex flex-col justify-end">
                <PitchyButton variant="secondary" class="w-full justify-between" @click="goToProject" :disabled="!selectedProject.project_id">
                  <span>Граф знаний</span>
                  <ChevronRightIcon class="w-4 h-4" />
                </PitchyButton>
                <PitchyButton variant="secondary" class="w-full justify-between" @click="goToSimulation">
                  <span>Фокус-группа</span>
                  <ChevronRightIcon class="w-4 h-4" />
                </PitchyButton>
                <PitchyButton variant="primary" class="w-full justify-between shadow-[0_0_20px_rgba(255,255,255,0.15)]" @click="goToReport" :disabled="!selectedProject.report_id">
                  <span>Открыть вердикт</span>
                  <ChevronRightIcon class="w-4 h-4" />
                </PitchyButton>
              </div>
            </div>
            
            <div class="pt-4 border-t border-white/5 text-[10px] text-white/20 italic text-center">
              Сохранённый прогон: доступны вердикт и снимки окружения.
            </div>
          </GlassCard>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getSimulationHistory } from '../api/simulation'
import GlassCard from './ui/GlassCard.vue'
import StatusBadge from './ui/StatusBadge.vue'
import PitchyButton from './ui/PitchyButton.vue'
import { 
  X as XIcon, 
  FileText as FileTextIcon, 
  ChevronRight as ChevronRightIcon 
} from 'lucide-vue-next'

const router = useRouter()
const projects = ref([])
const loading = ref(true)
const selectedProject = ref(null)

const formatSimulationId = (id) => `SIM_${id.replace('sim_', '').slice(0, 6).toUpperCase()}`
const getSimulationTitle = (req) => req?.slice(0, 40) || 'Untitled Simulation'
const formatDate = (d) => new Date(d).toLocaleDateString()
const formatTime = (d) => new Date(d).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
const formatRounds = (s) => (s.total_rounds ? `${s.current_round}/${s.total_rounds} RNDS` : 'NOT STARTED')

const getProgressType = (s) => {
  if (!s.total_rounds || s.current_round === 0) return 'default'
  if (s.current_round >= s.total_rounds) return 'success'
  return 'warning'
}

const navigateToProject = (p) => selectedProject.value = p
const closeModal = () => selectedProject.value = null

const goToProject = () => {
  if (selectedProject.value?.project_id) {
    router.push({ name: 'Process', params: { projectId: selectedProject.value.project_id } })
    closeModal()
  }
}

const goToSimulation = () => {
  if (selectedProject.value?.simulation_id) {
    router.push({ name: 'Simulation', params: { simulationId: selectedProject.value.simulation_id } })
    closeModal()
  }
}

const goToReport = () => {
  if (selectedProject.value?.report_id) {
    router.push({ name: 'Report', params: { reportId: selectedProject.value.report_id } })
    closeModal()
  }
}

const loadHistory = async () => {
  try {
    loading.value = true
    const res = await getSimulationHistory(12)
    if (res.success) projects.value = res.data || []
  } catch (err) {
    console.error(err)
  } finally {
    loading.value = false
  }
}

onMounted(loadHistory)
</script>

<style scoped>
.modal-enter-active, .modal-leave-active { transition: opacity 0.3s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>
