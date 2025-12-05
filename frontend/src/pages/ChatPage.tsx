import { useState, useEffect, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, GitBranch, Loader2 } from 'lucide-react'
import ChatMessage from '../components/ChatMessage'
import ChatInput from '../components/ChatInput'
import apiClient from '../api/client'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Array<{ path: string }>
}

export default function ChatPage() {
  const { codebaseId } = useParams<{ codebaseId: string }>()
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [sessionId] = useState(() => crypto.randomUUID())
  const [codebaseInfo, setCodebaseInfo] = useState<{ url: string } | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Fetch codebase info
    if (codebaseId) {
      apiClient.getIngestionStatus(codebaseId).then((data) => {
        setCodebaseInfo({ url: data.repo_url })
      }).catch(() => {
        // Handle error silently
      })
    }
  }, [codebaseId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSendMessage = async (content: string) => {
    if (!codebaseId) return

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
    }

    setMessages((prev) => [...prev, userMessage])
    setLoading(true)

    try {
      // Use streaming if available, otherwise fall back to regular endpoint
      let fullResponse = ''
      const assistantMessageId = crypto.randomUUID()

      // Add placeholder for assistant message
      setMessages((prev) => [
        ...prev,
        { id: assistantMessageId, role: 'assistant', content: '' },
      ])

      try {
        // Try streaming first
        for await (const chunk of apiClient.streamMessage(
          codebaseId,
          sessionId,
          content
        )) {
          fullResponse += chunk
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: fullResponse }
                : msg
            )
          )
        }
      } catch {
        // Fall back to regular endpoint
        const response = await apiClient.sendMessage(
          codebaseId,
          sessionId,
          content
        )
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? { ...msg, content: response.response, sources: response.sources }
              : msg
          )
        )
      }
    } catch (error) {
      const errorMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : 'Failed to get response'}`,
      }
      setMessages((prev) => [...prev.slice(0, -1), errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const repoName = codebaseInfo?.url?.split('/').slice(-2).join('/') || 'Loading...'

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {/* Header */}
      <div className="flex items-center space-x-4 pb-4 border-b border-slate-200">
        <Link
          to="/"
          className="flex items-center space-x-2 text-slate-600 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="h-5 w-5" />
          <span>Back</span>
        </Link>
        <div className="flex items-center space-x-2">
          <GitBranch className="h-5 w-5 text-slate-500" />
          <span className="font-medium text-slate-800">{repoName}</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto py-6 space-y-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="bg-primary-100 p-4 rounded-full mb-4">
              <GitBranch className="h-8 w-8 text-primary-600" />
            </div>
            <h2 className="text-xl font-semibold text-slate-800 mb-2">
              Start a Conversation
            </h2>
            <p className="text-slate-600 max-w-md">
              Ask questions about the codebase structure, find specific code patterns,
              or get explanations of how things work.
            </p>
            <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-3 max-w-lg">
              {[
                'What is the project structure?',
                'How does authentication work?',
                'Where are the API endpoints defined?',
                'Explain the main entry point',
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => handleSendMessage(suggestion)}
                  className="px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm text-slate-700 hover:bg-slate-50 transition-colors text-left"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <ChatMessage
              key={message.id}
              role={message.role}
              content={message.content}
              sources={message.sources}
            />
          ))
        )}
        {loading && messages[messages.length - 1]?.role === 'user' && (
          <div className="flex items-center space-x-2 text-slate-500">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span>Thinking...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="pt-4 border-t border-slate-200">
        <ChatInput onSend={handleSendMessage} loading={loading} />
      </div>
    </div>
  )
}
