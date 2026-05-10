<script setup>
import { ref, onMounted } from 'vue'
import { Menu, X, User } from 'lucide-vue-next'
import { getMe } from '../../api/auth'

const isScrolled = ref(false)
const isMobileMenuOpen = ref(false)
const isAuthenticated = ref(false)

const navLinks = [
  { label: 'ДАШБОРД', href: 'https://pitchy.pro/dashboard' },
  { label: 'FAQ', href: 'https://pitchy.pro/faq' },
  { label: 'О НАС', href: 'https://pitchy.pro/about' },
  { label: 'ТАРИФЫ', href: 'https://pitchy.pro/pricing' },
  { label: 'КОНТАКТЫ', href: 'https://pitchy.pro/contact' },
]

onMounted(async () => {
  window.addEventListener('scroll', () => {
    isScrolled.value = window.scrollY > 20
  })

  try {
    const response = await getMe()
    if (response.success) {
      isAuthenticated.value = true
    }
  } catch (error) {
    console.debug('Not authenticated')
    isAuthenticated.value = false
  }
})

const handleLogout = () => {
  document.cookie = 'access_token=; path=/; domain=.pitchy.pro; expires=Thu, 01 Jan 1970 00:00:01 GMT;'
  window.location.href = 'https://pitchy.pro/login'
}

const toggleMobileMenu = () => {
  isMobileMenuOpen.value = !isMobileMenuOpen.value
}
</script>

<template>
  <header
    :class="[
      'fixed top-0 left-0 right-0 z-50 transition-all duration-300 w-full',
      isScrolled || isMobileMenuOpen ? 'bg-background/80 backdrop-blur-xl' : 'bg-transparent'
    ]"
  >
    <div class="flex flex-row justify-between items-center py-5 px-6 md:px-8 w-full max-w-[1440px] mx-auto">
      <!-- Logo -->
      <a href="https://pitchy.pro" class="flex items-center gap-2 relative z-[110]">
        <span class="text-white font-bold text-2xl tracking-tighter font-display uppercase">
          PITCHY<span class="text-white/70">.</span>PRO
        </span>
        <span class="ml-2 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-widest bg-white/5 text-white/70 border border-white/10 font-display">
          CustDev
        </span>
      </a>

      <!-- Desktop Nav Centered -->
      <nav class="hidden md:flex items-center gap-8 absolute left-1/2 -translate-x-1/2">
        <a
          v-for="link in navLinks"
          :key="link.href"
          :href="link.href"
          class="flex items-center gap-1 text-white/80 hover:text-white transition-colors font-bold text-[12px] uppercase tracking-widest font-display"
        >
          {{ link.label }}
        </a>
      </nav>

      <!-- Auth Buttons -->
      <div class="hidden md:flex items-center gap-4 relative z-[110]">
        <template v-if="isAuthenticated">
          <a href="https://pitchy.pro/account" class="text-white/70 hover:text-white transition-colors">
            <User class="w-5 h-5" />
          </a>
          <button
            @click="handleLogout"
            class="text-[12px] font-bold uppercase tracking-widest text-white/70 hover:text-white transition-colors cursor-pointer font-display"
          >
            ВЫЙТИ
          </button>
        </template>

        <template v-else>
          <a href="https://pitchy.pro/login" class="text-white/70 hover:text-white text-[12px] font-bold uppercase tracking-widest font-display">
            ВОЙТИ
          </a>
          <a
            href="https://pitchy.pro/login"
            class="liquid-glass-strong text-white px-6 py-2 rounded-full text-[12px] font-black uppercase tracking-widest hover:scale-105 transition-transform font-display"
          >
            НАЧАТЬ
          </a>
        </template>
      </div>

      <!-- Mobile Menu Button -->
      <button
        @click="toggleMobileMenu"
        class="md:hidden p-2 rounded-lg text-white/70 hover:text-white transition-colors"
      >
        <X v-if="isMobileMenuOpen" class="w-6 h-6" />
        <Menu v-else class="w-6 h-6" />
      </button>
    </div>

    <!-- Subtle gradient divider -->
    <div class="w-full h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />

    <!-- Mobile Menu Overlay -->
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0 -translate-y-4"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 -translate-y-4"
    >
      <div v-if="isMobileMenuOpen" class="absolute top-full left-0 right-0 bg-background/95 backdrop-blur-xl border-b border-white/10 p-8 md:hidden">
        <nav class="flex flex-col gap-6 items-center">
          <a
            v-for="link in navLinks"
            :key="link.href"
            :href="link.href"
            class="text-2xl font-bold text-white/80 hover:text-white uppercase tracking-widest font-display"
          >
            {{ link.label }}
          </a>

          <div class="flex flex-col gap-4 w-full mt-4">
            <template v-if="isAuthenticated">
              <a href="https://pitchy.pro/account" class="text-center text-white/70 text-lg font-bold uppercase tracking-widest font-display">
                АККАУНТ
              </a>
              <button
                @click="handleLogout"
                class="liquid-glass-strong text-white text-center py-4 rounded-full font-black uppercase tracking-widest font-display"
              >
                ВЫЙТИ
              </button>
            </template>
            <template v-else>
              <a href="https://pitchy.pro/login" class="text-center text-white/70 text-lg font-bold uppercase tracking-widest font-display">
                ВОЙТИ
              </a>
              <a href="https://pitchy.pro/login" class="liquid-glass-strong text-white text-center py-4 rounded-full font-black uppercase tracking-widest font-display">
                НАЧАТЬ
              </a>
            </template>
          </div>
        </nav>
      </div>
    </Transition>
  </header>
</template>
