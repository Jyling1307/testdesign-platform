<script setup lang="ts">
import { onMounted, ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useTestDesignStore } from '../stores/testDesign'
import { useDocumentStore } from '../stores/document'
import { testDesignApi } from '../api'
import { parseMarkdownToTree } from '../utils/websocket'

const route = useRoute()
const store = useTestDesignStore()
const docStore = useDocumentStore()
const projectId = computed(() => Number(route.params.id))
const showCreate = ref(false)
const selectedDocId = ref<number | null>(null)
const feedbackText = ref('')
const displayMode = ref<'md' | 'tree'>('md')

const ALL_TEST_TYPES = [
  '功能测试', '性能基线测试', '性能极限测试', '业务影响性能测试',
  '可靠性测试', '升级测试', '压力测试', '长稳测试',
  '功能交互', '场景测试', '兼容性', '自动化测试', '易用性测试',
]
const selectedTypes = ref<string[]>([...ALL_TEST_TYPES])
const showTypePicker = ref(false)

// ── 逐节点审阅状态 ──
type ReviewStatus = 'pending' | 'approved' | 'rejected'
const nodeReviews = ref<Record<string, ReviewStatus>>({})
const nodeEdits = ref<Record<string, string>>({})
const editingNode = ref<string | null>(null)

const isReviewing = computed(() => store.current?.status === 'reviewing')

function toggleReview(path: string) {
  const current = nodeReviews.value[path] || 'pending'
  const next: Record<ReviewStatus, ReviewStatus> = { pending: 'approved', approved: 'rejected', rejected: 'pending' }
  nodeReviews.value[path] = next[current]
}

function startEdit(path: string) {
  editingNode.value = path
}

function saveEdit(path: string, newText: string) {
  if (newText.trim()) {
    nodeEdits.value[path] = newText.trim()
  }
  editingNode.value = null
}

// 构建扁平的 path→原始文本 映射（从 treeData 提取）
const flatNodeTexts = computed(() => {
  const map: Record<string, string> = {}
  const data = treeData.value
  if (!data) return map
  function walk(nodes: any[]) {
    for (const n of nodes) {
      map[n.path] = n.text
      if (n.children?.length) walk(n.children)
    }
  }
  walk(data.children)
  return map
})

// 切换设计时，从 API 返回的 reviews 恢复本地状态
watch(() => store.current, (design) => {
  if (!design) return
  nodeReviews.value = {}
  nodeEdits.value = {}
  editingNode.value = null
  const reviews: any[] = design.reviews || []
  for (const r of reviews) {
    nodeReviews.value[r.node_path] = r.status
    const original = flatNodeTexts.value[r.node_path]
    if (original && r.node_text !== original) {
      nodeEdits.value[r.node_path] = r.node_text
    }
  }
})

// AI 重新生成后清空审阅状态
watch(() => store.ws.status, (newStatus) => {
  if (newStatus === 'done' && store.current?.id) {
    nodeReviews.value = {}
    nodeEdits.value = {}
    editingNode.value = null
    store.fetchDesign(store.current.id)
    store.fetchDesigns(projectId.value)
  }
})

function toggleType(t: string) {
  const idx = selectedTypes.value.indexOf(t)
  if (idx >= 0) selectedTypes.value.splice(idx, 1)
  else selectedTypes.value.push(t)
}

function selectAllTypes() { selectedTypes.value = [...ALL_TEST_TYPES] }
function clearAllTypes() { selectedTypes.value = [] }

const treeData = computed(() => {
  const md = store.ws.fullMarkdown || store.current?.full_md || ''
  if (!md) return null
  return parseMarkdownToTree(md)
})

onMounted(() => {
  store.fetchDesigns(projectId.value)
  docStore.fetchDocuments(projectId.value)
})

watch(() => store.ws.fullMarkdown, (newMd) => {
  if (newMd) displayMode.value = 'md'
})

