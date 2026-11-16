'use client'

import { useEffect, useState } from 'react'
import { getDocument, listDocuments, reindexDocument, type DocumentDetail, type DocumentListResponse } from '@/lib/api'

const PAGE_SIZE = 20
const buttonClass = 'min-h-11 rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-40 disabled:cursor-not-allowed'

function formatDate(value?: string | null) {
  if (!value || Number.isNaN(new Date(value).getTime())) return ''
  return new Date(value).toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' })
}

function DocumentIndexAction({ documentId }: { documentId: number }) {
  const [attempt, setAttempt] = useState(0)
  const [phase, setPhase] = useState<'idle' | 'pending' | 'success' | 'error'>('idle')

  useEffect(() => {
    if (!attempt) return
    let cancelled = false
    const controller = new AbortController()
    reindexDocument(documentId, controller.signal)
      .then(() => { if (!cancelled) setPhase('success') })
      .catch(() => { if (!cancelled) setPhase('error') })
    return () => { cancelled = true; controller.abort() }
  }, [attempt, documentId])

  return (
    <div className="mt-5 border-t border-blue-100 pt-4">
      <p className="text-sm text-gray-600 mb-3">Re-index this saved content for retrieval. This uses the configured embedding provider and may incur a cost.</p>
      <button type="button" className={buttonClass} disabled={phase === 'pending'}
        onClick={() => {
          if (phase === 'pending') return
          setPhase('pending')
          setAttempt((value) => value + 1)
        }}>
        {phase === 'pending' ? 'Re-indexing...' : 'Re-index document'}
      </button>
      <p role="status" className="text-sm text-gray-700 mt-3">
        {phase === 'pending' && 'Indexing saved content...'}
        {phase === 'success' && 'Document indexed successfully.'}
      </p>
      {phase === 'error' && <p role="alert" className="text-sm text-red-700 mt-3">Could not index this document. Your saved content is unchanged. Check that the document is still available and the indexing service is running, then try again.</p>}
      <p className="text-xs text-gray-600 mt-3">Leaving this view stops waiting for the result. Indexing already started may still finish.</p>
    </div>
  )
}

