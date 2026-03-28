<template>
  <div 
    class="glass-card overflow-hidden" 
    :class="[
      hover ? 'glass-card-hover' : '',
      padding ? 'p-6' : 'p-0'
    ]"
  >
    <slot></slot>
  </div>
</template>

<script setup>
defineProps({
  hover: {
    type: Boolean,
    default: false
  },
  padding: {
    type: Boolean,
    default: true
  }
})
</script>
