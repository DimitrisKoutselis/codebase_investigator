export interface Codebase {
  id: string
  url: string
  name: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  created_at: string
  file_count?: number
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: SourceFile[]
  timestamp: string
}

export interface SourceFile {
  path: string
  content?: string
  relevance_score?: number
}

export interface ChatSession {
  id: string
  codebase_id: string
  messages: Message[]
  created_at: string
  updated_at: string
}

export interface IngestRequest {
  url: string
}

export interface IngestResponse {
  codebase_id: string
  status: string
  message: string
}

export interface ChatRequest {
  message: string
}

export interface ChatResponse {
  response: string
  sources: SourceFile[]
}
