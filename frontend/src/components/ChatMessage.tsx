import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { User, Bot, FileCode } from 'lucide-react'

interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
  sources?: Array<{ path: string }>
}

export default function ChatMessage({ role, content, sources }: ChatMessageProps) {
  const isUser = role === 'user'

  return (
    <div className={`flex space-x-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="flex-shrink-0 bg-primary-100 p-2 rounded-full h-10 w-10 flex items-center justify-center">
          <Bot className="h-5 w-5 text-primary-600" />
        </div>
      )}
      <div
        className={`max-w-3xl rounded-lg p-4 ${
          isUser
            ? 'bg-primary-500 text-white'
            : 'bg-white border border-slate-200'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{content}</p>
        ) : (
          <div className="prose prose-slate max-w-none">
            <ReactMarkdown
              components={{
                code({ className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '')
                  const isInline = !match
                  return isInline ? (
                    <code className="bg-slate-100 px-1 py-0.5 rounded text-sm" {...props}>
                      {children}
                    </code>
                  ) : (
                    <SyntaxHighlighter
                      style={oneDark}
                      language={match[1]}
                      PreTag="div"
                    >
                      {String(children).replace(/\n$/, '')}
                    </SyntaxHighlighter>
                  )
                },
              }}
            >
              {content}
            </ReactMarkdown>
          </div>
        )}

        {sources && sources.length > 0 && (
          <div className="mt-4 pt-4 border-t border-slate-200">
            <p className="text-sm font-medium text-slate-600 mb-2">Sources:</p>
            <div className="flex flex-wrap gap-2">
              {sources.map((source, index) => (
                <span
                  key={index}
                  className="inline-flex items-center space-x-1 px-2 py-1 bg-slate-100 rounded text-sm text-slate-700"
                >
                  <FileCode className="h-3 w-3" />
                  <span>{source.path}</span>
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
      {isUser && (
        <div className="flex-shrink-0 bg-primary-500 p-2 rounded-full h-10 w-10 flex items-center justify-center">
          <User className="h-5 w-5 text-white" />
        </div>
      )}
    </div>
  )
}
