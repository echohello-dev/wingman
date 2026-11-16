import { afterEach, expect, test } from 'bun:test'
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import Home from '../app/page'

const originalFetch = globalThis.fetch
const requests: Array<{ path: string; method?: string; signal?: AbortSignal | null; body?: BodyInit | null }> = []
const saved = (id: number) => ({ id, title: `Guide ${id}`, source: 'docs', created_at: '2026-11-15T09:00:00Z', content: `Saved content ${id}` })
const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status })

function mockApi(index: () => Response | Promise<Response>) {
  globalThis.fetch = (async (input: string | URL | Request, init?: RequestInit) => {
    const url = new URL(String(input))
    requests.push({ path: url.pathname, method: init?.method, signal: init?.signal, body: init?.body })
    if (url.pathname.endsWith('/index')) return index()
    if (url.pathname === '/api/documents') return json({ items: [saved(1), saved(2)], total: 21, limit: 20, offset: 0 })
    if (url.pathname === '/api/documents/1') return json(saved(1))
    if (url.pathname === '/api/documents/2') return json(saved(2))
    throw new Error(`Unexpected request ${url.pathname}`)
  }) as typeof fetch
}

async function openDocument() {
  render(<Home />)
  fireEvent.click(screen.getByRole('button', { name: 'Documents' }))
  fireEvent.click(await screen.findByRole('button', { name: /^Guide 1 / }))
  await screen.findByText('Saved content 1')
}

const indexRequests = () => requests.filter((request) => request.path.endsWith('/index'))

afterEach(() => {
  cleanup()
  globalThis.fetch = originalFetch
  requests.length = 0
})

test('re-indexing requires an explicit click, posts the saved ID once while pending, and keeps the content visible', async () => {
  let resolve!: (response: Response) => void
  mockApi(() => new Promise<Response>((done) => { resolve = done }))
  await openDocument()
  expect(indexRequests()).toEqual([])
  fireEvent.click(screen.getByRole('button', { name: 'Re-index document' }))
  const pending = screen.getByRole('button', { name: 'Re-indexing...' }) as HTMLButtonElement
  expect(pending.disabled).toBe(true)
  fireEvent.click(pending)
  expect(indexRequests()).toHaveLength(1)
  expect(indexRequests()[0]).toMatchObject({ path: '/api/documents/1/index', method: 'POST', body: undefined })
  expect(screen.getByText('Indexing saved content...')).toBeTruthy()
  expect(screen.getByText('Saved content 1')).toBeTruthy()
  await act(async () => { resolve(json({ id: 1, message: 'Document indexed successfully' })) })
  expect(screen.getByText('Document indexed successfully.').getAttribute('role')).toBe('status')
  expect((screen.getByRole('button', { name: 'Re-index document' }) as HTMLButtonElement).disabled).toBe(false)
  expect(screen.getByText('Saved content 1')).toBeTruthy()
  expect(requests.filter((request) => request.method === 'POST').map((request) => request.path)).toEqual(['/api/documents/1/index'])
})

test.each(['404', '422', '503', 'network'] as const)('re-indexing reports a safe failure for %s and retries the same saved document', async (failure) => {
  let fail = true
  mockApi(() => {
    if (!fail) return json({ id: 1, message: 'Document indexed successfully' })
    if (failure === 'network') return Promise.reject(new Error('private provider credentials'))
    return json({ detail: 'private provider credentials' }, Number(failure))
  })
  await openDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Re-index document' }))
  expect((await screen.findByRole('alert')).textContent).toContain('Your saved content is unchanged.')
  expect(screen.queryByText(/private provider credentials/)).toBeNull()
  expect(screen.queryByText('Document indexed successfully.')).toBeNull()
  expect(screen.getByText('Saved content 1')).toBeTruthy()
  fail = false
  fireEvent.click(screen.getByRole('button', { name: 'Re-index document' }))
  await screen.findByText('Document indexed successfully.')
  expect(screen.queryByRole('alert')).toBeNull()
  expect(indexRequests().map((request) => request.path)).toEqual(['/api/documents/1/index', '/api/documents/1/index'])
})

for (const destination of ['selection', 'search', 'page', 'tab'] as const) {
  test.each(['success', 'failure'] as const)(`re-indexing ignores a late %s after a ${destination} change`, async (outcome) => {
    let resolve!: (response: Response) => void
    let reject!: (error: Error) => void
    mockApi(() => new Promise<Response>((done, fail) => { resolve = done; reject = fail }))
    await openDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Re-index document' }))
    const pending = indexRequests()[0]
    if (destination === 'selection') fireEvent.click(screen.getByRole('button', { name: /^Guide 2 / }))
    if (destination === 'search') {
      fireEvent.change(screen.getByLabelText('Search documents'), { target: { value: 'Guide' } })
      fireEvent.click(screen.getByRole('button', { name: 'Search' }))
    }
    if (destination === 'page') fireEvent.click(screen.getByRole('button', { name: 'Next documents' }))
    if (destination === 'tab') {
      fireEvent.click(screen.getByRole('button', { name: 'Ask Question' }))
      fireEvent.click(screen.getByRole('button', { name: 'Documents' }))
    }
    expect(pending.signal?.aborted).toBe(true)
    if (destination !== 'selection') {
      fireEvent.click(await screen.findByRole('button', { name: /^Guide 1 / }))
    }
    await screen.findByText(destination === 'selection' ? 'Saved content 2' : 'Saved content 1')
    await act(async () => {
      if (outcome === 'success') resolve(json({ id: 1, message: 'Document indexed successfully' }))
      else reject(new Error('late failure'))
    })
    expect(screen.queryByText('Document indexed successfully.')).toBeNull()
    expect(screen.queryByText('Indexing saved content...')).toBeNull()
    expect(screen.queryByRole('alert')).toBeNull()
    mockApi(() => json({ id: destination === 'selection' ? 2 : 1, message: 'Document indexed successfully' }))
    fireEvent.click(screen.getByRole('button', { name: 'Re-index document' }))
    await screen.findByText('Document indexed successfully.')
    expect(indexRequests().at(-1)?.path).toBe(`/api/documents/${destination === 'selection' ? 2 : 1}/index`)
  })
}
