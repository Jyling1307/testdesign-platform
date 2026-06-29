<script setup lang="ts">
import { useRoute } from 'vue-router'
import { computed } from 'vue'

const route = useRoute()
const projectId = computed(() => route.params.id as string | undefined)
</script>

<template>
  <div id="app-layout">
    <header class="app-header">
      <router-link to="/" class="logo">TestDesignAI</router-link>
      <nav v-if="projectId" class="sub-nav">
        <router-link :to="`/project/${projectId}/documents`">文档管理</router-link>
        <router-link :to="`/project/${projectId}/designs`">测试设计</router-link>
        <router-link :to="`/project/${projectId}/knowledge`">知识检索</router-link>
      </nav>
    </header>
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  gap: 2rem;
  padding: 0.75rem 1.5rem;
  background: #1a1a2e;
  border-bottom: 1px solid #2a2a4a;
}

.logo {
  font-size: 1.25rem;
  font-weight: 700;
  color: #e94560;
  text-decoration: none;
}

.sub-nav {
  display: flex;
  gap: 1rem;
}

.sub-nav a {
  color: #a0a0b0;
  text-decoration: none;
  font-size: 0.9rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}

.sub-nav a.router-link-active {
  color: #fff;
  background: rgba(233, 69, 96, 0.15);
}

.app-main {
  padding: 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
}
</style>
