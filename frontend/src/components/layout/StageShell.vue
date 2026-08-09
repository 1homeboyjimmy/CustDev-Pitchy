<script setup>
import SideNavBar from './SideNavBar.vue'

defineProps({
  activeId: {
    type: String,
    default: 'custdev',
  },
})
</script>

<template>
  <div class="fixed inset-0 pt-20 pb-16 lg:pb-0 flex bg-black z-10 overflow-hidden">
    <SideNavBar :active-id="activeId" />
    <div class="flex-1 flex flex-col overflow-hidden min-w-0">
      <slot></slot>
    </div>
  </div>
</template>