async function createDesign() {
  if (!selectedDocId.value) return
  const { data } = await testDesignApi.create({ project_id: projectId.value, document_id: selectedDocId.value })
  showCreate.value = false
  selectedDocId.value = null
  await store.fetchDesigns(projectId.value)
  // 自动选中新创建的 design，确保 store.current.id 有值
  if (data?.id) await store.fetchDesign(data.id)
}

function selectDesign(id: number) {
  store.fetchDesign(id)
}

async function deleteCurrentDesign() {
  console.log('[删除设计] store.current =', JSON.parse(JSON.stringify(store.current || {})))
  const id = store.current?.id
  if (!id) {
    alert('当前设计信息不完整（id 缺失），请从左侧列表重新点选一个设计后再删除')
    return
  }
  if (!confirm(`确认删除「${getDesignLabel(store.current)}」？关联的审阅记录、测试用例都会一并删除，不可恢复。`)) return
  try {
    await store.deleteDesign(id)
    await store.fetchDesigns(projectId.value)
  } catch (e: any) {
    alert('删除失败: ' + (e.response?.data?.detail || e.message))
  }
}

function getStatusLabel(status: string) {
  const map: Record<string, string> = {
    draft: '草稿', generating: '生成中', reviewing: '审阅中',
    approved: '已确认', exported: '已归库',
  }
  return map[status] || status
}

function getDesignLabel(d: any) {
  return d.document?.title || `设计 #${d.id}`
}

async function exportXlsx(id: number) {
  try {
    const res = await testDesignApi.exportXlsx(id)
    const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const match = res.headers['content-disposition']?.match(/filename="?([^";\n]+)"?/)
    a.download = match ? decodeURIComponent(match[1]) : '测试用例.xlsx'
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (e: any) {
    alert('导出失败: ' + (e.response?.data?.error || e.message))
  }
}

// ── 归入知识库对话框 ──
const showKbDialog = ref(false)
const kbMode = ref<'A' | 'B' | 'C'>('A')
const kbUploadingFile = ref<File | null>(null)
const kbPreviewCases = ref<any[]>([])
const kbPreviewLoading = ref(false)
const kbSyncing = ref(false)
const hasStoredXlsx = computed(() => !!store.current?.xlsx_file)

function openKbDialog() {
  kbMode.value = 'A'
  kbUploadingFile.value = null
  kbPreviewCases.value = []
  showKbDialog.value = true
}

async function previewKbCases() {
  if (!store.current) return
  kbPreviewLoading.value = true
  kbPreviewCases.value = []
  try {
    const res = await testDesignApi.previewXlsx(
      store.current.id,
      kbMode.value === 'C' ? 'upload' : 'stored',
      kbMode.value === 'C' ? kbUploadingFile.value! : undefined,
    )
    kbPreviewCases.value = res.data.cases
  } catch (e: any) {
    alert('预览失败: ' + (e.response?.data?.error || e.message))
  } finally {
    kbPreviewLoading.value = false
  }
}

async function confirmKbSync() {
  if (!store.current) return
  kbSyncing.value = true
  try {
    const res = await testDesignApi.syncToKb(
      store.current.id,
      kbMode.value,
      kbMode.value === 'C' ? kbUploadingFile.value! : undefined,
    )
    alert(res.data.message)
    showKbDialog.value = false
    await store.fetchDesign(store.current.id)
    await store.fetchDesigns(projectId.value)
  } catch (e: any) {
    alert('同步失败: ' + (e.response?.data?.error || e.message))
  } finally {
    kbSyncing.value = false
  }
}

