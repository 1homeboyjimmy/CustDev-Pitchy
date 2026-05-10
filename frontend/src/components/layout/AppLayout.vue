<template>
  <div class="min-h-screen bg-black text-on-background font-sans">
    <Navbar />
    <main class="pt-20">
      <slot></slot>
    </main>
  </div>
</template>

<script setup>
import Navbar from './Navbar.vue'
</script>
