import { afterEach, expect, test } from 'bun:test'
import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import Home from '../app/page'
import type { RetrievalPreview } from '../lib/api'

const originalFetch = globalThis.fetch
const requests: Array<{ body: unknown; signal?: AbortSignal | null }> = []
const fixture: RetrievalPreview = {
  question: 'How do I reset VPN?', channel_id: 'CTARGET', top_k: 2, max_distance: 1,
  items: [{ content: 'Reset VPN via IT portal', distance: 1,
    metadata: { source: 'slack', channel_id: 'CTARGET', message_ts: '1.0' } }],
}

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })
}

function mockApi(handler: () => Response | Promise<Response> = () => json(fixture)) {
  globalThis.fetch = (async (input: string | URL | Request, init?: RequestInit) => {
    // Unexpected generation, document or Slack requests fail the test.
    expect(new URL(String(input)).pathname).toBe('/api/retrieval/preview')
    expect(init?.method).toBe('POST')
    expect(init?.headers).toEqual({ 'Content-Type': 'application/json' })
    requests.push({ body: JSON.parse(String(init?.body)), signal: init?.signal })
    return handler()
  }) as typeof fetch
}

function openPreview() {
  render(<Home />)
  fireEvent.click(screen.getByRole('button', { name: 'Retrieval' }))
}

function question(value = fixture.question) {
  fireEvent.change(screen.getByLabelText('Question', { exact: true }), { target: { value } })
}

function submit() {
  fireEvent.click(screen.getByRole('button', { name: 'Preview retrieval' }))
}

afterEach(() => {
  cleanup()
  globalThis.fetch = originalFetch
  requests.length = 0
})

test('retrieval waits for a non-blank question and submits trimmed optional scope', async () => {
  mockApi()
  openPreview()
  expect(requests).toEqual([])
  const button = screen.getByRole('button', { name: 'Preview retrieval' }) as HTMLButtonElement
  expect(button.disabled).toBe(true)
  question(' \n\t ')
  expect(button.disabled).toBe(true)
  question(`  ${fixture.question}\n`)
  fireEvent.change(screen.getByLabelText('Channel ID (optional)'), { target: { value: ' CTARGET ' } })
  submit()
  await screen.findByText('Reset VPN via IT portal')
  expect(requests.map((request) => request.body)).toEqual([
    { question: fixture.question, channel_id: 'CTARGET' },
  ])
  const results = within(screen.getByRole('region', { name: 'Retrieved chunks' }))
  expect(results.getByText('CTARGET', { selector: 'dd.text-gray-800' })).toBeTruthy()
  expect(results.getByText('Distance 1')).toBeTruthy()
  expect(results.getByText('slack')).toBeTruthy()
  expect(results.getByText('message_ts')).toBeTruthy()
  expect(results.getByText('1 chunk retrieved.')).toBeTruthy()
})

test('retrieval omits blank scope, preserves rank and raw distances, and shows an unset cutoff', async () => {
  mockApi(() => json({ ...fixture, channel_id: null, max_distance: null, items: [
    { content: 'Shared guide', distance: 0.123456789, metadata: { source: 'docs', title: 'VPN guide' } },
    { content: 'Reset VPN via IT portal', distance: 1, metadata: {} },
  ] }))
  openPreview()
  question()
  fireEvent.change(screen.getByLabelText('Channel ID (optional)'), { target: { value: ' \t ' } })
  submit()
  await screen.findByText('Shared guide')
  expect(requests[0].body).toEqual({ question: fixture.question })
  expect(screen.getByText('All indexed content')).toBeTruthy()
  expect(screen.getByText('Not set')).toBeTruthy()
  expect(screen.getByText('Distance 0.123456789')).toBeTruthy()
  const items = within(screen.getByRole('region', { name: 'Retrieved chunks' })).getAllByRole('listitem')
  expect(items[0].textContent).toContain('Shared guide')
  expect(items[1].textContent).toContain('Reset VPN via IT portal')
  expect(screen.getByText('No source metadata available.')).toBeTruthy()
})

