<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectStore } from '../stores/project'
import { projectApi } from '../api'

const store = useProjectStore()
const router = useRouter()
const showCreate = ref(false)
const newName = ref('')
const newProduct = ref('')
const newDesc = ref('')

onMounted(() => store.fetchProjects())

async function createProject() {
  if (!newName.value.trim()) return
  await projectApi.create({ name: newName.value.trim(), product: newProduct.value.trim(), description: newDesc.value.trim() })
  newName.value = ''
  newProduct.value = ''
  newDesc.value = ''
  showCreate.value = false
  await store.fetchProjects()
}

function openProject(id: number) {
  router.push(`/project/${id}`)
}
</script>

<template>
  <div class="project-list">
    <div class="page-header">
      <h1>测试项目</h1>
      <button class="btn btn-primary" @click="showCreate = !showCreate">+ 新建项目</button>
    </div>

    <div v-if="showCreate" class="card create-form">
      <input v-model="newName" placeholder="项目名称" class="input" @keyup.enter="createProject" />
      <input v-model="newProduct" placeholder="所属产品（如 IDM V5）" class="input" />
      <textarea v-model="newDesc" placeholder="项目描述（可选）" class="input" rows="2" />
      <div class="form-actions">
        <button class="btn btn-primary" @click="createProject" :disabled="!newName.trim()">创建</button>
        <button class="btn" @click="showCreate = false">取消</button>
      </div>
    </div>

    <div v-if="store.loading" class="loading">加载中...</div>
    <div v-else-if="store.projects.length === 0" class="empty">
      <p>还没有项目，点击上方按钮创建第一个吧！</p>
    </div>
    <div v-else class="project-grid">
      <div v-for="p in store.projects" :key="p.id" class="card project-card" @click="openProject(p.id)">
        <h3>{{ p.name }}</h3>
        <span v-if="p.product" class="product-tag">{{ p.product }}</span>
        <p class="desc">{{ p.description || '暂无描述' }}</p>
        <span class="date">{{ new Date(p.created_at).toLocaleDateString('zh-CN') }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}
.page-header h1 { margin: 0; }
.btn {
  padding: 0.5rem 1rem;
  border: 1px solid #3a3a5a;
  background: transparent;
  color: #ccc;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
}
.btn:hover { border-color: #e94560; color: #e94560; }
.btn-primary { background: #e94560; border-color: #e94560; color: #fff; }
.btn-primary:hover { background: #d63851; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.card {
  background: #16213e;
  border: 1px solid #2a2a4a;
  border-radius: 8px;
  padding: 1.25rem;
  margin-bottom: 1rem;
}
.create-form { display: flex; flex-direction: column; gap: 0.75rem; }
.input {
  padding: 0.5rem 0.75rem;
  background: #0f3460;
  border: 1px solid #2a2a4a;
  border-radius: 6px;
  color: #eee;
  font-size: 0.9rem;
  resize: vertical;
}
.form-actions { display: flex; gap: 0.5rem; }
.project-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; }
.project-card { cursor: pointer; transition: border-color 0.2s; }
.project-card:hover { border-color: #e94560; }
.project-card h3 { margin: 0 0 0.5rem; color: #eee; }
.product-tag { display: inline-block; background: rgba(233, 69, 96, 0.15); color: #e94560; font-size: 0.75rem; padding: 0.1rem 0.5rem; border-radius: 4px; margin-bottom: 0.5rem; }
.project-card .desc { margin: 0 0 0.75rem; color: #888; font-size: 0.85rem; }
.project-card .date { font-size: 0.75rem; color: #666; }
.loading, .empty { text-align: center; padding: 3rem; color: #888; }
</style>
