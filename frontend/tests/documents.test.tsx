import { afterEach, expect, test } from 'bun:test'
import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import Home from '../app/page'
import { listDocuments } from '../lib/api'

const originalFetch = globalThis.fetch
const requests: Array<{ url: URL; signal?: AbortSignal | null }> = []

function doc(id: number, title = `Guide ${id}`) {
  return { id, title, source: 'docs', created_at: '2026-11-14T09:00:00Z', content_preview: `Preview ${id}` }
}

function page(items = [doc(1)], total = items.length, offset = 0) {
  return { items, total, limit: 20, offset }
}

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })
}

function mockApi(handler: (url: URL) => Response | Promise<Response>) {
  globalThis.fetch = (async (input: string | URL | Request, init?: RequestInit) => {
    const url = new URL(String(input))
    expect(url.pathname.startsWith('/api/documents')).toBe(true)
    expect(init?.method).toBeUndefined()
    requests.push({ url, signal: init?.signal })
    return handler(url)
  }) as typeof fetch
}

function openDocuments() {
  render(<Home />)
  fireEvent.click(screen.getByRole('button', { name: 'Documents' }))
}

function draft(value: string) {
  fireEvent.change(screen.getByLabelText('Search documents'), { target: { value } })
}

function search(value: string) {
  draft(value)
  fireEvent.submit(screen.getByLabelText('Search documents').closest('form')!)
}

afterEach(() => {
  cleanup()
  globalThis.fetch = originalFetch
  requests.length = 0
})

test('documents load on opening the tab, search only on submit, and retain the applied query while paging', async () => {
  mockApi((url) => {
    const offset = Number(url.searchParams.get('offset'))
    return json(page(offset ? [doc(21)] : Array.from({ length: 20 }, (_, i) => doc(i + 1)), 21, offset))
  })
  render(<Home />)
  expect(requests).toEqual([])
  fireEvent.click(screen.getByRole('button', { name: 'Documents' }))
  await screen.findByText('Preview 1')
  expect((screen.getByRole('button', { name: 'Previous documents' }) as HTMLButtonElement).disabled).toBe(true)
  fireEvent.click(screen.getByRole('button', { name: 'Next documents' }))
  await screen.findByText('Preview 21')
  expect((screen.getByRole('button', { name: 'Next documents' }) as HTMLButtonElement).disabled).toBe(true)
  const before = requests.length
  draft('  VPN  ')
  expect(requests.length).toBe(before)
  fireEvent.click(screen.getByRole('button', { name: 'Search' }))
  await screen.findByText('21 matching documents for “VPN”')
  expect(requests.at(-1)?.url.searchParams.get('offset')).toBe('0')
  draft('unsubmitted edit')
  fireEvent.click(screen.getByRole('button', { name: 'Next documents' }))
  await screen.findByText('Preview 21')
  expect(requests.at(-1)?.url.searchParams.get('q')).toBe('VPN')
  expect(requests.at(-1)?.url.searchParams.get('offset')).toBe('20')
  fireEvent.click(screen.getByRole('button', { name: 'Previous documents' }))
  await screen.findByText('Preview 1')
  expect(requests.at(-1)?.url.searchParams.get('q')).toBe('VPN')
  expect(requests.at(-1)?.url.searchParams.get('offset')).toBe('0')
  fireEvent.click(screen.getByRole('button', { name: 'Clear search' }))
  await screen.findByText('21 documents')
  expect((screen.getByLabelText('Search documents') as HTMLInputElement).value).toBe('')
  expect(requests.at(-1)?.url.searchParams.has('q')).toBe(false)
  expect(requests.at(-1)?.url.searchParams.get('offset')).toBe('0')
})

test('document client encodes literal search text, keeps source filters, and omits blank queries', async () => {
  mockApi(() => json(page()))
  const query = 'VPN & 100%_setup/a?b=1+#'
  await listDocuments(20, 40, 'internal docs', `  ${query} \n`)
  expect(requests[0].url.searchParams.get('q')).toBe(query)
  expect(requests[0].url.searchParams.get('source')).toBe('internal docs')
  expect(requests[0].url.searchParams.get('offset')).toBe('40')
  expect(requests[0].url.searchParams.has('b')).toBe(false)
  await listDocuments(20, 0, undefined, ' \t ')
  expect(requests[1].url.searchParams.has('q')).toBe(false)
})

test('documents show loading, retry the submitted query after a list error, and distinguish empty searches', async () => {
  let resolve!: (response: Response) => void
  mockApi(() => new Promise<Response>((done) => { resolve = done }))
  openDocuments()
  expect(screen.getByRole('status').textContent).toBe('Loading documents...')
  await act(async () => { resolve(json(page([], 0))) })
  expect(screen.getByText('No saved documents on this page.')).toBeTruthy()
  mockApi(() => json({ detail: 'internal database details' }, 503))
  search('missing')
  await screen.findByRole('alert')
  expect(screen.queryByText('internal database details')).toBeNull()
  draft('new unsent text')
  mockApi(() => json(page([], 0)))
  fireEvent.click(screen.getByRole('button', { name: 'Retry documents' }))
  await screen.findByText(/No documents match this search/)
  expect(requests.at(-1)?.url.searchParams.get('q')).toBe('missing')
  expect(screen.queryByRole('alert')).toBeNull()
  expect((screen.getByRole('button', { name: 'Next documents' }) as HTMLButtonElement).disabled).toBe(true)
})

