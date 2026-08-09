<script setup>
import { ref, onMounted } from 'vue'
import { Menu, X } from 'lucide-vue-next'
import { getMe } from '../../api/auth'

const isMobileMenuOpen = ref(false)
const isAuthenticated = ref(false)

const navLinks = [
  { label: 'Главная', href: 'https://pitchy.pro/' },
  { label: 'Дашборд', href: 'https://pitchy.pro/dashboard' },
  { label: 'FAQ', href: 'https://pitchy.pro/faq' },
  { label: 'О нас', href: 'https://pitchy.pro/about' },
  { label: 'Тарифы', href: 'https://pitchy.pro/pricing' },
  { label: 'Контакты', href: 'https://pitchy.pro/contact' },
]

onMounted(async () => {
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
  <header class="fixed top-0 left-0 right-0 z-[100] w-full bg-black/95 backdrop-blur-xl border-b border-white/5">
    <div class="flex flex-row justify-between items-center py-4 px-8 w-full max-w-[1440px] mx-auto">
      <!-- Logo -->
      <a href="https://pitchy.pro/" class="flex items-center gap-2 relative z-[110]">
        <img src="/icon.png" alt="Pitchy" class="w-7 h-7 object-contain invert" />
        <span class="font-display tracking-tight text-white inline-flex items-baseline text-xl">
          Pitchy<span class="text-white/30 italic">.pro</span>
        </span>
      </a>

      <!-- Desktop nav (centered) -->
      <nav class="hidden md:flex items-center gap-8 absolute left-1/2 -translate-x-1/2">
        <a
          v-for="link in navLinks"
          :key="link.href"
          :href="link.href"
          class="flex items-center gap-1 text-white/70 hover:text-white transition-colors font-medium text-[13px] uppercase tracking-tighter font-sans"
        >
          {{ link.label }}
        </a>
      </nav>

      <!-- Right -->
      <div class="hidden md:flex items-center gap-4 relative z-[110]">
        <template v-if="isAuthenticated">
          <a
            href="https://pitchy.pro/account"
            class="text-white/70 hover:text-white text-[12px] font-medium uppercase tracking-tighter font-sans mr-2"
          >
            АККАУНТ
          </a>
          <button
            @click="handleLogout"
            class="bg-white text-black px-6 py-2 rounded-full text-[12px] font-bold uppercase tracking-tight font-sans hover:bg-neutral-200 transition-colors cursor-pointer"
          >
            ВЫЙТИ
          </button>
        </template>
        <template v-else>
          <a
            href="https://pitchy.pro/login"
            class="text-white/70 hover:text-white text-[12px] font-medium uppercase tracking-tighter font-sans mr-4"
          >
            ВОЙТИ
          </a>
          <a
            href="https://pitchy.pro/login"
            class="bg-white text-black px-6 py-2 rounded-full text-[12px] font-bold uppercase tracking-tight font-sans hover:bg-neutral-200 transition-colors shadow-[0_0_20px_rgba(255,255,255,0.1)]"
          >
            РЕГИСТРАЦИЯ
          </a>
        </template>
      </div>

      <!-- Mobile burger -->
      <button
        @click="toggleMobileMenu"
        class="md:hidden text-white/80 hover:text-white ml-2"
        aria-label="Меню"
      >
        <X v-if="isMobileMenuOpen" :size="24" />
        <Menu v-else :size="24" />
      </button>
    </div>

    <!-- Mobile menu overlay -->
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0 -translate-y-4"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 -translate-y-4"
    >
      <div v-if="isMobileMenuOpen" class="absolute top-full left-0 right-0 bg-black/95 backdrop-blur-xl border-b border-white/10 p-8 md:hidden">
        <nav class="flex flex-col gap-6 items-center">
          <a
            v-for="link in navLinks"
            :key="link.href"
            :href="link.href"
            class="text-xl font-medium text-white/80 hover:text-white uppercase tracking-tighter font-sans"
          >
            {{ link.label }}
          </a>
          <div class="flex flex-col gap-4 w-full mt-4">
            <template v-if="isAuthenticated">
              <a href="https://pitchy.pro/account" class="text-center text-white/70 text-lg font-medium font-sans">АККАУНТ</a>
              <button
                @click="handleLogout"
                class="bg-white text-black text-center py-4 rounded-full font-bold uppercase tracking-tight font-sans"
              >
                ВЫЙТИ
              </button>
            </template>
            <template v-else>
              <a href="https://pitchy.pro/login" class="text-center text-white/70 text-lg font-medium font-sans">ВОЙТИ</a>
              <a href="https://pitchy.pro/login" class="bg-white text-black text-center py-4 rounded-full font-bold uppercase tracking-tight font-sans">РЕГИСТРАЦИЯ</a>
            </template>
          </div>
        </nav>
      </div>
    </Transition>
  </header>
</template>
