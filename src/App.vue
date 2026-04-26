<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()
</script>

<template>
  <div class="app">
    <header class="header">
      <span class="header-title">msgvault</span>
      <div class="header-right">
        <nav class="header-nav">
          <router-link to="/" :class="{ active: route.name === 'dashboard' }">Dashboard</router-link>
          <router-link to="/browse" :class="{ active: route.name === 'browse' }">Browse</router-link>
          <router-link to="/search" :class="{ active: route.name === 'search' }">Search</router-link>
        </nav>
      </div>
    </header>
    <router-view />
    <footer class="footer">
      msgvault
      <span style="margin-left: 8px; opacity: 0.6;"><kbd>?</kbd> shortcuts</span>
    </footer>
  </div>
</template>
