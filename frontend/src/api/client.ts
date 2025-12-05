const API_BASE = '/api'

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      // Handle validation errors (422) with detail array
      if (error.detail && Array.isArray(error.detail)) {
        const messages = error.detail.map((d: { msg?: string; loc?: string[] }) =>
          d.msg || 'Validation error'
        ).join(', ')
        throw new Error(messages)
      }
      throw new Error(error.detail || error.message || `HTTP error ${response.status}`)
    }

    return response.json()
  }

  // Ingestion endpoints
  async ingestRepository(repoUrl: string) {
    return this.request<{
      codebase_id: string
      repo_url: string
      status: string
      file_count?: number
      created_at: string
    }>(
      '/ingest',
      {
        method: 'POST',
        body: JSON.stringify({ repo_url: repoUrl }),
      }
    )
  }

  async getIngestionStatus(codebaseId: string) {
    return this.request<{
      codebase_id: string
      repo_url: string
      status: string
      file_count?: number
      created_at: string
    }>(`/ingest/${codebaseId}`)
  }

  async listCodebases() {
    return this.request<Array<{
      codebase_id: string
      repo_url: string
      status: string
      file_count?: number
      created_at: string
    }>>('/ingest')
  }

  // Chat endpoints
  async sendMessage(codebaseId: string, sessionId: string, message: string) {
    return this.request<{ response: string; sources: Array<{ path: string }> }>(
      `/chat/${codebaseId}/${sessionId}`,
      {
        method: 'POST',
        body: JSON.stringify({ message }),
      }
    )
  }

  // Streaming chat
  async *streamMessage(
    codebaseId: string,
    sessionId: string,
    message: string
  ): AsyncGenerator<string, void, unknown> {
    const url = `${this.baseUrl}/chat/${codebaseId}/${sessionId}/stream`
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    })

    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) throw new Error('No response body')

    const decoder = new TextDecoder()
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const text = decoder.decode(value, { stream: true })
      yield text
    }
  }

  // Session endpoints
  async getSession(sessionId: string) {
    return this.request<{
      id: string
      codebase_id: string
      messages: Array<{ role: string; content: string }>
    }>(`/sessions/${sessionId}`)
  }

  async listSessions(codebaseId: string) {
    return this.request<{
      sessions: Array<{ id: string; created_at: string; message_count: number }>
    }>(`/sessions/codebase/${codebaseId}`)
  }

  async deleteSession(sessionId: string) {
    return this.request<{ message: string }>(`/sessions/${sessionId}`, {
      method: 'DELETE',
    })
  }

  // Health check
  async healthCheck() {
    return this.request<{ status: string }>('/health')
  }
}

export const apiClient = new ApiClient()
export default apiClient
