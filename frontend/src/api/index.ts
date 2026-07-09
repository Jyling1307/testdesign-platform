import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// Projects
export const projectApi = {
  list: () => api.get('/projects/'),
  create: (data: { name: string; product?: string; description?: string }) => api.post('/projects/', data),
  get: (id: number) => api.get(`/projects/${id}`),
  update: (id: number, data: Partial<{ name: string; description: string }>) => api.patch(`/projects/${id}/`, data),
  delete: (id: number) => api.delete(`/projects/${id}`),
}

// Documents
export const documentApi = {
  list: (projectId: number) => api.get('/documents/', { params: { project: projectId } }),
  upload: (projectId: number, file: File, onProgress?: (p: number) => void) => {
    const form = new FormData()
    form.append('file', file)
    return api.post(`/documents/upload/${projectId}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => { if (onProgress && e.total) onProgress(Math.round((e.loaded * 100) / e.total)) },
    })
  },
  get: (id: number) => api.get(`/documents/${id}`),
  delete: (id: number) => api.delete(`/documents/${id}`),
}

// Knowledge (semantic search)
export const knowledgeApi = {
  search: (projectId: number, query: string, topK = 10) =>
    api.post('/knowledge/search/', { project: String(projectId), query, top_k: topK }),
}

// Test Designs
export const testDesignApi = {
  list: (projectId: number) => api.get('/testdesigns/', { params: { project: projectId } }),
  get: (id: number) => api.get(`/testdesigns/${id}`),
  delete: (id: number) => api.delete(`/testdesigns/${id}`),
  create: (data: { project_id: number; document_id: number }) => api.post('/testdesigns/', data),
  generate: (id: number, notes?: string) => api.post(`/testdesigns/${id}/generate/`, { notes }),
  refine: (id: number, feedback: string, rejected_nodes?: any[]) =>
    api.post(`/testdesigns/${id}/refine/`, { feedback, rejected_nodes }),
  reviews: (id: number, reviews: any[]) => api.post(`/testdesigns/${id}/reviews/`, { reviews }),
  approve: (id: number) => api.post(`/testdesigns/${id}/approve/`),
  revertReview: (id: number) => api.post(`/testdesigns/${id}/revert-review/`),
  exportXlsx: (id: number) => api.post(`/testcases/${id}/export-xlsx/`, {}, { responseType: 'blob' }),
  syncToKb: (id: number, mode: string, file?: File) => {
    const form = new FormData()
    form.append('mode', mode)
    if (file) form.append('xlsx_file', file)
    return api.post(`/testdesigns/${id}/sync-kb/`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  previewXlsx: (id: number, source: string, file?: File) => {
    const form = new FormData()
    form.append('source', source)
    if (file) form.append('xlsx_file', file)
    return api.post(`/testdesigns/${id}/preview-xlsx/`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}

// Test Cases
export const testCaseApi = {
  list: (designId: number) => api.get('/testcases/', { params: { design: designId } }),
}

export default api