test('documents render saved content as text and retry detail failures without losing results', async () => {
  let fail = true
  const markup = '<script>alert("fixture")</script>'
  mockApi((url) => url.pathname === '/api/documents'
    ? json(page([doc(1, 'VPN guide')]))
    : fail ? json({}, 404) : json({ ...doc(1, 'VPN guide'), content: markup }))
  openDocuments()
  await screen.findByText('Preview 1')
  fireEvent.click(screen.getByRole('button', { name: /^VPN guide/ }))
  await screen.findByRole('alert')
  expect(screen.getByText('Preview 1')).toBeTruthy()
  fail = false
  fireEvent.click(screen.getByRole('button', { name: 'Retry document' }))
  await screen.findByText(markup)
  const detail = within(screen.getByRole('region', { name: 'Document content' }))
  expect(detail.getByRole('heading', { name: 'VPN guide' })).toBeTruthy()
  expect(document.querySelector('script')).toBeNull()
  search('new query')
  expect(screen.queryByRole('region', { name: 'Document content' })).toBeNull()
  await screen.findByText('1 matching document for “new query”')
})

test('documents ignore stale successful and failed list responses after a newer search', async () => {
  let resolveOld!: (response: Response) => void
  let rejectOld!: (error: Error) => void
  mockApi((url) => {
    if (!url.searchParams.has('q')) return new Promise<Response>((done) => { resolveOld = done })
    if (url.searchParams.get('q') === 'old') return new Promise<Response>((_, reject) => { rejectOld = reject })
    return json(page([doc(2, 'Current result')]))
  })
  openDocuments()
  search('old')
  expect(requests[0].signal?.aborted).toBe(true)
  search('current')
  await screen.findByText('Current result')
  await act(async () => {
    resolveOld(json(page([doc(1, 'Stale result')])))
    rejectOld(new Error('late failure'))
  })
  expect(screen.queryByText('Stale result')).toBeNull()
  expect(screen.queryByRole('alert')).toBeNull()
  expect(screen.getByText('Current result')).toBeTruthy()
})

test('documents ignore late details after another selection, a page change, and clearing a search', async () => {
  const pending: Array<(response: Response) => void> = []
  mockApi((url) => url.pathname === '/api/documents'
    ? json(page([doc(1), doc(2)], 21, Number(url.searchParams.get('offset'))))
    : new Promise<Response>((done) => { pending.push(done) }))
  openDocuments()
  await screen.findByText('Preview 1')
  fireEvent.click(screen.getByRole('button', { name: /^Guide 1 / }))
  expect(screen.getAllByRole('status').some((node) => node.textContent === 'Loading document...')).toBe(true)
  fireEvent.click(screen.getByRole('button', { name: /^Guide 2 / }))
  await act(async () => {
    pending[1](json({ ...doc(2), content: 'Current full content' }))
    pending[0](json({ ...doc(1), content: 'Stale full content' }))
  })
  expect(screen.getByText('Current full content')).toBeTruthy()
  expect(screen.queryByText('Stale full content')).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: /^Guide 1 / }))
  const detailRequest = requests.at(-1)!
  fireEvent.click(screen.getByRole('button', { name: 'Next documents' }))
  expect(detailRequest.signal?.aborted).toBe(true)
  await screen.findByText('Preview 1')
  await act(async () => { pending[2](json({ ...doc(1), content: 'Stale page detail' })) })
  expect(screen.queryByRole('region', { name: 'Document content' })).toBeNull()
  search('vpn')
  await screen.findByText('21 matching documents for “vpn”')
  fireEvent.click(screen.getByRole('button', { name: /^Guide 1 / }))
  fireEvent.click(screen.getByRole('button', { name: 'Clear search' }))
  await act(async () => { pending[3](json({ ...doc(1), content: 'Stale search detail' })) })
  await screen.findByText('21 documents')
  expect(screen.queryByRole('region', { name: 'Document content' })).toBeNull()
})

test('documents abort requests on leaving the tab and ignore late responses when reopened', async () => {
  let resolveOld!: (response: Response) => void
  mockApi(() => new Promise<Response>((done) => { resolveOld = done }))
  openDocuments()
  fireEvent.click(screen.getByRole('button', { name: 'Ask Question' }))
  expect(requests[0].signal?.aborted).toBe(true)
  mockApi(() => json(page([doc(2, 'Reopened result')])))
  fireEvent.click(screen.getByRole('button', { name: 'Documents' }))
  await screen.findByText('Reopened result')
  await act(async () => { resolveOld(json(page([doc(1, 'Unmounted result')]))) })
  expect(screen.queryByText('Unmounted result')).toBeNull()
})
