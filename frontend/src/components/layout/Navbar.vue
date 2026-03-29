<script setup>
import { ref, onMounted } from 'vue'
import { Zap, Menu, X, User, LogOut, LayoutDashboard, HelpCircle, Info, CreditCard, Mail } from 'lucide-vue-next'

const isScrolled = ref(false)
const isMobileMenuOpen = ref(false)
const isAuthenticated = ref(false)

// Links configuration - all absolute to main domain
const navLinks = [
  { label: 'Дашборд', href: 'https://pitchy.pro/dashboard', icon: LayoutDashboard },
  { label: 'FAQ', href: 'https://pitchy.pro/faq', icon: HelpCircle },
  { label: 'О нас', href: 'https://pitchy.pro/about', icon: Info },
  { label: 'Тарифы', href: 'https://pitchy.pro/pricing', icon: CreditCard },
  { label: 'Контакты', href: 'https://pitchy.pro/contact', icon: Mail },
]

onMounted(() => {
  window.addEventListener('scroll', () => {
    isScrolled.value = window.scrollY > 20
  })

  // Check for access_token cookie
  isAuthenticated.value = document.cookie.includes('access_token')
})

const handleLogout = () => {
  // Clear the cookie on the shared domain
  document.cookie = 'access_token=; path=/; domain=.pitchy.pro; expires=Thu, 01 Jan 1970 00:00:01 GMT;'
  // Redirect to main login
  window.location.href = 'https://pitchy.pro/login'
}

const toggleMobileMenu = () => {
  isMobileMenuOpen.value = !isMobileMenuOpen.value
}
</script>

<template>
  <header 
    :class="[
      'fixed top-0 left-0 right-0 z-50 transition-all duration-300 h-20 flex items-center',
      isScrolled || isMobileMenuOpen ? 'bg-zinc-950/80 backdrop-blur-xl border-b border-zinc-800/50' : 'bg-transparent'
    ]"
  >
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full">
      <div class="flex items-center justify-between">
        <!-- Logo -->
        <a href="https://pitchy.pro" class="flex items-center gap-2 group">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center transition-transform group-hover:scale-105">
            <Zap class="w-5 h-5 text-white" />
          </div>
          <div class="flex items-baseline">
            <span class="text-xl font-bold text-white tracking-tight">pitchy</span>
            <span class="text-violet-400 font-medium">.pro</span>
            <span class="ml-2 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-violet-500/10 text-violet-400 border border-violet-500/20">CustDev</span>
          </div>
        </a>

        <!-- Desktop Nav -->
        <nav class="hidden md:flex items-center gap-1">
          <a
            v-for="link in navLinks"
            :key="link.href"
            :href="link.href"
            class="px-4 py-2 text-sm font-medium text-zinc-400 hover:text-white transition-colors duration-200"
          >
            {{ link.label }}
          </a>
          
          <div v-if="isAuthenticated" class="flex items-center gap-4 ml-4 pl-4 border-l border-white/10">
            <a href="https://pitchy.pro/account" class="text-zinc-400 hover:text-white transition-colors">
              <User class="w-5 h-5" />
            </a>
            <button @click="handleLogout" class="text-sm font-medium text-zinc-400 hover:text-red-400 transition-colors cursor-pointer">
              Выйти
            </button>
          </div>
          
          <div v-else class="flex items-center gap-4 ml-4">
            <a href="https://pitchy.pro/login" class="text-sm font-medium text-zinc-400 hover:text-white transition-colors">
              Войти
            </a>
            <a href="https://pitchy.pro/login" class="px-5 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium transition-all shadow-[0_0_20px_rgba(139,92,246,0.3)]">
              Начать
            </a>
          </div>
        </nav>

        <!-- Mobile Menu Button -->
        <button 
          @click="toggleMobileMenu"
          class="md:hidden p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800/50 transition-colors"
        >
          <X v-if="isMobileMenuOpen" class="w-6 h-6" />
          <Menu v-else class="w-6 h-6" />
        </button>
      </div>
    </div>
  </header>

  <!-- Mobile Menu Overlay -->
  <Transition
    enter-active-class="transition duration-200 ease-out"
    enter-from-class="opacity-0 -translate-y-4"
    enter-to-class="opacity-100 translate-y-0"
    leave-active-class="transition duration-150 ease-in"
    leave-from-class="opacity-100 translate-y-0"
    leave-to-class="opacity-0 -translate-y-4"
  >
    <div v-if="isMobileMenuOpen" class="fixed inset-x-0 top-20 z-40 md:hidden bg-zinc-950/95 backdrop-blur-xl border-b border-zinc-800 p-4 space-y-4">
      <nav class="flex flex-col gap-1">
        <a
          v-for="link in navLinks"
          :key="link.href"
          :href="link.href"
          class="block px-4 py-3 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800/50 transition-colors"
        >
          {{ link.label }}
        </a>
      </nav>
      
      <div class="pt-4 border-t border-zinc-800">
        <div v-if="isAuthenticated" class="flex flex-col gap-2">
          <a href="https://pitchy.pro/account" class="block px-4 py-3 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800/50">
            Аккаунт
          </a>
          <button @click="handleLogout" class="w-full text-left px-4 py-3 rounded-lg text-red-400 hover:bg-red-400/10 transition-colors">
            Выйти
          </button>
        </div>
        <div v-else class="flex flex-col gap-4 p-2">
          <a href="https://pitchy.pro/login" class="text-center py-3 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800/50">
            Войти
          </a>
          <a href="https://pitchy.pro/login" class="text-center py-3 rounded-xl bg-violet-600 text-white font-medium">
            Начать
          </a>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
/* Scoped styles if needed, but mostly using Tailwind classes */
</style>
