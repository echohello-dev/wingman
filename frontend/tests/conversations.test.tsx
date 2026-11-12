import { afterEach, expect, test } from 'bun:test'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import Home from '../app/page'
import { getConversation } from '../lib/api'

const originalFetch = globalThis.fetch
const requests: string[] = []

function summary(id: string, count = 2) {
  return {
    conversation_id: id, channel_id: 'CSUPPORT', message_count: count,
    first_message_at: '2026-11-13T01:00:00Z', last_message_at: '2026-11-13T01:01:00Z',
    last_message_preview: `Preview for ${id}`,
  }
}

function turns(id: string, offset = 0) {
  return {
    conversation_id: id, total: 21, limit: 20, offset,
    items: Array.from({ length: offset ? 1 : 20 }, (_, i) => ({
      id: i + offset, conversation_id: id, user_id: i % 2 ? null : 'UFIXTURE',
      channel_id: 'CSUPPORT', role: i % 2 ? 'assistant' : 'user',
      message: `${id} turn ${i + offset + 1}`, message_ts: null,
      created_at: '2026-11-13T01:00:00Z',
    })),
  }
}

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })
}

function mockApi(handler: (url: URL) => Response | Promise<Response>) {
  globalThis.fetch = (async (input: string | URL | Request) => {
    const url = new URL(String(input))
    requests.push(url.pathname + url.search)
    return handler(url)
  }) as typeof fetch
}

function openConversations() {
  render(<Home />)
  fireEvent.click(screen.getByRole('button', { name: 'Conversations' }))
}

function select(id: string) {
  fireEvent.click(screen.getByRole('button', { name: new RegExp(`^${id} CSUPPORT`) }))
}

afterEach(() => {
  cleanup()
  globalThis.fetch = originalFetch
  requests.length = 0
})

test('loads only on opening the tab and paginates summaries and chronological turns independently', async () => {
  mockApi((url) => {
    const offset = Number(url.searchParams.get('offset'))
    if (url.pathname === '/api/conversations') {
      return json({ items: offset ? [summary('older')] : Array.from({ length: 20 }, (_, i) => summary(`saved-${i}`)), total: 21, limit: 20, offset })
    }
    return json(turns('saved-0', offset))
  })
  render(<Home />)
  expect(requests).toEqual([])
  fireEvent.click(screen.getByRole('button', { name: 'Conversations' }))
  await screen.findByText('Preview for saved-0')
  expect((screen.getByRole('button', { name: 'Previous conversations' }) as HTMLButtonElement).disabled).toBe(true)
  select('saved-0')
  await screen.findByText('saved-0 turn 1')
  const detail = within(screen.getByRole('region', { name: 'Conversation turns' }))
  expect(detail.getAllByRole('listitem')[0].textContent).toContain('saved-0 turn 1')
  expect(detail.getAllByRole('listitem')[1].textContent).toContain('saved-0 turn 2')
  fireEvent.click(screen.getByRole('button', { name: 'Next turns' }))
  await screen.findByText('saved-0 turn 21')
  expect((screen.getByRole('button', { name: 'Next turns' }) as HTMLButtonElement).disabled).toBe(true)
  fireEvent.click(screen.getByRole('button', { name: 'Previous turns' }))
  await screen.findByText('saved-0 turn 1')
  fireEvent.click(screen.getByRole('button', { name: 'Next conversations' }))
  await screen.findByText('Preview for older')
  expect(screen.queryByText('saved-0 turn 1')).toBeNull()
  expect((screen.getByRole('button', { name: 'Next conversations' }) as HTMLButtonElement).disabled).toBe(true)
  fireEvent.click(screen.getByRole('button', { name: 'Previous conversations' }))
  await screen.findByText('Preview for saved-0')
  expect(requests).toContain('/api/conversations?limit=20&offset=20')
  expect(requests).toContain('/api/conversations/saved-0?limit=20&offset=20')
})

