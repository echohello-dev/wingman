import { afterEach, expect, test } from 'bun:test'
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import Home from '../app/page'

const originalFetch = globalThis.fetch
const requests: Array<{ url: URL; method?: string; signal?: AbortSignal | null; body?: BodyInit | null }> = []
const saved = (id: number) => ({ id, title: `Guide ${id}`, source: 'docs', created_at: '2026-11-16T09:00:00Z', content: `Saved content ${id}` })
const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status })
const deletes = () => requests.filter((request) => request.method === 'DELETE')

function mockApi(remove: () => Response | Promise<Response>, options: { index?: () => Promise<Response>; list?: (url: URL) => Response } = {}) {
  globalThis.fetch = (async (input: string | URL | Request, init?: RequestInit) => {
    const url = new URL(String(input))
    requests.push({ url, method: init?.method, signal: init?.signal, body: init?.body })
    if (init?.method === 'DELETE') return remove()
    if (url.pathname.endsWith('/index') && options.index) return options.index()
    if (url.pathname === '/api/documents') return options.list?.(url) ?? json({ items: [saved(1), saved(2)], total: 21, limit: 20, offset: 0 })
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

function confirm() {
  fireEvent.click(screen.getByRole('button', { name: 'Delete document' }))
  fireEvent.click(screen.getByRole('button', { name: 'Confirm deletion' }))
}

afterEach(() => {
  cleanup()
  globalThis.fetch = originalFetch
  requests.length = 0
})

test('deletion requires confirmation of the selected document and cancellation sends no mutation', async () => {
  mockApi(() => json({ id: 1 }))
  await openDocument()
  expect(deletes()).toHaveLength(0)
  fireEvent.click(screen.getByRole('button', { name: 'Delete document' }))
  expect(screen.getByRole('group', { name: 'Confirm document deletion' }).textContent).toContain('Delete “Guide 1” (ID 1)?')
  expect(screen.getByText(/Historical chunks without an owner/)).toBeTruthy()
  expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Cancel deletion' }))
  expect((screen.getByRole('button', { name: 'Re-index document' }) as HTMLButtonElement).disabled).toBe(true)
  expect(deletes()).toHaveLength(0)
  fireEvent.click(screen.getByRole('button', { name: 'Cancel deletion' }))
  expect(screen.queryByRole('group', { name: 'Confirm document deletion' })).toBeNull()
  expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Delete document' }))
  expect((screen.getByRole('button', { name: 'Re-index document' }) as HTMLButtonElement).disabled).toBe(false)
  expect(deletes()).toHaveLength(0)
})

test.each([200, 404])('confirmed deletion handles HTTP %s by refreshing page one of the applied search', async (status) => {
  let removed = false
  let resolve!: (response: Response) => void
  mockApi(() => new Promise<Response>((done) => { resolve = done }), {
    list: (url) => json({ items: removed ? [saved(2)] : url.searchParams.get('offset') === '20' ? [saved(1)] : [saved(1), saved(2)], total: removed ? 1 : 21, limit: 20, offset: Number(url.searchParams.get('offset')) }),
  })
  await openDocument()
  fireEvent.change(screen.getByLabelText('Search documents'), { target: { value: 'Guide' } })
  fireEvent.click(screen.getByRole('button', { name: 'Search' }))
  await screen.findByText('21 matching documents for “Guide”')
  fireEvent.click(screen.getByRole('button', { name: 'Next documents' }))
  await screen.findByText('21-21 of 21')
  fireEvent.click(screen.getByRole('button', { name: /^Guide 1 / }))
  await screen.findByText('Saved content 1')
  fireEvent.change(screen.getByLabelText('Search documents'), { target: { value: 'unsent edit' } })
  confirm()
  const pending = screen.getByRole('button', { name: 'Deleting...' }) as HTMLButtonElement
  expect(pending.disabled).toBe(true)
  expect((screen.getByRole('button', { name: 'Cancel deletion' }) as HTMLButtonElement).disabled).toBe(true)
  expect((screen.getByRole('button', { name: 'Re-index document' }) as HTMLButtonElement).disabled).toBe(true)
  fireEvent.click(pending)
  fireEvent.click(screen.getByRole('button', { name: 'Re-index document' }))
  expect(deletes()).toHaveLength(1)
  expect(deletes()[0]).toMatchObject({ method: 'DELETE', body: undefined })
  expect(deletes()[0].url.pathname).toBe('/api/documents/1')
  expect(requests.filter((request) => request.method === 'POST')).toHaveLength(0)
  expect(screen.getByText('Saved content 1')).toBeTruthy()
  removed = true
  await act(async () => { resolve(json({}, status)) })
  await screen.findByText('1 matching document for “Guide”')
  expect(screen.getByText('Document is no longer saved.')).toBeTruthy()
  expect(screen.queryByRole('region', { name: 'Document content' })).toBeNull()
  expect(screen.queryByRole('button', { name: /^Guide 1 / })).toBeNull()
  expect(requests.at(-1)?.url.searchParams.get('q')).toBe('Guide')
  expect(requests.at(-1)?.url.searchParams.get('offset')).toBe('0')
  expect((screen.getByLabelText('Search documents') as HTMLInputElement).value).toBe('unsent edit')
  expect(document.activeElement).toBe(screen.getByRole('heading', { name: 'Knowledge Base Documents' }))
})

test.each(['503', '403', 'network'] as const)('deletion reports an uncertain outcome after %s and retries the same ID', async (failure) => {
  let fail = true
  mockApi(() => {
    if (!fail) return json({ id: 1 })
    if (failure === 'network') return Promise.reject(new Error('private credentials'))
    return json({ detail: 'private credentials' }, Number(failure))
  })
  await openDocument()
  confirm()
  expect((await screen.findByRole('alert')).textContent).toContain('Some retrieval chunks may already be removed.')
  expect(screen.queryByText(/private credentials/)).toBeNull()
  expect(screen.getByText('Saved content 1')).toBeTruthy()
  expect(screen.queryByText('Document is no longer saved.')).toBeNull()
  fail = false
  fireEvent.click(screen.getByRole('button', { name: 'Confirm deletion' }))
  await screen.findByText('Document is no longer saved.')
  expect(deletes().map((request) => request.url.pathname)).toEqual(['/api/documents/1', '/api/documents/1'])
})

test('a deletion failure can be cancelled and re-indexing blocks deletion until it finishes', async () => {
  let resolve!: (response: Response) => void
  mockApi(() => json({}, 503), { index: () => new Promise<Response>((done) => { resolve = done }) })
  await openDocument()
  confirm()
  await screen.findByRole('alert')
  fireEvent.click(screen.getByRole('button', { name: 'Cancel deletion' }))
  fireEvent.click(screen.getByRole('button', { name: 'Re-index document' }))
  expect((screen.getByRole('button', { name: 'Delete document' }) as HTMLButtonElement).disabled).toBe(true)
  fireEvent.click(screen.getByRole('button', { name: 'Delete document' }))
  expect(screen.queryByRole('group', { name: 'Confirm document deletion' })).toBeNull()
  await act(async () => { resolve(json({ id: 1 })) })
  await screen.findByText('Document indexed successfully.')
  expect((screen.getByRole('button', { name: 'Delete document' }) as HTMLButtonElement).disabled).toBe(false)
})

test('a failed list refresh after deletion offers a list retry without repeating DELETE', async () => {
  let removed = false
  let listFails = true
  mockApi(() => { removed = true; return json({ id: 1 }) }, {
    list: () => removed && listFails ? json({}, 503) : json({ items: removed ? [] : [saved(1)], total: removed ? 0 : 1, limit: 20, offset: 0 }),
  })
  await openDocument()
  confirm()
  await screen.findByRole('alert')
  expect(screen.getByText('Document is no longer saved.')).toBeTruthy()
  expect(screen.queryByRole('region', { name: 'Document content' })).toBeNull()
  listFails = false
  fireEvent.click(screen.getByRole('button', { name: 'Retry documents' }))
  await screen.findByText('No saved documents on this page.')
  expect(deletes()).toHaveLength(1)
})

for (const destination of ['selection', 'search', 'page', 'tab'] as const) {
  test.each(['success', 'failure'] as const)(`deletion ignores late %s after a ${destination} change`, async (outcome) => {
    let resolve!: (response: Response) => void
    let reject!: (error: Error) => void
    mockApi(() => new Promise<Response>((done, fail) => { resolve = done; reject = fail }))
    await openDocument()
    confirm()
    if (destination === 'selection') fireEvent.click(screen.getByRole('button', { name: /^Guide 2 / }))
    if (destination === 'search') fireEvent.click(screen.getByRole('button', { name: 'Search' }))
    if (destination === 'page') fireEvent.click(screen.getByRole('button', { name: 'Next documents' }))
    if (destination === 'tab') {
      fireEvent.click(screen.getByRole('button', { name: 'Ask Question' }))
      fireEvent.click(screen.getByRole('button', { name: 'Documents' }))
    }
    expect(deletes()[0].signal?.aborted).toBe(true)
    if (destination !== 'selection') fireEvent.click(await screen.findByRole('button', { name: /^Guide 1 / }))
    const content = destination === 'selection' ? 'Saved content 2' : 'Saved content 1'
    await screen.findByText(content)
    const count = requests.length
    await act(async () => {
      if (outcome === 'success') resolve(json({ id: 1 }))
      else reject(new Error('late failure'))
    })
    expect(screen.getByText(content)).toBeTruthy()
    expect(screen.queryByText('Document is no longer saved.')).toBeNull()
    expect(screen.queryByRole('alert')).toBeNull()
    expect(requests).toHaveLength(count)
    expect(screen.queryByRole('group', { name: 'Confirm document deletion' })).toBeNull()
  })
}
