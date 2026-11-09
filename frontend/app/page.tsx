'use client'

import { useEffect, useState } from 'react'
import {
  askQuestion,
  getDocument,
  listDocuments,
  type Document,
  type DocumentDetail,
} from '@/lib/api'

function formatDate(value?: string | null) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString('en-AU', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

export default function Home() {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'ask' | 'documents' | 'messages'>('ask')
  const [documents, setDocuments] = useState<Document[]>([])
  const [documentsTotal, setDocumentsTotal] = useState(0)
  const [documentsLoading, setDocumentsLoading] = useState(false)
  const [documentsError, setDocumentsError] = useState('')
  const [selectedDocument, setSelectedDocument] = useState<DocumentDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')

  useEffect(() => {
    if (activeTab !== 'documents') return
    let cancelled = false
    setDocumentsLoading(true)
    setDocumentsError('')
    listDocuments()
      .then((data) => {
        if (cancelled) return
        setDocuments(data.items)
        setDocumentsTotal(data.total)
      })
      .catch(() => {
        if (cancelled) return
        setDocuments([])
        setDocumentsTotal(0)
        setDocumentsError('Could not load documents. Check the backend is running and try again.')
      })
      .finally(() => {
        if (!cancelled) setDocumentsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [activeTab])

  const handleSelectDocument = async (doc: Document) => {
    setDetailLoading(true)
    setDetailError('')
    try {
      const detail = await getDocument(doc.id)
      setSelectedDocument(detail)
    } catch {
      setSelectedDocument(null)
      setDetailError('Could not load this document. Try again.')
    } finally {
      setDetailLoading(false)
    }
  }

  const handleAsk = async () => {
    if (!question.trim()) return

    setLoading(true)
    try {
      const response = await askQuestion(question)
      setAnswer(response.answer)
    } catch (error) {
      console.error('Error asking question:', error)
      setAnswer('Error: Could not get response')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        <header className="text-center mb-12">
          <h1 className="text-5xl font-bold text-gray-800 mb-4">
            🛩️ Wingman
          </h1>
          <p className="text-xl text-gray-600">
            AI-Powered Slack Support Assistant
          </p>
        </header>

        {/* Tab Navigation */}
        <div className="flex justify-center mb-8">
          <div className="bg-white rounded-lg shadow-md p-1 inline-flex">
            <button
              onClick={() => setActiveTab('ask')}
              className={`px-6 py-2 rounded-md transition-colors ${
                activeTab === 'ask'
                  ? 'bg-primary-500 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              Ask Question
            </button>
            <button
              onClick={() => setActiveTab('documents')}
              className={`px-6 py-2 rounded-md transition-colors ${
                activeTab === 'documents'
                  ? 'bg-primary-500 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              Documents
            </button>
            <button
              onClick={() => setActiveTab('messages')}
              className={`px-6 py-2 rounded-md transition-colors ${
                activeTab === 'messages'
                  ? 'bg-primary-500 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              Messages
            </button>
          </div>
        </div>

        {/* Ask Question Tab */}
        {activeTab === 'ask' && (
          <div className="max-w-3xl mx-auto">
            <div className="bg-white rounded-xl shadow-lg p-8">
              <h2 className="text-2xl font-semibold text-gray-800 mb-6">
                Ask a Question
              </h2>
              
              <div className="mb-6">
                <textarea
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="What would you like to know?"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none text-gray-800"
                  rows={4}
                  disabled={loading}
                />
              </div>

              <button
                onClick={handleAsk}
                disabled={loading || !question.trim()}
                className="w-full bg-primary-600 hover:bg-primary-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {loading ? 'Thinking...' : 'Ask Wingman'}
              </button>

              {answer && (
                <div className="mt-8 p-6 bg-blue-50 rounded-lg">
                  <h3 className="text-lg font-semibold text-gray-800 mb-3">
                    Answer:
                  </h3>
                  <p className="text-gray-700 whitespace-pre-wrap">{answer}</p>
                </div>
              )}
            </div>

            <div className="mt-8 bg-white rounded-xl shadow-lg p-8">
              <h3 className="text-xl font-semibold text-gray-800 mb-4">
                How It Works
              </h3>
              <ul className="space-y-3 text-gray-600">
                <li className="flex items-start">
                  <span className="text-primary-500 mr-2">✓</span>
                  <span>Ask questions about your Slack workspace and documentation</span>
                </li>
                <li className="flex items-start">
                  <span className="text-primary-500 mr-2">✓</span>
                  <span>Wingman uses RAG to find relevant context from past conversations</span>
                </li>
                <li className="flex items-start">
                  <span className="text-primary-500 mr-2">✓</span>
                  <span>Get AI-powered answers backed by your team's knowledge base</span>
                </li>
              </ul>
            </div>
          </div>
        )}

        {/* Documents Tab */}
        {activeTab === 'documents' && (
          <div className="max-w-3xl mx-auto">
            <div className="bg-white rounded-xl shadow-lg p-8">
              <h2 className="text-2xl font-semibold text-gray-800 mb-2">
                Knowledge Base Documents
              </h2>
              <p className="text-gray-600 mb-6">
                Indexed documents used for retrieval-augmented generation. Select one to read its full content.
              </p>

              {documentsLoading && (
                <p className="text-gray-600">Loading documents...</p>
              )}

              {!documentsLoading && documentsError && (
                <div className="p-4 bg-red-50 rounded-lg">
                  <p className="text-red-700">{documentsError}</p>
                </div>
              )}

              {!documentsLoading && !documentsError && documents.length === 0 && (
                <p className="text-gray-600">
                  No documents yet. Add one with POST /api/documents and it will appear here.
                </p>
              )}

              {!documentsLoading && !documentsError && documents.length > 0 && (
                <>
                  <p className="text-sm text-gray-500 mb-4">
                    {documentsTotal} {documentsTotal === 1 ? 'document' : 'documents'}
                  </p>
                  <ul className="divide-y divide-gray-100">
                    {documents.map((doc) => (
                      <li key={doc.id}>
                        <button
                          onClick={() => handleSelectDocument(doc)}
                          className={`w-full text-left py-4 px-3 rounded-lg transition-colors ${
                            selectedDocument?.id === doc.id
                              ? 'bg-blue-50'
                              : 'hover:bg-gray-50'
                          }`}
                        >
                          <span className="flex items-center justify-between gap-4">
                            <span className="font-medium text-gray-800">{doc.title}</span>
                            <span className="shrink-0 text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full">
                              {doc.source}
                            </span>
                          </span>
                          {formatDate(doc.created_at) && (
                            <span className="block text-sm text-gray-500 mt-1">
                              {formatDate(doc.created_at)}
                            </span>
                          )}
                          {doc.content_preview && (
                            <span className="block text-sm text-gray-600 mt-1 line-clamp-2">
                              {doc.content_preview}
                            </span>
                          )}
                        </button>
                      </li>
                    ))}
                  </ul>
                </>
              )}

              {detailLoading && (
                <p className="text-gray-600 mt-6">Loading document...</p>
              )}

              {!detailLoading && detailError && (
                <div className="mt-6 p-4 bg-red-50 rounded-lg">
                  <p className="text-red-700">{detailError}</p>
                </div>
              )}

              {!detailLoading && !detailError && selectedDocument && (
                <div className="mt-6 p-6 bg-blue-50 rounded-lg">
                  <h3 className="text-lg font-semibold text-gray-800 mb-1">
                    {selectedDocument.title}
                  </h3>
                  <p className="text-sm text-gray-500 mb-3">
                    {selectedDocument.source}
                    {formatDate(selectedDocument.created_at) &&
                      ` - ${formatDate(selectedDocument.created_at)}`}
                  </p>
                  <p className="text-gray-700 whitespace-pre-wrap">{selectedDocument.content}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Messages Tab */}
        {activeTab === 'messages' && (
          <div className="max-w-3xl mx-auto">
            <div className="bg-white rounded-xl shadow-lg p-8">
              <h2 className="text-2xl font-semibold text-gray-800 mb-6">
                Recent Slack Messages
              </h2>
              <p className="text-gray-600">
                View and manage Slack messages that have been processed by Wingman.
                Messages are automatically indexed when the bot is mentioned or receives a DM.
              </p>
            </div>
          </div>
        )}

        <footer className="mt-16 text-center text-gray-600">
          <p className="mb-2">
            Built with FastAPI, Slack Bolt, LangChain, and Next.js
          </p>
          <p className="text-sm">
            See <a href="/docs/README.md" className="text-primary-600 hover:underline">README</a> for setup instructions
          </p>
        </footer>
      </div>
    </main>
  )
}
