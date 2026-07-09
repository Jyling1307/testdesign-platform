<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'

interface SearchResult {
  content: string
  source: string
  source_type: string
  heading: string
  collection: string
  score: number
}

// source_type → 展示标签
const TYPE_LABEL: Record<string, string> = {
  code: '📦 代码图谱',
  design_doc: '📄 设计文档',
  test_design: '📝 测试设计',
  document: '📄 设计文档',
  testcase: '🧪 测试用例',
}

const route = useRoute()
const projectId = computed(() => Number(route.params.id))
const query = ref('')
const results = ref<SearchResult[]>([])
const searching = ref(false)
const errorMsg = ref('')
const hasSearched = ref(false)
const aiAnswer = ref('')
const aiThinking = ref(false)

async function search() {
  if (!query.value.trim()) return
  searching.value = true
  errorMsg.value = ''
  hasSearched.value = true
  aiAnswer.value = ''
  aiThinking.value = false
  results.value = []
  try {
    const resp = await fetch('/api/knowledge/ask/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project: String(projectId.value), query: query.value, top_k: 10 }),
    })
    if (!resp.ok || !resp.body) {
      errorMsg.value = `后端返回 HTTP ${resp.status}`
      return
    }
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      // SSE 事件以空行分隔
      const events = buffer.split('\n\n')
      buffer = events.pop() || ''
      for (const evt of events) {
        const line = evt.trim()
        if (!line.startsWith('data:')) continue
        let payload: any
        try {
          payload = JSON.parse(line.slice(5).trim())
        } catch {
          continue
        }
        if (payload.type === 'results') {
          results.value = payload.results || []
        } else if (payload.type === 'chunk') {
          aiThinking.value = true
          aiAnswer.value += payload.content
        } else if (payload.type === 'error') {
          errorMsg.value = payload.message
        }
      }
    }
  } catch (err: any) {
    console.error('[知识问答] 请求失败:', err)
    if (!errorMsg.value) errorMsg.value = err.message || '网络错误'
  } finally {
    searching.value = false
    aiThinking.value = false
  }
}
</script>

<template>
  <div class="knowledge-search">
    <h3>知识库语义检索</h3>
    <div class="search-bar">
      <input v-model="query" placeholder="输入问题，AI 将检索知识库（设计文档+代码图谱+测试用例）并综合回答..." class="input" @keyup.enter="search" />
      <button class="btn btn-primary" @click="search" :disabled="searching || !query.trim()">
        {{ searching ? '检索中...' : '检索' }}
      </button>
    </div>

    <div v-if="errorMsg" class="error">⚠ {{ errorMsg }}</div>

    <!-- AI 综合回答区 -->
    <div v-if="aiAnswer || (searching && !errorMsg)" class="card ai-answer">
      <div class="ai-header">
        <span>🤖 AI 综合回答</span>
        <span v-if="aiThinking" class="ai-cursor">▊</span>
      </div>
      <div class="ai-body">{{ aiAnswer || '正在检索知识库并思考...' }}</div>
    </div>

    <!-- 片段列表 -->
    <div v-if="results.length > 0" class="results">
      <div class="results-title">📚 知识库片段（{{ results.length }}）</div>
      <div v-for="(r, i) in results" :key="i" class="card result-item">
        <div class="result-header">
          <div class="result-tags">
            <span class="tag tag-type">{{ TYPE_LABEL[r.source_type] || r.source_type || '未知' }}</span>
            <span class="source">{{ r.source || `片段 #${i + 1}` }}</span>
          </div>
          <span class="score">相似度 {{ (r.score * 100).toFixed(0) }}%</span>
        </div>
        <p v-if="r.heading" class="heading">{{ r.heading }}</p>
        <p class="result-content">{{ r.content }}</p>
      </div>
    </div>
    <div v-else-if="searching && !aiAnswer" class="empty">检索中...</div>
    <div v-else-if="errorMsg && !results.length" class="empty">请求失败，详见上方红字</div>
    <div v-else-if="hasSearched && !aiAnswer" class="empty">未找到相关内容</div>
    <div v-else class="empty">输入问题开始检索（projectId = {{ projectId }}）</div>
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

/* AI 回答区 */
.ai-answer { border-color: #e94560; background: linear-gradient(135deg, #1a1a3e 0%, #16213e 100%); }
.ai-header { color: #e94560; font-weight: 600; margin-bottom: 0.5rem; font-size: 0.95rem; }
.ai-cursor { animation: blink 1s step-end infinite; color: #e94560; }
.ai-body { color: #ddd; font-size: 0.92rem; line-height: 1.75; white-space: pre-wrap; word-break: break-word; }
@keyframes blink { 50% { opacity: 0; } }

/* 片段列表 */
.results-title { color: #888; font-size: 0.85rem; margin: 0.5rem 0; }
.result-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; gap: 0.5rem; }
.result-tags { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.tag { padding: 0.1rem 0.5rem; border-radius: 4px; font-size: 0.72rem; }
.tag-type { background: #2a4a6a; color: #8ab4f8; border: 1px solid #3a5a7a; }
.source { color: #e94560; font-size: 0.82rem; }
.score { color: #666; font-size: 0.78rem; white-space: nowrap; }
.heading { color: #aaa; font-size: 0.8rem; margin: 0 0 0.3rem; font-style: italic; }
.result-content { color: #ccc; font-size: 0.88rem; margin: 0; line-height: 1.6; }

.empty { text-align: center; padding: 2rem; color: #666; }
.error { background: #3a1530; border: 1px solid #e94560; color: #ffb3c1; padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.85rem; word-break: break-all; }
</style>
