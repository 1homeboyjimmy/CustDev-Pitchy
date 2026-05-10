<script setup>
import { ref, onMounted, watch } from 'vue'
import {
  LayoutDashboard,
  MessageSquare,
  GitBranch,
  Users,
  Shield,
  HelpCircle,
  Star,
  ChevronLeft,
  ChevronRight,
} from 'lucide-vue-next'

const props = defineProps({
  activeId: {
    type: String,
    default: 'custdev',
  },
})

const isCollapsed = ref(true)

onMounted(() => {
  const stored = localStorage.getItem('custdev:sidenav-collapsed')
  if (stored !== null) isCollapsed.value = stored === '1'
})

watch(isCollapsed, (v) => {
  localStorage.setItem('custdev:sidenav-collapsed', v ? '1' : '0')
})

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}

const items = [
  { id: 'overview', label: 'Обзор', icon: LayoutDashboard, href: 'https://pitchy.pro/dashboard' },
  { id: 'chat', label: 'Чат', icon: MessageSquare, href: 'https://pitchy.pro/dashboard?tab=chat' },
  { id: 'tree', label: 'Дорожная карта', icon: GitBranch, href: 'https://pitchy.pro/dashboard?tab=tree' },
  { id: 'custdev', label: 'Кастдев', icon: Users, href: 'https://custdev.pitchy.pro/' },
  { id: 'admin', label: 'Админ', icon: Shield, href: 'https://pitchy.pro/admin' },
]
</script>

<template>
  <aside
    :class="[
      'self-start sticky top-20 h-[calc(100vh-5rem)] border-r border-white/5 bg-black flex flex-col py-8 z-40 transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] shrink-0',
      isCollapsed ? 'w-20' : 'w-64',
    ]"
  >
    <!-- Header: logo + collapse toggle -->
    <div
      :class="[
        'px-6 mb-12 flex items-center justify-between transition-all duration-500',
        isCollapsed ? 'flex-col gap-8' : '',
      ]"
    >
      <div class="flex items-center gap-3 overflow-hidden">
        <a
          href="https://pitchy.pro/"
          class="font-display tracking-tight text-white inline-flex items-baseline text-xl"
        >
          <template v-if="isCollapsed">P</template>
          <template v-else>
            Pitchy<span class="text-white/30 italic">.pro</span>
          </template>
        </a>
      </div>
      <button
        @click="toggleCollapse"
        class="text-white/40 hover:text-white p-2 transition-all rounded-xl hover:bg-white/5 active:scale-90 border border-white/10"
        :aria-label="isCollapsed ? 'Развернуть' : 'Свернуть'"
      >
        <ChevronRight v-if="isCollapsed" :size="18" />
        <ChevronLeft v-else :size="18" />
      </button>
    </div>

    <!-- Nav -->
    <nav class="flex-1 px-3 space-y-1 overflow-hidden">
      <a
        v-for="item in items"
        :key="item.id"
        :href="item.href"
        :title="isCollapsed ? item.label : ''"
        :class="[
          'group flex items-center gap-3 px-4 py-3 transition-all duration-300 active:scale-[0.98] rounded-2xl',
          activeId === item.id
            ? 'bg-white/[0.05] text-white shadow-[0_4px_20px_rgba(255,255,255,0.02)]'
            : 'text-white/50 hover:bg-white/[0.03] hover:text-white',
          isCollapsed ? 'justify-center px-0' : '',
        ]"
      >
        <div
          :class="[
            'flex items-center justify-center transition-all duration-500',
            isCollapsed ? 'w-10 h-10' : 'w-5',
          ]"
        >
          <component
            :is="item.icon"
            :size="isCollapsed ? 20 : 18"
            :stroke-width="1.5"
            :class="activeId === item.id ? 'text-white' : 'text-white/40'"
          />
        </div>
        <span
          v-if="!isCollapsed"
          :class="[
            'font-display text-[17px] tracking-tight whitespace-nowrap transition-all duration-500',
            activeId === item.id ? 'text-white' : 'text-white/50 group-hover:text-white/80',
          ]"
        >
          {{ item.label }}
        </span>
      </a>
    </nav>

    <!-- Tip card -->
    <div v-if="!isCollapsed" class="px-5 mb-6 transition-all duration-500 opacity-100">
      <div class="rounded-3xl p-5 flex flex-col gap-3 border border-white/5 bg-gradient-to-br from-white/[0.02] to-transparent">
        <div class="flex items-center gap-2 text-white/40">
          <Star :size="14" :stroke-width="2" />
          <span class="font-mono text-[9px] uppercase tracking-[0.2em] font-bold">СОВЕТ</span>
        </div>
        <p class="font-sans text-[12px] text-white/40 leading-relaxed font-medium italic">
          «Чем подробнее вы опишете проект в начале, тем точнее будет анализ.»
        </p>
      </div>
    </div>

    <!-- Support -->
    <div
      :class="[
        'px-3 border-t border-white/5 pt-6 transition-all duration-500',
        isCollapsed ? 'flex flex-col items-center' : '',
      ]"
    >
      <a
        href="https://pitchy.pro/contact"
        :title="isCollapsed ? 'Поддержка' : ''"
        :class="[
          'group w-full flex items-center gap-3 px-4 py-3 text-white/50 hover:bg-white/[0.03] hover:text-white transition-all duration-300 rounded-2xl active:scale-[0.98]',
          isCollapsed ? 'justify-center px-0' : '',
        ]"
      >
        <div
          :class="[
            'flex items-center justify-center transition-all duration-500',
            isCollapsed ? 'w-10 h-10' : 'w-5',
          ]"
        >
          <HelpCircle
            :size="isCollapsed ? 20 : 18"
            :stroke-width="1.5"
            class="text-white/40 group-hover:text-white/80"
          />
        </div>
        <span
          v-if="!isCollapsed"
          class="font-display text-[17px] tracking-tight whitespace-nowrap"
        >
          Поддержка
        </span>
      </a>
    </div>
  </aside>
</template>
