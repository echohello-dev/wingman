'use client'

import { useEffect, useRef, useState } from 'react'
import { previewRetrieval, type RetrievalPreview } from '@/lib/api'

const inputClass = 'w-full rounded-lg border border-gray-300 px-4 py-3 text-gray-800 focus:ring-2 focus:ring-primary-500 disabled:bg-gray-50'

export default function RetrievalPanel() {
  const [question, setQuestion] = useState('')
  const [channel, setChannel] = useState('')
  const [result, setResult] = useState<RetrievalPreview | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const request = useRef<AbortController | null>(null)

  useEffect(() => () => request.current?.abort(), [])

  async function preview() {
    if (!question.trim() || request.current) return
    const controller = new AbortController()
    request.current = controller
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const data = await previewRetrieval(question, channel, controller.signal)
      if (!controller.signal.aborted) setResult(data)
    } catch {
      if (!controller.signal.aborted) {
        setError('Could not preview retrieval. Check the backend is running and try again.')
      }
    } finally {
      if (!controller.signal.aborted) {
        request.current = null
        setLoading(false)
      }
    }
  }

  function edit(field: 'question' | 'channel', value: string) {
    if (field === 'question') setQuestion(value)
    else setChannel(value)
    setResult(null)
    setError('')
  }

  return (
    <section aria-label="Retrieval preview" className="max-w-4xl mx-auto bg-white rounded-xl shadow-lg p-6 sm:p-8">
      <h2 className="text-2xl font-semibold text-gray-800">Inspect retrieval</h2>
      <p className="text-gray-600 mt-2">
        See which knowledge base chunks a question retrieves before generating an answer.
        Previewing uses the configured embedding provider and may incur embedding costs.
      </p>
      <form className="mt-6 space-y-4" onSubmit={(event) => { event.preventDefault(); void preview() }}>
        <div>
          <label htmlFor="retrieval-question" className="block font-medium text-gray-800 mb-2">Question</label>
          <textarea id="retrieval-question" required rows={3} value={question} disabled={loading}
            onChange={(event) => edit('question', event.target.value)} className={inputClass} />
        </div>
        <div>
          <label htmlFor="retrieval-channel" className="block font-medium text-gray-800 mb-2">Channel ID (optional)</label>
          <input id="retrieval-channel" value={channel} disabled={loading} aria-describedby="retrieval-scope"
            onChange={(event) => edit('channel', event.target.value)} className={inputClass} />
          <p id="retrieval-scope" className="text-sm text-gray-600 mt-2">
            Leave blank to search all indexed content. Channel scope filters results; it does not restrict access.
          </p>
        </div>
        <button type="submit" disabled={loading || !question.trim()}
          className="bg-primary-600 hover:bg-primary-700 text-white font-semibold py-3 px-6 rounded-lg disabled:bg-gray-400 disabled:cursor-not-allowed">
          {loading ? 'Retrieving...' : error ? 'Retry preview' : 'Preview retrieval'}
        </button>
      </form>

      <div aria-live="polite" className="mt-6">
        {loading && <p role="status" className="text-gray-600">Retrieving chunks...</p>}
        {error && <p role="alert" className="rounded-lg bg-red-50 p-4 text-red-700">{error}</p>}
        {!result && !loading && !error && <p className="text-gray-500">Submit a question to inspect its sources.</p>}
        {result && (
          <section aria-label="Retrieved chunks">
            <h3 className="font-semibold text-lg text-gray-800">{result.question}</h3>
            <dl className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-4 rounded-lg bg-gray-50 p-4 text-sm">
              <div><dt className="text-gray-500">Search scope</dt><dd className="text-gray-800 break-all mt-1">{result.channel_id ?? 'All indexed content'}</dd></div>
              <div><dt className="text-gray-500">Maximum chunks</dt><dd className="text-gray-800 mt-1">{result.top_k}</dd></div>
              <div><dt className="text-gray-500">Distance cutoff</dt><dd className="text-gray-800 mt-1">{result.max_distance ?? 'Not set'}</dd></div>
            </dl>
            <p role="status" className="text-gray-600 mt-4">{result.items.length} {result.items.length === 1 ? 'chunk' : 'chunks'} retrieved.</p>
            <p className="text-sm text-gray-500 mt-1">Lower distances mean closer vectors, not a confidence percentage.</p>
            {result.items.length === 0 && (
              <p className="text-gray-600 mt-4">No chunks matched this question under the current scope and cutoff. Try another question or channel.</p>
            )}
            <ol className="space-y-4 mt-4">
              {result.items.map((item, index) => (
                <li key={index} className="border border-gray-200 rounded-lg p-4 sm:p-5">
                  <div className="flex flex-wrap justify-between gap-2 text-sm">
                    <h4 className="font-semibold text-gray-800">Chunk {index + 1}</h4>
                    <span className="font-mono text-primary-800 break-all">Distance {item.distance}</span>
                  </div>
                  <p className="text-gray-800 whitespace-pre-wrap break-words mt-3">{item.content}</p>
                  {Object.keys(item.metadata).length > 0 ? (
                    <dl className="mt-4 border-t border-gray-100 pt-3 space-y-2 text-xs font-mono">
                      {Object.entries(item.metadata).map(([key, value]) => (
                        <div key={key} className="grid sm:grid-cols-[9rem_minmax(0,1fr)] gap-1">
                          <dt className="text-gray-500 break-all">{key}</dt>
                          <dd className="text-gray-700 whitespace-pre-wrap break-all">{typeof value === 'string' ? value : JSON.stringify(value)}</dd>
                        </div>
                      ))}
                    </dl>
                  ) : <p className="mt-4 text-xs text-gray-500">No source metadata available.</p>}
                </li>
              ))}
            </ol>
          </section>
        )}
      </div>
    </section>
  )
}
