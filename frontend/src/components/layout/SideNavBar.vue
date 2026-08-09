<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { getMe } from '../../api/auth'
import {
  LayoutDashboard,
  MessageSquare,
  GitBranch,
  Users,
  Shield,
  HelpCircle,
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
const isAdmin = ref(false)
const logoUrl = '/icon.png'

onMounted(async () => {
  const stored = localStorage.getItem('custdev:sidenav-collapsed')
  if (stored !== null) isCollapsed.value = stored === '1'

  // Кнопка «Админ» — только администраторам (Config.ADMIN_USER_IDS на бэке).
  try {
    const res = await getMe()
    if (res && res.success && res.data) isAdmin.value = !!res.data.is_admin
  } catch {
    isAdmin.value = false
  }
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

// Скрываем «Админ» у обычных пользователей.
const visibleItems = computed(() =>
  items.filter((item) => item.id !== 'admin' || isAdmin.value)
)
</script>

<template>
  <aside
    :class="[
      'self-start sticky top-20 h-[calc(100vh-5rem)] border-r border-white/5 bg-black hidden lg:flex flex-col py-8 z-40 transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] shrink-0',
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
          class="font-display tracking-tight text-white inline-flex items-center text-xl shrink-0"
        >
          <img
            v-if="isCollapsed"
            :src="logoUrl"
            alt="Pitchy"
            class="w-8 h-8 rounded-lg object-contain"
          />
          <span v-else class="inline-flex items-baseline">
            Pitchy<span class="text-white/30 italic">.pro</span>
          </span>
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
        v-for="item in visibleItems"
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

  <!-- Compact navigation on phones and tablets. It does not reduce the work area. -->
  <nav
    class="lg:hidden fixed inset-x-0 bottom-0 z-[90] h-16 border-t border-white/10 bg-black/95 backdrop-blur-xl px-2 pb-[env(safe-area-inset-bottom)]"
    aria-label="Навигация CustDev"
  >
    <div class="h-full flex items-center justify-around max-w-xl mx-auto">
      <a
        v-for="item in visibleItems"
        :key="`mobile-${item.id}`"
        :href="item.href"
        :aria-label="item.label"
        :class="[
          'min-w-12 h-12 px-2 rounded-xl flex flex-col items-center justify-center gap-1 transition-colors',
          activeId === item.id ? 'bg-white/10 text-white' : 'text-white/45 hover:text-white'
        ]"
      >
        <component :is="item.icon" :size="18" :stroke-width="1.5" />
        <span class="text-[8px] leading-none font-medium truncate max-w-16">{{ item.label }}</span>
      </a>
    </div>
  </nav>
</template>