test('shows loading, an empty page and a list error with a working retry', async () => {
  let resolve!: (response: Response) => void
  mockApi(() => new Promise<Response>((done) => { resolve = done }))
  openConversations()
  expect(screen.getByRole('status').textContent).toBe('Loading conversations...')
  await act(async () => { resolve(json({}, 503)) })
  expect(screen.getByRole('alert').textContent).toContain('Could not load conversations')
  mockApi(() => json({ items: [], total: 0, limit: 20, offset: 0 }))
  fireEvent.click(screen.getByRole('button', { name: 'Retry conversations' }))
  await screen.findByText('No saved conversations on this page.')
  expect((screen.getByRole('button', { name: 'Next conversations' }) as HTMLButtonElement).disabled).toBe(true)
  expect(screen.queryByRole('alert')).toBeNull()
})

test('retries missing conversation details without discarding the list', async () => {
  let fail = true
  mockApi((url) => url.pathname === '/api/conversations'
    ? json({ items: [summary('vpn')], total: 1, limit: 20, offset: 0 })
    : fail ? json({}, 404) : json(turns('vpn')))
  openConversations()
  await screen.findByText('Preview for vpn')
  select('vpn')
  await screen.findByRole('alert')
  expect(screen.getByText('Preview for vpn')).toBeTruthy()
  fail = false
  fireEvent.click(screen.getByRole('button', { name: 'Retry turns' }))
  await screen.findByText('vpn turn 1')
  expect(screen.queryByRole('alert')).toBeNull()
})

test('ignores stale detail responses after selecting another conversation', async () => {
  let resolveOld!: (response: Response) => void
  mockApi((url) => {
    if (url.pathname === '/api/conversations') return json({ items: [summary('old'), summary('new')], total: 2, limit: 20, offset: 0 })
    if (url.pathname.endsWith('/old')) return new Promise<Response>((done) => { resolveOld = done })
    return json(turns('new'))
  })
  openConversations()
  await screen.findByText('Preview for old')
  select('old')
  expect(screen.getByRole('status').textContent).toBe('Loading turns...')
  select('new')
  await screen.findByText('new turn 1')
  await act(async () => { resolveOld(json(turns('old'))) })
  expect(screen.queryByText('old turn 1')).toBeNull()
  expect(screen.getByText('new turn 1')).toBeTruthy()
})

test('ignores stale errors after leaving and reopening the tab', async () => {
  let rejectOld!: (error: Error) => void
  mockApi(() => new Promise<Response>((_, reject) => { rejectOld = reject }))
  openConversations()
  fireEvent.click(screen.getByRole('button', { name: 'Ask Question' }))
  mockApi(() => json({ items: [], total: 0, limit: 20, offset: 0 }))
  fireEvent.click(screen.getByRole('button', { name: 'Conversations' }))
  await screen.findByText('No saved conversations on this page.')
  await act(async () => { rejectOld(new Error('offline')) })
  expect(screen.queryByRole('alert')).toBeNull()
})

test('renders stored markup as text and supports missing metadata', async () => {
  mockApi((url) => url.pathname === '/api/conversations'
    ? json({ items: [{ ...summary('plain'), channel_id: null, last_message_at: null, last_message_preview: null }], total: 1, limit: 20, offset: 0 })
    : json({ ...turns('plain'), items: [{ ...turns('plain').items[0], message: '<script>alert("fixture")</script>', created_at: null }] }))
  openConversations()
  await screen.findByText('No preview available')
  fireEvent.click(screen.getByRole('button', { name: /^plain No channel/ }))
  await screen.findByText('<script>alert("fixture")</script>')
  expect(document.querySelector('script')).toBeNull()
  expect(screen.getAllByText('Date unavailable').length).toBe(2)
})

test('encodes conversation IDs in detail request paths', async () => {
  mockApi(() => json(turns('channel/thread ?')))
  await getConversation('channel/thread ?', 20, 0)
  await waitFor(() => expect(requests).toEqual(['/api/conversations/channel%2Fthread%20%3F?limit=20&offset=0']))
})
