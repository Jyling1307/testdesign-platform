import { defineStore } from 'pinia'
import { ref } from 'vue'
import { documentApi } from '../api'

export interface Document {
  id: number
  project: number
  title: string
  file: string
  file_size: number
  file_type: string
  raw_text: string
  parsed_structure: object
  status: string
  created_at: string
}

export const useDocumentStore = defineStore('document', () => {
  const documents = ref<Document[]>([])
  const uploading = ref(false)
  const uploadProgress = ref(0)

  async function fetchDocuments(projectId: number) {
    const { data } = await documentApi.list(projectId)
    documents.value = data
  }

  async function uploadDocument(projectId: number, file: File) {
    uploading.value = true
    uploadProgress.value = 0
    try {
      await documentApi.upload(projectId, file, (p) => { uploadProgress.value = p })
      await fetchDocuments(projectId)
    } finally {
      uploading.value = false
    }
  }

  async function deleteDocument(id: number, projectId: number) {
    await documentApi.delete(id)
    await fetchDocuments(projectId)
  }

  return { documents, uploading, uploadProgress, fetchDocuments, uploadDocument, deleteDocument }
})
