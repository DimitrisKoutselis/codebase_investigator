import { useState, useEffect } from 'react'
import { Code2, Database, Loader2 } from 'lucide-react'
import IngestForm from '../components/IngestForm'
import CodebaseCard from '../components/CodebaseCard'
import apiClient from '../api/client'

interface Codebase {
  id: string
  url: string
  status: string
}

export default function HomePage() {
  const [codebases, setCodebases] = useState<Codebase[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchCodebases = async () => {
    try {
      const data = await apiClient.listCodebases()
      // Map API response to internal format
      const mapped = data.map((cb) => ({
        id: cb.codebase_id,
        url: cb.repo_url,
        status: cb.status,
      }))
      setCodebases(mapped)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load codebases')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCodebases()
  }, [])

  const handleIngest = async (url: string) => {
    const result = await apiClient.ingestRepository(url)
    // Add new codebase to the list
    setCodebases((prev) => [
      { id: result.codebase_id, url: result.repo_url, status: result.status },
      ...prev,
    ])
    // Poll for status updates if not already completed
    if (result.status !== 'completed') {
      pollStatus(result.codebase_id)
    }
  }

  const pollStatus = async (codebaseId: string) => {
    const poll = async () => {
      try {
        const data = await apiClient.getIngestionStatus(codebaseId)
        setCodebases((prev) =>
          prev.map((cb) =>
            cb.id === codebaseId ? { ...cb, status: data.status } : cb
          )
        )
        if (data.status === 'in_progress' || data.status === 'pending') {
          setTimeout(poll, 3000)
        }
      } catch {
        // Stop polling on error
      }
    }
    poll()
  }

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <div className="text-center py-12">
        <div className="inline-flex items-center justify-center bg-primary-100 p-4 rounded-full mb-6">
          <Code2 className="h-12 w-12 text-primary-600" />
        </div>
        <h1 className="text-4xl font-bold text-slate-900 mb-4">
          Codebase Investigator
        </h1>
        <p className="text-xl text-slate-600 max-w-2xl mx-auto">
          Ingest GitHub repositories and ask questions about the code using AI-powered RAG
        </p>
      </div>

      {/* Ingest Form */}
      <div className="max-w-xl mx-auto">
        <IngestForm onSubmit={handleIngest} />
      </div>

      {/* Codebases List */}
      <div className="mt-12">
        <div className="flex items-center space-x-3 mb-6">
          <Database className="h-6 w-6 text-slate-600" />
          <h2 className="text-2xl font-semibold text-slate-800">
            Your Codebases
          </h2>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 text-primary-500 animate-spin" />
          </div>
        ) : error ? (
          <div className="text-center py-12 text-red-600">{error}</div>
        ) : codebases.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg border border-slate-200">
            <Database className="h-12 w-12 text-slate-400 mx-auto mb-4" />
            <p className="text-slate-600">No codebases yet</p>
            <p className="text-sm text-slate-500">
              Add a GitHub repository above to get started
            </p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {codebases.map((codebase) => (
              <CodebaseCard
                key={codebase.id}
                id={codebase.id}
                url={codebase.url}
                status={codebase.status}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
