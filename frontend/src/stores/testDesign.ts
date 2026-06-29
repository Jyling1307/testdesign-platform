import { defineStore } from 'pinia'
import { ref } from 'vue'
import { testDesignApi } from '../api'
import { useWebSocket } from './websocket'

export interface TestDesign {
  id: number
  project: number
  document: number
  version: number
  full_md: string
  status: string
  created_at: string
  updated_at: string
}

export const useTestDesignStore = defineStore('testDesign', () => {
  const designs = ref<TestDesign[]>([])
  const current = ref<TestDesign | null>(null)
  const generating = ref(false)
  const ws = useWebSocket()

  async function fetchDesigns(projectId: number) {
    const { data } = await testDesignApi.list(projectId)
    designs.value = data
  }

  async function fetchDesign(id: number) {
    const { data } = await testDesignApi.get(id)
    current.value = data
  }

  async function generateDesign(id: number, useWebSocket = true, notes = '', testTypes: string[] = []) {
    if (useWebSocket) {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.hostname}:8000/ws/gen/${id}`
      ws.reset()
      ws.connect(wsUrl)
      ws.send({ notes, test_types: testTypes })
    } else {
      generating.value = true
      try {
        const { data } = await testDesignApi.generate(id)
        if (current.value && current.value.id === id) {
          current.value.full_md = data.full_md
          current.value.status = data.status
        }
        await fetchDesign(id)
      } finally {
        generating.value = false
      }
    }
  }

  async function refineDesign(id: number, feedback: string, rejectedNodes: any[] = [], useWebSocket = true, testTypes: string[] = []) {
    if (useWebSocket) {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.hostname}:8000/ws/ref/${id}`
      ws.reset()
      ws.connect(wsUrl)
      ws.send({ feedback, rejected_nodes: rejectedNodes, test_types: testTypes })
    } else {
      generating.value = true
      try {
        const { data } = await testDesignApi.refine(id, feedback)
        if (current.value && current.value.id === id) {
          current.value.full_md = data.full_md
          current.value.status = data.status
        }
        await fetchDesign(id)
      } finally {
        generating.value = false
      }
    }
  }

  return { designs, current, generating, ws, fetchDesigns, fetchDesign, generateDesign, refineDesign }
})