test('retrieval disables inputs and duplicate submissions while loading', async () => {
  let resolve!: (response: Response) => void
  mockApi(() => new Promise<Response>((done) => { resolve = done }))
  openPreview()
  question()
  submit()
  expect(screen.getByRole('status').textContent).toBe('Retrieving chunks...')
  expect((screen.getByLabelText('Question', { exact: true }) as HTMLTextAreaElement).disabled).toBe(true)
  expect((screen.getByLabelText('Channel ID (optional)') as HTMLInputElement).disabled).toBe(true)
  expect((screen.getByRole('button', { name: 'Retrieving...' }) as HTMLButtonElement).disabled).toBe(true)
  fireEvent.submit(screen.getByLabelText('Question', { exact: true }).closest('form')!)
  expect(requests.length).toBe(1)
  await act(async () => { resolve(json(fixture)) })
  expect((screen.getByRole('button', { name: 'Preview retrieval' }) as HTMLButtonElement).disabled).toBe(false)
})

test('retrieval shows an empty result and a zero distance cutoff', async () => {
  mockApi(() => json({ ...fixture, items: [], max_distance: 0 }))
  openPreview()
  question()
  submit()
  await screen.findByText('0 chunks retrieved.')
  expect(screen.getByText(/No chunks matched this question/)).toBeTruthy()
  expect(screen.getByText('0', { selector: 'dd' })).toBeTruthy()
  expect(screen.queryByRole('alert')).toBeNull()
})

test('retrieval replaces a failed request with a successful retry', async () => {
  let fail = true
  mockApi(() => fail ? json({ detail: 'private service details' }, 503) : json(fixture))
  openPreview()
  question()
  submit()
  await screen.findByRole('alert')
  expect(screen.queryByText('private service details')).toBeNull()
  fail = false
  fireEvent.click(screen.getByRole('button', { name: 'Retry preview' }))
  await screen.findByText('Reset VPN via IT portal')
  expect(screen.queryByRole('alert')).toBeNull()
  expect(requests.length).toBe(2)
})

test('retrieval clears old results when the question or channel changes', async () => {
  mockApi()
  openPreview()
  question()
  submit()
  await screen.findByText('Reset VPN via IT portal')
  fireEvent.change(screen.getByLabelText('Channel ID (optional)'), { target: { value: 'COTHER' } })
  expect(screen.queryByRole('region', { name: 'Retrieved chunks' })).toBeNull()
  submit()
  await screen.findByText('Reset VPN via IT portal')
  question('Another question')
  expect(screen.queryByRole('region', { name: 'Retrieved chunks' })).toBeNull()
  expect(requests.length).toBe(2)
})

test('retrieval aborts on leaving the tab and ignores late responses after reopening', async () => {
  let resolveOld!: (response: Response) => void
  mockApi(() => new Promise<Response>((done) => { resolveOld = done }))
  openPreview()
  question()
  submit()
  fireEvent.click(screen.getByRole('button', { name: 'Ask Question' }))
  expect(requests[0].signal?.aborted).toBe(true)
  mockApi(() => json({ ...fixture, question: 'New question', items: [] }))
  fireEvent.click(screen.getByRole('button', { name: 'Retrieval' }))
  question('New question')
  submit()
  await screen.findByText('0 chunks retrieved.')
  await act(async () => { resolveOld(json(fixture)) })
  expect(screen.queryByText('Reset VPN via IT portal')).toBeNull()
  expect(screen.getByText('New question', { selector: 'h3' })).toBeTruthy()
})

test('retrieval renders chunk and metadata markup as text', async () => {
  const markup = '<script>alert("fixture")</script>'
  mockApi(() => json({ ...fixture, items: [
    { content: markup, distance: 0, metadata: { title: '<img src=x onerror=alert(1)>', extra: { nested: true } } },
  ] }))
  openPreview()
  question()
  submit()
  await screen.findByText(markup)
  expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeTruthy()
  expect(screen.getByText('{"nested":true}')).toBeTruthy()
  expect(document.querySelector('script, img')).toBeNull()
})
