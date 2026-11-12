'use client'

import { useEffect, useState } from 'react'
import {
  getConversation, listConversations,
  type ConversationDetailResponse, type ConversationListResponse,
} from '@/lib/api'

const PAGE_SIZE = 20
const buttonClass = 'rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed'

function formatDate(value: string | null) {
  if (!value || Number.isNaN(new Date(value).getTime())) return 'Date unavailable'
  return new Date(value).toLocaleString('en-AU')
}

function Pagination({ label, offset, count, total, onChange }: {
  label: string; offset: number; count: number; total: number
  onChange: (offset: number) => void
}) {
  return (
    <nav aria-label={`${label} pages`} className="mt-4 flex flex-wrap items-center justify-between gap-3">
      <span className="text-sm text-gray-500">
        {count ? offset + 1 : 0}-{offset + count} of {total}
      </span>
      <div className="flex gap-2">
        <button className={buttonClass} disabled={offset === 0}
          aria-label={`Previous ${label}`} onClick={() => onChange(Math.max(0, offset - PAGE_SIZE))}>
          Previous
        </button>
        <button className={buttonClass} disabled={offset + count >= total}
          aria-label={`Next ${label}`} onClick={() => onChange(offset + PAGE_SIZE)}>
          Next
        </button>
      </div>
    </nav>
  )
}

export default function ConversationsPanel() {
  const [offset, setOffset] = useState(0)
  const [list, setList] = useState<ConversationListResponse | null>(null)
  const [listError, setListError] = useState(false)
  const [listAttempt, setListAttempt] = useState(0)
  const [selection, setSelection] = useState<{ id: string; offset: number } | null>(null)
  const [detail, setDetail] = useState<ConversationDetailResponse | null>(null)
  const [detailError, setDetailError] = useState(false)
  const [detailAttempt, setDetailAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    listConversations(PAGE_SIZE, offset).then((data) => {
      if (!cancelled) setList(data)
    }).catch(() => {
      if (!cancelled) setListError(true)
    })
    return () => { cancelled = true }
  }, [offset, listAttempt])

  useEffect(() => {
    if (!selection) return
    let cancelled = false
    getConversation(selection.id, PAGE_SIZE, selection.offset).then((data) => {
      if (!cancelled) setDetail(data)
    }).catch(() => {
      if (!cancelled) setDetailError(true)
    })
    return () => { cancelled = true }
  }, [selection, detailAttempt])

  function changePage(next: number) {
    setList(null)
    setListError(false)
    setSelection(null)
    setDetail(null)
    setDetailError(false)
    setOffset(next)
  }

  function select(id: string, turnOffset = 0) {
    setDetail(null)
    setDetailError(false)
    setSelection({ id, offset: turnOffset })
  }

  return (
    <section aria-labelledby="conversations-title" className="max-w-5xl mx-auto bg-white rounded-xl shadow-lg p-6 sm:p-8">
      <h2 id="conversations-title" className="text-2xl font-semibold text-gray-800 mb-2">Conversations</h2>
      <p className="text-sm text-gray-600 mb-6">
        Saved conversation audit history, most recent first. Pi runtime history is not included.
      </p>
      <div className="grid gap-6 md:grid-cols-2">
        <div>
          <h3 className="font-semibold text-gray-800 mb-3">Saved conversations</h3>
          {listError ? (
            <div role="alert" className="p-4 bg-red-50 rounded-lg text-red-700">
              <p>Could not load conversations.</p>
              <button className={`${buttonClass} mt-3`} onClick={() => {
                setListError(false)
                setListAttempt((attempt) => attempt + 1)
              }}>Retry conversations</button>
            </div>
          ) : !list ? <p role="status" className="text-gray-600">Loading conversations...</p> : (
            <>
              {list.items.length === 0 && <p className="text-gray-600">No saved conversations on this page.</p>}
              <ul className="divide-y divide-gray-100">
                {list.items.map((conversation) => (
                  <li key={conversation.conversation_id}>
                    <button onClick={() => select(conversation.conversation_id)}
                      aria-pressed={selection?.id === conversation.conversation_id}
                      className={`w-full text-left p-3 rounded-lg break-words ${selection?.id === conversation.conversation_id ? 'bg-blue-50' : 'hover:bg-gray-50'}`}>
                      <span className="block font-medium text-gray-800">{conversation.conversation_id}</span>
                      <span className="block text-xs text-gray-500 mt-1">
                        {conversation.channel_id || 'No channel'} - {conversation.message_count} {conversation.message_count === 1 ? 'turn' : 'turns'}
                      </span>
                      <span className="block text-xs text-gray-500 mt-1">{formatDate(conversation.last_message_at)}</span>
                      <span className="block text-sm text-gray-700 mt-2 line-clamp-2">{conversation.last_message_preview || 'No preview available'}</span>
                    </button>
                  </li>
                ))}
              </ul>
              <Pagination label="conversations" offset={offset} count={list.items.length} total={list.total} onChange={changePage} />
            </>
          )}
        </div>
        <section aria-label="Conversation turns" className="min-w-0">
          <h3 className="font-semibold text-gray-800 mb-3">Conversation turns</h3>
          {!selection ? <p className="text-gray-600">Select a conversation to read its turns.</p> : (
            <>
              <p className="text-sm text-gray-500 break-words mb-3">{selection.id}</p>
              {detailError ? (
                <div role="alert" className="p-4 bg-red-50 rounded-lg text-red-700">
                  <p>Could not load this conversation. It may no longer be available.</p>
                  <button className={`${buttonClass} mt-3`} onClick={() => {
                    setDetailError(false)
                    setDetailAttempt((attempt) => attempt + 1)
                  }}>Retry turns</button>
                </div>
              ) : !detail ? <p role="status" className="text-gray-600">Loading turns...</p> : (
                <>
                  {detail.items.length === 0 && <p className="text-gray-600">No turns on this page.</p>}
                  <ol className="space-y-3">
                    {detail.items.map((turn) => (
                      <li key={turn.id} className="bg-blue-50 rounded-lg p-4">
                        <p className="text-sm font-medium text-gray-800">{turn.role}{turn.user_id ? ` - ${turn.user_id}` : ''}</p>
                        <p className="text-xs text-gray-500 mt-1">{formatDate(turn.created_at)}</p>
                        <p className="text-gray-700 whitespace-pre-wrap break-words mt-3">{turn.message}</p>
                      </li>
                    ))}
                  </ol>
                  <Pagination label="turns" offset={selection.offset} count={detail.items.length} total={detail.total}
                    onChange={(next) => select(selection.id, next)} />
                </>
              )}
            </>
          )}
        </section>
      </div>
    </section>
  )
}
