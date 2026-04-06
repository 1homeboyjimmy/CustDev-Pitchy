<template>
  <div class="min-h-screen flex flex-col bg-pitchy-bg text-foreground font-sans selection:bg-pitchy-violet/30 selection:text-white">
    <!-- Main Background Gradients -->
    <div class="fixed inset-0 z-0 overflow-hidden pointer-events-none">
      <div class="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-pitchy-violet/10 blur-[120px] rounded-full"></div>
      <div class="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-pitchy-cyan/10 blur-[120px] rounded-full"></div>
      <div class="absolute inset-0 grid-pattern opacity-10"></div>
    </div>

    <!-- Layout Shell -->
    <div class="relative z-10 flex flex-col h-screen overflow-hidden">
      <Navbar />
      
      <main class="flex-1 flex flex-col min-h-0 pt-20">
        <slot></slot>
      </main>

      <!-- Optional Footer or Status bar could go here -->
    </div>
  </div>
</template>

<script setup>
import Navbar from './Navbar.vue'
</script>
