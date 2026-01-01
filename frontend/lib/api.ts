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

export interface Document {
  id: number
  title: string
  source: string
  created_at: string
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

export async function listDocuments(): Promise<Document[]> {
  const response = await fetch(`${API_BASE_URL}/api/documents`)

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