// ── 提交审阅结果（先保存到 DB，再触发 AI 修改）──
const submitting = ref(false)
async function submitReview() {
  if (!store.current || submitting.value) return
  const id = store.current.id

  submitting.value = true
  try {
    // 1. 收集所有有审阅标记的节点，保存到 DB
    const reviews = Object.entries(nodeReviews.value)
      .filter(([, status]) => status !== 'pending')
      .map(([path, status]) => ({
        node_path: path,
        node_text: nodeEdits.value[path] || flatNodeTexts.value[path] || '',
        status,
        feedback: '',
      }))

    if (reviews.length > 0) {
      await testDesignApi.reviews(id, reviews)
    }

    // 2. 触发 AI 修改（consumer 从 DB 读取 rejected 节点）
    await store.refineDesign(id, feedbackText.value, [], true, selectedTypes.value)

    // 3. 清空本地审阅状态
    feedbackText.value = ''
  } catch (e: any) {
    alert('提交失败: ' + (e.response?.data?.error || e.message))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="test-design">
    <div class="page-header">
      <h3>测试设计</h3>
      <button class="btn btn-primary" @click="showCreate = !showCreate">+ 新建设计</button>
    </div>

    <div v-if="showCreate" class="card create-form">
      <label class="form-label">选择需求文档</label>
      <select v-model="selectedDocId" class="input">
        <option :value="null" disabled>请选择文档...</option>
        <option v-for="doc in docStore.documents" :key="doc.id" :value="doc.id">{{ doc.title }}</option>
      </select>
      <div class="form-actions">
        <button class="btn btn-primary" @click="createDesign" :disabled="!selectedDocId">创建</button>
        <button class="btn" @click="showCreate = false">取消</button>
      </div>
    </div>

    <div class="layout">
      <div class="design-list">
        <div v-for="d in store.designs" :key="d.id" class="card design-item" :class="{ active: store.current?.id === d.id }" @click="selectDesign(d.id)">
          <span class="design-title">{{ getDesignLabel(d) }}</span>
          <span class="status" :class="d.status">{{ getStatusLabel(d.status) }}</span>
        </div>
        <div v-if="store.designs.length === 0" class="empty guide">
          <p>还没有测试设计</p>
          <p class="guide-steps">操作步骤：</p>
          <p>1. 先到「文档管理」上传需求文档（.docx / .pdf）</p>
          <p>2. 点击上方「+ 新建设计」，选择刚上传的文档</p>
          <p>3. 创建后点击左侧列表中的设计</p>
          <p>4. 点击「AI 生成」，AI 将自动生成测试设计方案</p>
          <p>5. 在树结构中逐节点审阅，提交反馈给 AI 修改</p>
          <p>6. 确认设计 → 导出 xlsx → 归入知识库</p>
        </div>
      </div>

      <div class="design-panel">
        <template v-if="store.current">
          <div class="panel-header">
            <div>
              <h4>{{ getDesignLabel(store.current) }}</h4>
              <span class="version">v{{ store.current.version }}</span>
            </div>
            <div class="panel-actions">
              <button v-if="store.current.status === 'reviewing'" class="btn approve" @click="testDesignApi.approve(store.current!.id).then(() => store.fetchDesign(store.current!.id))">确认设计</button>
              <button v-if="store.current.status === 'approved'" class="btn" @click="exportXlsx(store.current!.id)">
                导出 xlsx
              </button>
              <button v-if="store.current.status === 'approved' || store.current.status === 'exported'" class="btn" @click="testDesignApi.revertReview(store.current!.id).then(() => store.fetchDesign(store.current!.id))">回退审阅</button>
              <button v-if="store.current.status === 'approved' || store.current.status === 'exported'" class="btn sync-kb" @click="openKbDialog()">
                归入知识库
              </button>
              <span v-if="store.current.status === 'exported'" class="kb-done">已归库</span>
              <button class="btn danger" @click="deleteCurrentDesign" :disabled="!store.current?.id">删除设计</button>
            </div>
          </div>

          <div class="toolbar">
            <button class="btn btn-primary" @click="store.generateDesign(store.current!.id, true, '', selectedTypes)" :disabled="store.generating || selectedTypes.length === 0 || !store.current?.id">
              {{ store.ws.isGenerating ? '生成中...' : 'AI 生成' }}
            </button>
            <span style="color:#888;font-size:0.7rem;margin-left:0.5rem;">[诊断 g={{Number(store.generating)}} t={{selectedTypes.length}} id={{store.current?.id ?? 'none'}} ws={{store.ws.status}}]</span>
            <div class="type-picker">
              <button class="btn" @click="showTypePicker = !showTypePicker" :class="{ active: showTypePicker }">
                测试类型 {{ selectedTypes.length }}/{{ ALL_TEST_TYPES.length }}
              </button>
              <div v-if="showTypePicker" class="type-dropdown">
                <div class="type-header">
                  <button class="btn-sm" @click="selectAllTypes">全选</button>
                  <button class="btn-sm" @click="clearAllTypes">清空</button>
                </div>
                <div v-for="t in ALL_TEST_TYPES" :key="t" class="type-option" @click="toggleType(t)">
                  <span class="type-check">{{ selectedTypes.includes(t) ? '✓' : '' }}</span>
                  <span>{{ t }}</span>
                </div>
              </div>
            </div>
            <span v-if="store.ws.statusMessage" class="ws-status">{{ store.ws.statusMessage }}</span>
            <span v-if="store.ws.errorMessage" class="ws-error">{{ store.ws.errorMessage }}</span>
          </div>

          <div class="design-content">
            <template v-if="store.ws.fullMarkdown || store.current?.full_md">
              <div class="view-toggle">
                <button class="btn" :class="{ active: displayMode === 'md' }" @click="displayMode = 'md'">Markdown</button>
                <button class="btn" :class="{ active: displayMode === 'tree' }" @click="displayMode = 'tree'">树结构</button>
              </div>
              <pre v-if="displayMode === 'md'" class="md-view">{{ store.ws.fullMarkdown || store.current?.full_md }}</pre>
              <div v-else-if="displayMode === 'tree' && treeData" class="tree-view">
                <div class="tree-legend" v-if="isReviewing">
                  <span class="legend-item"><span class="legend-dot pending">○</span> 待审阅</span>
                  <span class="legend-item"><span class="legend-dot approved">✓</span> 认可</span>
                  <span class="legend-item"><span class="legend-dot rejected">✗</span> 拒绝</span>
                  <span class="legend-item"><span class="legend-dot edited">✎</span> 双击编辑</span>
                </div>
                <div v-for="child in treeData.children" :key="child.path" class="tree-node" :style="{ paddingLeft: '0px' }">
                  <TreeNodeItem
                    :node="child"
                    :is-reviewing="isReviewing"
                    :reviews-map="nodeReviews"
                    :edits-map="nodeEdits"
                    :editing-path="editingNode"
                    @toggle-review="toggleReview($event)"
                    @start-edit="startEdit($event)"
                    @save-edit="(path, text) => saveEdit(path, text)"
                  />
                </div>
              </div>
            </template>
            <div v-else-if="store.generating || store.ws.isGenerating" class="generating">
              <span class="spinner"></span> AI 正在分析需求文档...
            </div>
            <div v-else class="placeholder">点击"AI 生成"开始，将基于需求文档和知识库自动生成测试设计</div>
          </div>

          <div v-if="store.current.status === 'reviewing'" class="feedback-section">
            <textarea v-model="feedbackText" placeholder="输入反馈意见（可选），让 AI 优化设计方案...也可以在上方树结构中逐节点标记认可/拒绝..." class="input" rows="2" />
            <button class="btn btn-primary" @click="submitReview" :disabled="submitting || store.generating || store.ws.isGenerating">
              {{ submitting ? '提交中...' : '提交反馈' }}
            </button>
          </div>
        </template>
        <div v-else class="placeholder">选择一个测试设计查看详情</div>
      </div>
    </div>

    <!-- 归入知识库对话框 -->
    <div v-if="showKbDialog" class="dialog-overlay" @click.self="showKbDialog = false">
      <div class="dialog kb-dialog">
        <h4>归入知识库</h4>
        <p class="dialog-desc">选择入库来源：</p>

        <div class="kb-options">
          <label class="kb-option" :class="{ active: kbMode === 'A' }">
            <input type="radio" v-model="kbMode" value="A" />
            <div>
              <strong>用当前设计入库</strong>
              <span>将设计原文分块 + 解析测试用例嵌入向量库</span>
            </div>
          </label>

          <label class="kb-option" :class="{ active: kbMode === 'B', disabled: !hasStoredXlsx }">
            <input type="radio" v-model="kbMode" value="B" :disabled="!hasStoredXlsx" />
            <div>
              <strong>用之前导出的xlsx入库</strong>
              <span v-if="hasStoredXlsx">解析已导出xlsx中的测试用例嵌入向量库</span>
              <span v-else class="option-disabled">尚未导出过xlsx，请先导出</span>
            </div>
          </label>

          <label class="kb-option" :class="{ active: kbMode === 'C' }">
            <input type="radio" v-model="kbMode" value="C" />
            <div>
              <strong>上传新的xlsx入库</strong>
              <span>上传修改后的xlsx文件，解析用例嵌入向量库</span>
            </div>
          </label>
        </div>

        <!-- C 模式文件上传 -->
        <div v-if="kbMode === 'C'" class="upload-section">
          <input type="file" accept=".xlsx" @change="(e: any) => kbUploadingFile = (e.target.files?.[0] || null)" class="file-input" />
          <span v-if="kbUploadingFile" class="upload-filename">{{ kbUploadingFile.name }}</span>
        </div>

        <!-- B/C 模式预览 -->
        <div v-if="kbMode === 'B' || kbMode === 'C'" class="preview-section">
          <button class="btn" @click="previewKbCases" :disabled="kbPreviewLoading || (kbMode === 'C' && !kbUploadingFile)">
            {{ kbPreviewLoading ? '解析中...' : '预览用例' }}
          </button>
          <div v-if="kbPreviewCases.length > 0" class="preview-table-wrapper">
            <table class="preview-table">
              <thead>
                <tr>
                  <th>用例名称</th><th>所属产品</th><th>用例类型</th>
                  <th>适用阶段</th><th>前置条件</th><th>步骤</th><th>预期结果</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(c, i) in kbPreviewCases" :key="i">
                  <td>{{ c.name }}</td><td>{{ c.product }}</td><td>{{ c.case_type }}</td>
                  <td>{{ c.phase }}</td><td>{{ c.precondition }}</td><td>{{ c.steps }}</td><td>{{ c.expected }}</td>
                </tr>
              </tbody>
            </table>
            <p class="preview-count">共 {{ kbPreviewCases.length }} 条用例</p>
          </div>
        </div>

        <div class="dialog-actions">
          <button class="btn btn-primary" @click="confirmKbSync"
            :disabled="kbSyncing || (kbMode === 'B' && !hasStoredXlsx) || (kbMode === 'C' && !kbUploadingFile)">
            {{ kbSyncing ? '入库中...' : '确认入库' }}
          </button>
          <button class="btn" @click="showKbDialog = false">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, h } from 'vue'

const TreeNodeItem = defineComponent({
  name: 'TreeNodeItem',
  props: {
    node: { type: Object, required: true },
    depth: { type: Number, default: 0 },
    isReviewing: { type: Boolean, default: false },
    reviewsMap: { type: Object, default: () => ({}) },
    editsMap: { type: Object, default: () => ({}) },
    editingPath: { type: String, default: null },
  },
  emits: ['toggle-review', 'start-edit', 'save-edit'],
  setup(props, { emit }) {
    return () => {
      const node = props.node as any
      const children = node.children || []
      const path = node.path
      const review = (props.reviewsMap as Record<string, any>)[path] || 'pending'
      const editVal = (props.editsMap as Record<string, any>)[path]
      const hasEdit = !!editVal
      const displayText = editVal || node.text

      // 审阅徽标
      const reviewBadge = props.isReviewing ? h('span', {
        class: ['review-badge', review],
        onClick: (e: MouseEvent) => { e.stopPropagation(); emit('toggle-review', path) },
        title: review === 'pending' ? '点击标记' : review === 'approved' ? '已认可' : '已拒绝',
      }, review === 'approved' ? '✓' : review === 'rejected' ? '✗' : '○') : null

      // 编辑图标
      const editIcon = props.isReviewing ? h('span', {
        class: 'edit-icon',
        onDblclick: (e: MouseEvent) => { e.stopPropagation(); emit('start-edit', path) },
        onClick: (e: MouseEvent) => { e.stopPropagation(); emit('start-edit', path) },
        title: '双击编辑',
      }, '✎') : null

      // 节点文本或编辑框
      let textContent: any
      if (props.editingPath === path) {
        textContent = h('textarea', {
          class: 'tree-node-input',
          rows: 2,
          value: editVal || node.text,
          onBlur: (e: Event) => emit('save-edit', path, (e.target as HTMLTextAreaElement).value),
          onKeydown: (e: KeyboardEvent) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              emit('save-edit', path, (e.target as HTMLTextAreaElement).value)
            }
          },
        })
      } else {
        textContent = h('span', { class: 'node-text-content' }, displayText)
      }

      // 编辑标记
      const editMark = hasEdit && props.editingPath !== path ? h('span', { class: 'edit-mark' }, '✎') : null

      return h('div', { class: ['tree-node', { 'node-rejected': review === 'rejected' }], style: { paddingLeft: `${(props.depth + 1) * 16}px` } }, [
        h('div', { class: 'tree-node-text' }, [
          h('span', { class: 'tree-bullet' }, '- '),
          reviewBadge,
          textContent,
          editMark,
          editIcon,
        ]),
        ...children.map((child: any) =>
          h(TreeNodeItem, {
            node: child,
            depth: props.depth + 1,
            isReviewing: props.isReviewing,
            reviewsMap: props.reviewsMap,
            editsMap: props.editsMap,
            editingPath: props.editingPath,
            'onToggle-review': (p: string) => emit('toggle-review', p),
            'onStart-edit': (p: string) => emit('start-edit', p),
            'onSave-edit': (p: string, v: string) => emit('save-edit', p, v),
          })
        ),
      ])
    }
  },
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.page-header h3 { margin: 0; }
.btn { padding: 0.4rem 0.8rem; border: 1px solid #3a3a5a; background: transparent; color: #ccc; border-radius: 6px; cursor: pointer; font-size: 0.85rem; }
.btn:hover { border-color: #e94560; color: #e94560; }
.btn-primary { background: #e94560; border-color: #e94560; color: #fff; }
.btn-primary:hover { background: #d63851; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn.approve { border-color: #10b981; color: #10b981; }
.btn.approve:hover { background: rgba(16, 185, 129, 0.15); }
.btn.sync-kb { border-color: #8b5cf6; color: #8b5cf6; }
.btn.sync-kb:hover { background: rgba(139, 92, 246, 0.15); }
.btn.sync-kb:disabled { opacity: 0.6; cursor: not-allowed; }
.btn.danger { border-color: #ef4444; color: #ef4444; }
.btn.danger:hover { background: rgba(239, 68, 68, 0.15); }
.kb-done { color: #10b981; font-size: 0.85rem; }
.btn.active { border-color: #e94560; color: #e94560; }
.card { background: #16213e; border: 1px solid #2a2a4a; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.5rem; }
.create-form { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1rem; }
.form-label { color: #a0a0b0; font-size: 0.85rem; }
.input, select.input { padding: 0.5rem 0.75rem; background: #0f3460; border: 1px solid #2a2a4a; border-radius: 6px; color: #eee; font-size: 0.9rem; }
.form-actions { display: flex; gap: 0.5rem; }
.layout { display: flex; gap: 1rem; }
.design-list { width: 240px; flex-shrink: 0; max-height: 70vh; overflow-y: auto; }
.design-item { cursor: pointer; display: flex; justify-content: space-between; align-items: center; transition: border-color 0.2s; gap: 0.5rem; }
.design-item:hover, .design-item.active { border-color: #e94560; }
.design-title { color: #eee; font-size: 0.85rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.version { color: #666; font-size: 0.75rem; }
.status { font-size: 0.75rem; padding: 0.1rem 0.4rem; border-radius: 4px; white-space: nowrap; }
.status.reviewing { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
.status.approved { background: rgba(16, 185, 129, 0.15); color: #10b981; }
.status.exported { background: rgba(139, 92, 246, 0.15); color: #8b5cf6; }
.status.draft { background: rgba(148, 163, 184, 0.15); color: #94a3b8; }
.status.generating { background: rgba(59, 130, 246, 0.15); color: #3b82f6; }
.design-panel { flex: 1; }
.panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; }
.panel-header h4 { margin: 0 0.25rem 0 0; color: #eee; }
.panel-actions { display: flex; gap: 0.5rem; }
.toolbar { display: flex; align-items: flex-start; gap: 1rem; margin-bottom: 0.75rem; flex-wrap: wrap; }
.type-picker { position: relative; }
.type-dropdown { position: absolute; top: 100%; left: 0; z-index: 100; background: #16213e; border: 1px solid #2a2a4a; border-radius: 8px; padding: 0.5rem; min-width: 200px; max-height: 300px; overflow-y: auto; margin-top: 0.25rem; }
.type-header { display: flex; gap: 0.5rem; margin-bottom: 0.5rem; padding-bottom: 0.5rem; border-bottom: 1px solid #2a2a4a; }
.btn-sm { padding: 0.2rem 0.5rem; border: 1px solid #3a3a5a; background: transparent; color: #aaa; border-radius: 4px; cursor: pointer; font-size: 0.75rem; }
.btn-sm:hover { border-color: #e94560; color: #e94560; }
.type-option { display: flex; gap: 0.5rem; padding: 0.3rem 0.5rem; cursor: pointer; border-radius: 4px; font-size: 0.85rem; color: #ccc; }
.type-option:hover { background: rgba(233, 69, 96, 0.1); }
.type-check { width: 1.2rem; text-align: center; color: #e94560; }
.ws-status { color: #3b82f6; font-size: 0.85rem; }
.ws-error { color: #ef4444; font-size: 0.85rem; }
.view-toggle { display: flex; gap: 0.25rem; margin-bottom: 0.75rem; }
.design-content { background: #0f3460; border-radius: 8px; padding: 1rem; min-height: 300px; }
.md-view { white-space: pre-wrap; color: #ddd; font-family: 'Consolas', 'Monaco', monospace; font-size: 0.85rem; margin: 0; max-height: 60vh; overflow-y: auto; }
.tree-view { color: #ccc; font-size: 0.85rem; max-height: 60vh; overflow-y: auto; }
.tree-node-text { padding: 0.2rem 0; display: flex; align-items: center; gap: 2px; }
.tree-bullet { color: #e94560; flex-shrink: 0; }
.generating { color: #3b82f6; text-align: center; padding: 2rem; }
.spinner { display: inline-block; animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.placeholder { color: #666; text-align: center; padding: 2rem; }
.feedback-section { margin-top: 1rem; display: flex; gap: 0.5rem; align-items: flex-start; }
.feedback-section .input { flex: 1; resize: vertical; }
.empty { text-align: center; padding: 1.5rem; color: #666; font-size: 0.85rem; }
.guide-steps { color: #888; margin-top: 0.5rem; font-size: 0.8rem; }

/* ── 审阅相关样式 ── */
.review-badge { cursor: pointer; width: 16px; height: 16px; display: inline-flex; align-items: center; justify-content: center; font-size: 0.75rem; flex-shrink: 0; user-select: none; opacity: 0.5; border-radius: 50%; transition: all 0.15s; }
.review-badge:hover { opacity: 1; }
.review-badge.approved { color: #10b981; opacity: 1; background: rgba(16, 185, 129, 0.1); }
.review-badge.rejected { color: #ef4444; opacity: 1; background: rgba(239, 68, 68, 0.1); }
.node-rejected .node-text-content { color: #ef4444; text-decoration: line-through; opacity: 0.7; }
.edit-icon { cursor: pointer; color: #f59e0b; opacity: 0.4; font-size: 0.75rem; margin-left: 2px; flex-shrink: 0; }
.edit-icon:hover { opacity: 1; }
.edit-mark { color: #f59e0b; font-size: 0.7rem; margin-left: 2px; flex-shrink: 0; }
.tree-node-input { background: #0f3460; border: 1px solid #e94560; color: #eee; font-size: 0.85rem; width: 100%; resize: vertical; padding: 0.2rem; border-radius: 4px; font-family: inherit; }
.tree-legend { display: flex; gap: 0.8rem; padding: 0.3rem 0.5rem; margin-bottom: 0.5rem; border-bottom: 1px solid #2a2a4a; font-size: 0.75rem; color: #888; flex-wrap: wrap; }
.legend-item { display: inline-flex; align-items: center; gap: 0.2rem; }
.legend-dot { font-size: 0.85rem; }
.legend-dot.pending { color: #666; }
.legend-dot.approved { color: #10b981; }
.legend-dot.rejected { color: #ef4444; }
.legend-dot.edited { color: #f59e0b; cursor: default; }
.node-text-content { min-width: 0; }

/* ── 对话框 ── */
.dialog-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.dialog { background: #16213e; border: 1px solid #2a2a4a; border-radius: 12px; padding: 1.5rem; width: 750px; max-height: 85vh; overflow-y: auto; }
.dialog h4 { margin: 0 0 0.25rem; color: #eee; }
.dialog-desc { color: #a0a0b0; font-size: 0.85rem; margin: 0 0 1rem; }
.kb-options { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1rem; }
.kb-option { display: flex; gap: 0.75rem; padding: 0.75rem; border: 1px solid #2a2a4a; border-radius: 8px; cursor: pointer; transition: border-color 0.2s; }
.kb-option:hover, .kb-option.active { border-color: #8b5cf6; }
.kb-option.disabled { opacity: 0.5; cursor: not-allowed; }
.kb-option.disabled:hover { border-color: #2a2a4a; }
.kb-option input[type="radio"] { margin-top: 0.15rem; accent-color: #8b5cf6; }
.kb-option div { display: flex; flex-direction: column; gap: 0.15rem; }
.kb-option strong { color: #eee; font-size: 0.9rem; }
.kb-option span { color: #a0a0b0; font-size: 0.8rem; }
.option-disabled { color: #ef4444 !important; }
.upload-section { margin-bottom: 1rem; }
.file-input { color: #ccc; font-size: 0.85rem; }
.upload-filename { color: #10b981; font-size: 0.85rem; margin-left: 0.5rem; }
.preview-section { margin-bottom: 1rem; }
.preview-table-wrapper { margin-top: 0.5rem; max-height: 300px; overflow: auto; border: 1px solid #2a2a4a; border-radius: 8px; }
.preview-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
.preview-table th { background: #0f3460; color: #ccc; padding: 0.4rem; text-align: left; position: sticky; top: 0; z-index: 1; }
.preview-table td { padding: 0.4rem; color: #ddd; border-top: 1px solid #2a2a4a; vertical-align: top; }
.preview-count { color: #888; font-size: 0.8rem; margin: 0.5rem 0 0; text-align: right; }
.dialog-actions { display: flex; gap: 0.5rem; justify-content: flex-end; }
</style>
