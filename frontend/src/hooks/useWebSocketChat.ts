import { useState, useRef, useCallback, useEffect } from 'react'

interface WebSocketMessage {
  type: 'chunk' | 'done' | 'error'
  content?: string
  sources?: Array<{ path: string }>
  message?: string
}

interface UseWebSocketChatOptions {
  codebaseId: string
  sessionId: string
  onChunk?: (chunk: string) => void
  onDone?: (sources: Array<{ path: string }>) => void
  onError?: (error: string) => void
}

export function useWebSocketChat({
  codebaseId,
  sessionId,
  onChunk,
  onDone,
  onError,
}: UseWebSocketChatOptions) {
  const [isConnected, setIsConnected] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)

  // Use refs for callbacks to avoid stale closures
  const onChunkRef = useRef(onChunk)
  const onDoneRef = useRef(onDone)
  const onErrorRef = useRef(onError)

  // Update refs when callbacks change
  useEffect(() => {
    onChunkRef.current = onChunk
    onDoneRef.current = onDone
    onErrorRef.current = onError
  }, [onChunk, onDone, onError])

  const getWebSocketUrl = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    return `${protocol}//${host}/ws/chat/${codebaseId}/${sessionId}`
  }, [codebaseId, sessionId])

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    // Don't try to connect if we don't have a codebaseId
    if (!codebaseId) {
      return
    }

    const ws = new WebSocket(getWebSocketUrl())

    ws.onopen = () => {
      setIsConnected(true)
      console.log('WebSocket connected')
    }

    ws.onclose = () => {
      setIsConnected(false)
      setIsStreaming(false)
      console.log('WebSocket disconnected')

      // Attempt to reconnect after 3 seconds
      reconnectTimeoutRef.current = window.setTimeout(() => {
        if (wsRef.current?.readyState !== WebSocket.OPEN) {
          connect()
        }
      }, 3000)
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      onErrorRef.current?.('WebSocket connection error')
    }

    ws.onmessage = (event) => {
      try {
        const data: WebSocketMessage = JSON.parse(event.data)

        switch (data.type) {
          case 'chunk':
            if (data.content) {
              onChunkRef.current?.(data.content)
            }
            break

          case 'done':
            setIsStreaming(false)
            onDoneRef.current?.(data.sources || [])
            break

          case 'error':
            setIsStreaming(false)
            onErrorRef.current?.(data.message || 'Unknown error')
            break
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }

    wsRef.current = ws
  }, [getWebSocketUrl, codebaseId])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    setIsConnected(false)
    setIsStreaming(false)
  }, [])

  const sendMessage = useCallback((message: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      onErrorRef.current?.('WebSocket not connected')
      return false
    }

    setIsStreaming(true)
    wsRef.current.send(JSON.stringify({ message }))
    return true
  }, [])

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect()

    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  return {
    isConnected,
    isStreaming,
    sendMessage,
    connect,
    disconnect,
  }
}

export default useWebSocketChat
