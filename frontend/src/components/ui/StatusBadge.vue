<template>
  <div
    class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest border transition-all duration-300 font-display"
    :class="variants[type]"
  >
    <div v-if="dot" class="w-1 h-1 rounded-full animate-pulse bg-current"></div>
    <slot></slot>
  </div>
</template>

<script setup>
defineProps({
  type: {
    type: String,
    default: 'default',
    validator: (v) => ['default', 'primary', 'cyan', 'success', 'warning', 'danger'].includes(v)
  },
  dot: {
    type: Boolean,
    default: true
  }
})

const variants = {
  default: 'bg-white/5 border-white/10 text-white/70',
  primary: 'bg-white/10 border-white/20 text-white',
  cyan: 'bg-white/8 border-white/15 text-white/85',
  success: 'bg-emerald-500/10 border-emerald-500/25 text-emerald-300',
  warning: 'bg-amber-500/10 border-amber-500/25 text-amber-300',
  danger: 'bg-red-500/10 border-red-500/25 text-red-300'
}
</script>
