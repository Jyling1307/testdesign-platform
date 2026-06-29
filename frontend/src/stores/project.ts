import { defineStore } from 'pinia'
import { ref } from 'vue'
import { projectApi } from '../api'

export interface Project {
  id: number
  name: string
  product: string
  description: string
  created_at: string
  updated_at: string
}

export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const current = ref<Project | null>(null)
  const loading = ref(false)

  async function fetchProjects() {
    loading.value = true
    try {
      const { data } = await projectApi.list()
      projects.value = data
    } finally {
      loading.value = false
    }
  }

  async function fetchProject(id: number) {
    loading.value = true
    try {
      const { data } = await projectApi.get(id)
      current.value = data
    } finally {
      loading.value = false
    }
  }

  return { projects, current, loading, fetchProjects, fetchProject }
})
