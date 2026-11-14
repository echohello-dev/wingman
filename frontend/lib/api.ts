/**
 * API client for Wingman backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Types
export interface QuestionResponse {
  answer: string
  sources: Array<Record<string, unknown>>
  confidence: string
}

export interface RetrievalPreview {
  question: string
  channel_id: string | null
  top_k: number
  max_distance: number | null
  items: Array<{
    content: string
    metadata: Record<string, unknown>
    distance: number
  }>
}

export async function previewRetrieval(
  question: string, channelId?: string, signal?: AbortSignal
): Promise<RetrievalPreview> {
  const response = await fetch(`${API_BASE_URL}/api/retrieval/preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question: question.trim(),
      channel_id: channelId?.trim() || undefined,
    }),
    signal,
  })
  if (!response.ok) throw new Error(`API error: ${response.status}`)
  return response.json()
}

export interface Document {
  id: number
  title: string
  source: string
  created_at: string
  content_preview?: string | null
}

export interface DocumentDetail extends Document {
  content: string
  updated_at?: string | null
}

export interface DocumentListResponse {
  items: Document[]
  total: number
  limit: number
  offset: number
}

export interface DocumentRequest {
  title: string
  content: string
  source?: string
}

export interface Message {
  id: number
  message_ts: string
  channel_id: string
  user_id: string
  text: string
}

export interface Conversation {
  conversation_id: string
  channel_id: string | null
  message_count: number
  first_message_at: string | null
  last_message_at: string | null
  last_message_preview: string | null
}

export interface ConversationTurn {
  id: number
  conversation_id: string
  user_id: string | null
  channel_id: string | null
  role: string
  message: string
  message_ts: string | null
  created_at: string | null
}

export interface ConversationListResponse {
  items: Conversation[]
  total: number
  limit: number
  offset: number
}

export interface ConversationDetailResponse {
  conversation_id: string
  items: ConversationTurn[]
  total: number
  limit: number
  offset: number
}

export async function listConversations(limit: number, offset: number): Promise<ConversationListResponse> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  const response = await fetch(`${API_BASE_URL}/api/conversations?${params}`)
  if (!response.ok) throw new Error(`API error: ${response.status}`)
  return response.json()
}

export async function getConversation(
  id: string, limit: number, offset: number
): Promise<ConversationDetailResponse> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  const response = await fetch(`${API_BASE_URL}/api/conversations/${encodeURIComponent(id)}?${params}`)
  if (!response.ok) throw new Error(`API error: ${response.status}`)
  return response.json()
}

// API functions
export async function askQuestion(
  question: string,
  channelId?: string
): Promise<QuestionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/ask`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      question,
      channel_id: channelId,
    }),
  })

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }

  return response.json()
}

export async function listDocuments(
  limit?: number,
  offset?: number,
  source?: string
): Promise<DocumentListResponse> {
  const params = new URLSearchParams()
  if (limit !== undefined) params.append('limit', limit.toString())
  if (offset !== undefined) params.append('offset', offset.toString())
  if (source) params.append('source', source)

  const url = `${API_BASE_URL}/api/documents${params.toString() ? `?${params}` : ''}`
  const response = await fetch(url)

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }

  return response.json()
}

export async function getDocument(id: number): Promise<DocumentDetail> {
  const response = await fetch(`${API_BASE_URL}/api/documents/${id}`)

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }

  return response.json()
}

export async function addDocument(doc: DocumentRequest): Promise<{ id: number; message: string }> {
  const response = await fetch(`${API_BASE_URL}/api/documents`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(doc),
  })

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }

  return response.json()
}

export async function listMessages(
  limit?: number,
  channelId?: string
): Promise<Message[]> {
  const params = new URLSearchParams()
  if (limit) params.append('limit', limit.toString())
  if (channelId) params.append('channel_id', channelId)

  const url = `${API_BASE_URL}/api/messages${params.toString() ? `?${params}` : ''}`
  const response = await fetch(url)

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }

  return response.json()
}

export async function indexThread(
  channelId: string,
  threadTs: string
): Promise<{ message: string; thread_ts: string }> {
  const params = new URLSearchParams({
    channel_id: channelId,
    thread_ts: threadTs,
  })

  const response = await fetch(`${API_BASE_URL}/api/index/thread?${params}`, {
    method: 'POST',
  })

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }

  return response.json()
}

export async function healthCheck(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE_URL}/health`)

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }

  return response.json()
}
