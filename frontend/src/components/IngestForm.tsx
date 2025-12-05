import { useState, FormEvent } from 'react'
import { GitBranch, Loader2, Plus } from 'lucide-react'

interface IngestFormProps {
  onSubmit: (url: string) => Promise<void>
}

export default function IngestForm({ onSubmit }: IngestFormProps) {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!url.trim()) return

    // Basic GitHub URL validation
    const githubPattern = /^https?:\/\/(www\.)?github\.com\/[\w-]+\/[\w.-]+\/?$/
    if (!githubPattern.test(url.trim())) {
      setError('Please enter a valid GitHub repository URL')
      return
    }

    setLoading(true)
    try {
      await onSubmit(url.trim())
      setUrl('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to ingest repository')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-6">
      <div className="flex items-center space-x-3 mb-4">
        <div className="bg-primary-100 p-2 rounded-lg">
          <GitBranch className="h-5 w-5 text-primary-600" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-slate-800">Add Repository</h2>
          <p className="text-sm text-slate-500">
            Enter a GitHub repository URL to start analyzing
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://github.com/owner/repository"
            className="w-full px-4 py-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            disabled={loading}
          />
          {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
        </div>

        <button
          type="submit"
          disabled={loading || !url.trim()}
          className="w-full flex items-center justify-center space-x-2 bg-primary-500 text-white py-3 px-4 rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>Ingesting...</span>
            </>
          ) : (
            <>
              <Plus className="h-5 w-5" />
              <span>Add Repository</span>
            </>
          )}
        </button>
      </form>
    </div>
  )
}
