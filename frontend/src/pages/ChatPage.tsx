import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, GitBranch, Loader2, Wifi, WifiOff } from 'lucide-react'
import ChatMessage from '../components/ChatMessage'
import ChatInput from '../components/ChatInput'
import apiClient from '../api/client'
import { useWebSocketChat } from '../hooks/useWebSocketChat'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Array<{ path: string }>
}

export default function ChatPage() {
  const { codebaseId } = useParams<{ codebaseId: string }>()
  const [messages, setMessages] = useState<Message[]>([])
  const [sessionId] = useState(() => crypto.randomUUID())
  const [codebaseInfo, setCodebaseInfo] = useState<{ url: string } | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Use a ref to track the current assistant message ID to avoid stale closures
  const currentAssistantMessageIdRef = useRef<string | null>(null)

  // WebSocket chat callbacks using refs
  const handleChunk = useCallback((chunk: string) => {
    const messageId = currentAssistantMessageIdRef.current
    if (!messageId) return

    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === messageId
          ? { ...msg, content: msg.content + chunk }
          : msg
      )
    )
  }, [])

  const handleDone = useCallback((sources: Array<{ path: string }>) => {
    const messageId = currentAssistantMessageIdRef.current
    if (!messageId) return

    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === messageId
          ? { ...msg, sources }
          : msg
      )
    )
    currentAssistantMessageIdRef.current = null
  }, [])

  const handleError = useCallback((error: string) => {
    const messageId = currentAssistantMessageIdRef.current
    if (!messageId) return

    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === messageId
          ? { ...msg, content: `Error: ${error}` }
          : msg
      )
    )
    currentAssistantMessageIdRef.current = null
  }, [])

  const { isConnected, isStreaming, sendMessage } = useWebSocketChat({
    codebaseId: codebaseId || '',
    sessionId,
    onChunk: handleChunk,
    onDone: handleDone,
    onError: handleError,
  })

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

  const handleSendMessage = useCallback((content: string) => {
    if (!codebaseId || isStreaming) return

    // Add user message
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
    }

    // Create placeholder for assistant message
    const assistantMessageId = crypto.randomUUID()
    const assistantMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
    }

    setMessages((prev) => [...prev, userMessage, assistantMessage])
    currentAssistantMessageIdRef.current = assistantMessageId

    // Send via WebSocket
    const sent = sendMessage(content)

    if (!sent) {
      // WebSocket failed, update with error
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId
            ? { ...msg, content: 'Error: Failed to connect. Please try again.' }
            : msg
        )
      )
      currentAssistantMessageIdRef.current = null
    }
  }, [codebaseId, isStreaming, sendMessage])

  const repoName = codebaseInfo?.url?.split('/').slice(-2).join('/') || 'Loading...'

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-200">
        <div className="flex items-center space-x-4">
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

        {/* Connection status */}
        <div className="flex items-center space-x-2">
          {isConnected ? (
            <>
              <Wifi className="h-4 w-4 text-green-500" />
              <span className="text-sm text-green-600">Connected</span>
            </>
          ) : (
            <>
              <WifiOff className="h-4 w-4 text-red-500" />
              <span className="text-sm text-red-600">Disconnected</span>
            </>
          )}
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
                  disabled={!isConnected || isStreaming}
                  className="px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm text-slate-700 hover:bg-slate-50 transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed"
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
        {isStreaming && messages[messages.length - 1]?.content === '' && (
          <div className="flex items-center space-x-2 text-slate-500">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span>Thinking...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="pt-4 border-t border-slate-200">
        <ChatInput
          onSend={handleSendMessage}
          disabled={!isConnected}
          loading={isStreaming}
        />
      </div>
    </div>
  )
}
