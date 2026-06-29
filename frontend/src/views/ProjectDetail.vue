<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectStore } from '../stores/project'

const route = useRoute()
const store = useProjectStore()
const projectId = computed(() => Number(route.params.id))

onMounted(() => store.fetchProject(projectId.value))
</script>

<template>
  <div class="project-detail">
    <div v-if="store.loading">加载中...</div>
    <div v-else-if="store.current">
      <h2>{{ store.current.name }}</h2>
      <p class="desc">{{ store.current.description || '暂无描述' }}</p>
      <router-view />
    </div>
  </div>
</template>

<style scoped>
h2 { margin: 0 0 0.5rem; }
.desc { color: #888; margin-bottom: 1.5rem; }
</style>