export default function DocumentsPanel() {
  const [draft, setDraft] = useState('')
  const [request, setRequest] = useState({ query: '', offset: 0 })
  const [list, setList] = useState<DocumentListResponse | null>(null)
  const [listError, setListError] = useState(false)
  const [selection, setSelection] = useState<{ id: number } | null>(null)
  const [detail, setDetail] = useState<DocumentDetail | null>(null)
  const [detailError, setDetailError] = useState(false)

  useEffect(() => {
    let cancelled = false
    const controller = new AbortController()
    listDocuments(PAGE_SIZE, request.offset, undefined, request.query, controller.signal)
      .then((data) => { if (!cancelled) setList(data) })
      .catch(() => { if (!cancelled) setListError(true) })
    return () => { cancelled = true; controller.abort() }
  }, [request])

  useEffect(() => {
    if (!selection) return
    let cancelled = false
    const controller = new AbortController()
    getDocument(selection.id, controller.signal)
      .then((data) => { if (!cancelled) setDetail(data) })
      .catch(() => { if (!cancelled) setDetailError(true) })
    return () => { cancelled = true; controller.abort() }
  }, [selection])

  function load(query: string, offset = 0) {
    setList(null)
    setListError(false)
    setSelection(null)
    setDetail(null)
    setDetailError(false)
    setRequest({ query, offset })
  }

  function select(id: number) {
    setDetail(null)
    setDetailError(false)
    setSelection({ id })
  }

  return (
    <section aria-labelledby="documents-title" className="max-w-3xl mx-auto bg-white rounded-xl shadow-lg p-6 sm:p-8">
      <h2 id="documents-title" className="text-2xl font-semibold text-gray-800 mb-2">Knowledge Base Documents</h2>
      <p className="text-gray-600 mb-6">
        Saved documents for retrieval-augmented generation. Select one to read or re-index its content.
      </p>
      <form onSubmit={(event) => { event.preventDefault(); load(draft.trim()) }} className="mb-6">
        <label htmlFor="document-search" className="block font-medium text-gray-800 mb-2">Search documents</label>
        <p id="document-search-help" className="text-sm text-gray-600 mb-3">Search titles and full content for matching text.</p>
        <div className="flex flex-wrap gap-2">
          <input id="document-search" type="search" value={draft} onChange={(event) => setDraft(event.target.value)}
            aria-describedby="document-search-help"
            className="min-w-0 w-full sm:w-auto sm:flex-1 min-h-11 rounded-lg border border-gray-300 px-3 py-2 text-gray-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600" />
          <button type="submit" className={buttonClass}>Search</button>
          <button type="button" className={buttonClass} disabled={!draft && !request.query}
            onClick={() => { setDraft(''); load('') }}>Clear search</button>
        </div>
      </form>

      {listError ? (
        <div role="alert" className="p-4 bg-red-50 rounded-lg text-red-700">
          <p>Could not load documents. Check the backend is running and try again.</p>
          <button className={`${buttonClass} mt-3`} onClick={() => load(request.query, request.offset)}>Retry documents</button>
        </div>
      ) : !list ? <p role="status" className="text-gray-600">Loading documents...</p> : (
        <>
          <p role="status" className="text-sm text-gray-600 mb-4 break-words">
            {list.total} {request.query ? 'matching ' : ''}{list.total === 1 ? 'document' : 'documents'}
            {request.query && <> for &ldquo;{request.query}&rdquo;</>}
          </p>
          {list.items.length === 0 && (
            <p className="text-gray-600">{request.query ? 'No documents match this search. Try different text or clear the search.' : 'No saved documents on this page.'}</p>
          )}
          <ul className="divide-y divide-gray-100">
            {list.items.map((doc) => (
              <li key={doc.id}>
                <button onClick={() => select(doc.id)} aria-pressed={selection?.id === doc.id}
                  className={`w-full text-left py-4 px-3 rounded-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 ${selection?.id === doc.id ? 'bg-blue-50' : 'hover:bg-gray-50'}`}>
                  <span className="flex items-start justify-between gap-4">
                    <span className="min-w-0 break-words font-medium text-gray-800">{doc.title}</span>
                    <span className="max-w-[40%] break-words text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full">{doc.source}</span>
                  </span>
                  {formatDate(doc.created_at) && <span className="block text-sm text-gray-600 mt-1">{formatDate(doc.created_at)}</span>}
                  {doc.content_preview && <span className="block text-sm text-gray-600 mt-1 line-clamp-2 break-words">{doc.content_preview}</span>}
                </button>
              </li>
            ))}
          </ul>
          <nav aria-label="Document pages" className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <span className="text-sm text-gray-600 tabular-nums">{list.items.length ? request.offset + 1 : 0}-{request.offset + list.items.length} of {list.total}</span>
            <div className="flex gap-2">
              <button className={buttonClass} aria-label="Previous documents" disabled={request.offset === 0}
                onClick={() => load(request.query, Math.max(0, request.offset - PAGE_SIZE))}>Previous</button>
              <button className={buttonClass} aria-label="Next documents" disabled={request.offset + list.items.length >= list.total}
                onClick={() => load(request.query, request.offset + PAGE_SIZE)}>Next</button>
            </div>
          </nav>
        </>
      )}

      {selection && (
        <section aria-label="Document content" className="mt-6">
          {detailError ? (
            <div role="alert" className="p-4 bg-red-50 rounded-lg text-red-700">
              <p>Could not load this document. It may no longer be available.</p>
              <button className={`${buttonClass} mt-3`} onClick={() => select(selection.id)}>Retry document</button>
            </div>
          ) : !detail ? <p role="status" className="text-gray-600">Loading document...</p> : (
            <div className="p-6 bg-blue-50 rounded-lg break-words">
              <h3 className="text-lg font-semibold text-gray-800 mb-1">{detail.title}</h3>
              <p className="text-sm text-gray-600 mb-3">{detail.source}{formatDate(detail.created_at) && ` - ${formatDate(detail.created_at)}`}</p>
              <p className="text-gray-700 whitespace-pre-wrap">{detail.content}</p>
              <DocumentIndexAction key={detail.id} documentId={detail.id} />
            </div>
          )}
        </section>
      )}
    </section>
  )
}
