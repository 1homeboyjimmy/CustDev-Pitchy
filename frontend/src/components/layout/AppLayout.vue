<template>
  <div class="min-h-screen flex flex-col bg-background text-on-background font-sans">
    <!-- Aurora background -->
    <div class="fixed inset-0 z-0 overflow-hidden pointer-events-none aurora-bg">
      <div class="aurora-orb animate-float-slow" style="top: -10%; left: -10%; width: 40%; height: 40%; background: radial-gradient(circle, rgba(255,255,255,0.08), transparent 60%);"></div>
      <div class="aurora-orb animate-float-slow" style="bottom: -10%; right: -10%; width: 40%; height: 40%; background: radial-gradient(circle, rgba(255,255,255,0.05), transparent 60%); animation-delay: -4s;"></div>
      <div class="absolute inset-0 grid-pattern opacity-[0.04]"></div>
    </div>

    <!-- Layout Shell -->
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
