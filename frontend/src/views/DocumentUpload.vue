<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useDocumentStore } from '../stores/document'

const route = useRoute()
const store = useDocumentStore()
const projectId = computed(() => Number(route.params.id))
const fileInput = ref<HTMLInputElement | null>(null)

onMounted(() => store.fetchDocuments(projectId.value))

function triggerUpload() {
  fileInput.value?.click()
}

async function handleFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) {
    await store.uploadDocument(projectId.value, file)
    if (fileInput.value) fileInput.value.value = ''
  }
}

function getStatusLabel(status: string) {
  const map: Record<string, string> = {
    uploaded: '已上传', parsing: '解析中', parsed: '已解析',
    embedded: '已入库', error: '错误',
  }
  return map[status] || status
}

function getStatusClass(status: string) {
  return status
}
</script>

<template>
  <div class="doc-upload">
    <div class="page-header">
      <h3>文档管理</h3>
      <button class="btn btn-primary" @click="triggerUpload" :disabled="store.uploading">
        {{ store.uploading ? `上传中 ${store.uploadProgress}%` : '+ 上传文档' }}
      </button>
    </div>
    <input ref="fileInput" type="file" accept=".docx,.pdf,.md" style="display:none" @change="handleFile" />

    <div v-if="store.documents.length === 0" class="empty">暂无文档，点击上方按钮上传</div>
    <div v-else class="doc-list">
      <div v-for="doc in store.documents" :key="doc.id" class="card doc-item">
        <div class="doc-info">
          <span class="doc-name">{{ doc.title }}</span>
          <span class="doc-meta">{{ doc.file_size ? (doc.file_size / 1024).toFixed(1) + ' KB' : doc.file_type.toUpperCase() }}</span>
        </div>
        <div class="doc-right">
          <span class="status" :class="getStatusClass(doc.status)">{{ getStatusLabel(doc.status) }}</span>
          <button class="btn-sm danger" @click="store.deleteDocument(doc.id, projectId)">删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.page-header h3 { margin: 0; }
.btn { padding: 0.4rem 0.8rem; border: 1px solid #3a3a5a; background: transparent; color: #ccc; border-radius: 6px; cursor: pointer; }
.btn-primary { background: #e94560; border-color: #e94560; color: #fff; }
.btn-primary:disabled { opacity: 0.6; }
.empty { text-align: center; padding: 2rem; color: #888; }
.doc-list { display: flex; flex-direction: column; gap: 0.5rem; }
.card { background: #16213e; border: 1px solid #2a2a4a; border-radius: 8px; padding: 0.75rem 1rem; }
.doc-item { display: flex; justify-content: space-between; align-items: center; }
.doc-info { display: flex; flex-direction: column; gap: 0.2rem; }
.doc-name { color: #eee; font-size: 0.9rem; word-break: break-all; }
.doc-meta { color: #666; font-size: 0.8rem; }
.doc-right { display: flex; align-items: center; gap: 0.75rem; }
.status { font-size: 0.8rem; padding: 0.15rem 0.5rem; border-radius: 4px; }
.status.embedded, .status.parsed { background: rgba(16, 185, 129, 0.15); color: #10b981; }
.status.parsing { background: rgba(59, 130, 246, 0.15); color: #3b82f6; }
.status.uploaded { background: rgba(148, 163, 184, 0.15); color: #94a3b8; }
.status.error { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
.btn-sm { padding: 0.2rem 0.5rem; border: none; background: transparent; color: #888; cursor: pointer; border-radius: 4px; font-size: 0.8rem; }
.btn-sm.danger:hover { color: #ef4444; }
</style>
