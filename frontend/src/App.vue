<template>
  <div class="min-h-screen bg-pitchy-bg">
    <Navbar />
    <main class="pt-20">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import Navbar from './components/layout/Navbar.vue'
/**
 * Pitchy-Offline Frontend
 * Redesigned with Tailwind CSS v4 and Pitchy Design System
 */
</script>

<style>
/* 
  Global styles are now managed in src/assets/globals.css 
  using Tailwind CSS v4 design tokens.
*/
</style>

