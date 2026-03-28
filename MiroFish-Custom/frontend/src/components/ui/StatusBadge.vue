<template>
  <div 
    class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border transition-all duration-300 shadow-[0_0_15px_rgba(0,0,0,0.2)]"
    :class="variants[type]"
  >
    <div v-if="dot" class="w-1 h-1 rounded-full animate-pulse shadow-glow shadow-current bg-current"></div>
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
  default: 'bg-white/5 border-white/10 text-white/60',
  primary: 'bg-pitchy-violet/15 border-pitchy-violet/30 text-pitchy-violet-light shadow-[0_0_15px_rgba(139,92,246,0.15)]',
  cyan: 'bg-pitchy-cyan/15 border-pitchy-cyan/30 text-pitchy-cyan-light shadow-[0_0_15px_rgba(6,182,212,0.15)]',
  success: 'bg-pitchy-score-green/15 border-pitchy-score-green/30 text-pitchy-score-green shadow-[0_0_15px_rgba(16,185,129,0.15)]',
  warning: 'bg-pitchy-score-yellow/15 border-pitchy-score-yellow/30 text-pitchy-score-yellow shadow-[0_0_15px_rgba(245,158,11,0.15)]',
  danger: 'bg-pitchy-score-red/15 border-pitchy-score-red/30 text-pitchy-score-red shadow-[0_0_15px_rgba(239,68,68,0.15)]'
}
</script>
