<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { knowledgeApi } from '../api'

const route = useRoute()
const projectId = computed(() => Number(route.params.id))
const query = ref('')
const results = ref<Array<{ id: number; content: string; source: string; score: number }>>([])
const searching = ref(false)

async function search() {
  if (!query.value.trim()) return
  searching.value = true
  try {
    const { data } = await knowledgeApi.search(projectId.value, query.value)
    results.value = data.results || data || []
  } catch {
    results.value = []
  } finally {
    searching.value = false
  }
}
</script>

<template>
  <div class="knowledge-search">
    <h3>知识库语义检索</h3>
    <div class="search-bar">
      <input v-model="query" placeholder="输入检索关键词，AI 将进行语义匹配..." class="input" @keyup.enter="search" />
      <button class="btn btn-primary" @click="search" :disabled="searching || !query.trim()">
        {{ searching ? '检索中...' : '检索' }}
      </button>
    </div>

    <div v-if="results.length > 0" class="results">
      <div v-for="(r, i) in results" :key="r.id || i" class="card result-item">
        <div class="result-header">
          <span class="source">{{ r.source || `片段 #${i + 1}` }}</span>
          <span class="score">相似度: {{ (r.score * 100).toFixed(0) }}%</span>
        </div>
        <p class="result-content">{{ r.content }}</p>
      </div>
    </div>
    <div v-else-if="!searching && query" class="empty">未找到相关内容</div>
    <div v-else class="empty">输入关键词开始检索知识库</div>
  </div>
</template>

<style scoped>
h3 { margin: 0 0 1rem; }
.search-bar { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
.input { flex: 1; padding: 0.5rem 0.75rem; background: #0f3460; border: 1px solid #2a2a4a; border-radius: 6px; color: #eee; font-size: 0.9rem; }
.btn { padding: 0.5rem 1rem; border: 1px solid #3a3a5a; background: transparent; color: #ccc; border-radius: 6px; cursor: pointer; }
.btn-primary { background: #e94560; border-color: #e94560; color: #fff; }
.btn-primary:disabled { opacity: 0.6; }
.card { background: #16213e; border: 1px solid #2a2a4a; border-radius: 8px; padding: 1rem; margin-bottom: 0.5rem; }
.result-header { display: flex; justify-content: space-between; margin-bottom: 0.5rem; }
.source { color: #e94560; font-size: 0.85rem; }
.score { color: #666; font-size: 0.8rem; }
.result-content { color: #ccc; font-size: 0.9rem; margin: 0; line-height: 1.6; }
.empty { text-align: center; padding: 2rem; color: #666; }
</style>
