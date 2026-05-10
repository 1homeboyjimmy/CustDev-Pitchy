<template>
  <div
    class="overflow-hidden rounded-2xl"
    :class="[
      strong ? 'liquid-glass-strong' : 'liquid-glass',
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
  },
  strong: {
    type: Boolean,
    default: false
  }
})
</script>
