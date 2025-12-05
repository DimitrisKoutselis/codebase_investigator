import { useNavigate } from 'react-router-dom'
import { GitBranch, MessageSquare, Clock, CheckCircle, Loader2, XCircle } from 'lucide-react'

interface CodebaseCardProps {
  id: string
  url: string
  status: string
  createdAt?: string
}

export default function CodebaseCard({ id, url, status, createdAt }: CodebaseCardProps) {
  const navigate = useNavigate()

  const getStatusIcon = () => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'processing':
      case 'pending':
        return <Loader2 className="h-5 w-5 text-primary-500 animate-spin" />
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />
      default:
        return null
    }
  }

  const getStatusText = () => {
    switch (status) {
      case 'completed':
        return 'Ready'
      case 'processing':
        return 'Processing...'
      case 'pending':
        return 'Pending...'
      case 'failed':
        return 'Failed'
      default:
        return status
    }
  }

  const repoName = url.split('/').slice(-2).join('/')

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex items-center space-x-3">
          <div className="bg-slate-100 p-2 rounded-lg">
            <GitBranch className="h-5 w-5 text-slate-600" />
          </div>
          <div>
            <h3 className="font-medium text-slate-800">{repoName}</h3>
            <p className="text-sm text-slate-500 truncate max-w-xs">{url}</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          {getStatusIcon()}
          <span className="text-sm text-slate-600">{getStatusText()}</span>
        </div>
      </div>

      {createdAt && (
        <div className="mt-4 flex items-center text-sm text-slate-500">
          <Clock className="h-4 w-4 mr-1" />
          {new Date(createdAt).toLocaleDateString()}
        </div>
      )}

      <div className="mt-4 flex space-x-3">
        <button
          onClick={() => navigate(`/chat/${id}`)}
          disabled={status !== 'completed'}
          className="flex items-center space-x-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <MessageSquare className="h-4 w-4" />
          <span>Chat</span>
        </button>
      </div>
    </div>
  )
}
