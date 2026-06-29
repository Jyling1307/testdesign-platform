import { ref, computed } from 'vue'

export type WSStatus = 'disconnected' | 'connected' | 'generating' | 'done' | 'error'

export function useWebSocket() {
  const status = ref<WSStatus>('disconnected')
  const fullMarkdown = ref('')
  const errorMessage = ref('')
  const statusMessage = ref('')
  let ws: WebSocket | null = null
  let pendingMessage: object | null = null

  const isConnected = computed(() => status.value === 'connected' || status.value === 'generating')
  const isGenerating = computed(() => status.value === 'generating')

  function connect(url: string) {
    disconnect()
    ws = new WebSocket(url)

    ws.onopen = () => {
      status.value = 'connected'
      if (pendingMessage) {
        ws.send(JSON.stringify(pendingMessage))
        pendingMessage = null
      }
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      switch (data.type) {
        case 'status':
          statusMessage.value = data.message
          if (data.message.includes('生成') || data.message.includes('检索') || data.message.includes('修改')) {
            status.value = 'generating'
          }
          break
        case 'markdown':
          fullMarkdown.value = data.content
          break
        case 'chunk':
          fullMarkdown.value += data.content
          break
        case 'done':
          statusMessage.value = ''
          status.value = 'done'
          break
        case 'error':
          errorMessage.value = data.message
          status.value = 'error'
          break
      }
    }

    ws.onclose = () => {
      if (status.value === 'connected' || status.value === 'generating') {
        status.value = 'disconnected'
      }
    }

    ws.onerror = () => {
      status.value = 'error'
      errorMessage.value = 'WebSocket 连接失败'
    }
  }

  function send(data: object) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data))
    } else {
      pendingMessage = data
    }
  }

  function disconnect() {
    if (ws) {
      ws.close()
      ws = null
    }
    status.value = 'disconnected'
    fullMarkdown.value = ''
    errorMessage.value = ''
    statusMessage.value = ''
  }

  function reset() {
    if (ws) {
      ws.close()
      ws = null
    }
    status.value = 'disconnected'
    errorMessage.value = ''
    statusMessage.value = ''
  }

  return { status, fullMarkdown, errorMessage, statusMessage, isConnected, isGenerating, connect, send, disconnect, reset }
}
