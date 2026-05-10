<template>
  <div class="min-h-screen flex flex-col bg-black text-on-background font-sans">
    <div class="relative z-10 flex flex-col h-screen overflow-hidden">
      <Navbar />

      <main class="flex-1 flex flex-col min-h-0 pt-20">
        <slot></slot>
      </main>
    </div>
  </div>
</template>

<script setup>
import Navbar from './Navbar.vue'
</script>
