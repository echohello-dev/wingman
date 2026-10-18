import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createModels } from '@earendil-works/pi-ai/models';
import { fauxProvider, fauxAssistantMessage } from '@earendil-works/pi-ai/providers/faux';
import { answerJob } from './agent.mjs';
import { Jobs, processJob } from './jobs.mjs';

const payload = { request_id: 'event-1', conversation_id: 'thread-1', question: 'Hello?', context: 'Reference', sources: [] };

test('real Pi SQLite storage preserves answers, deduplicates retries, and retains conversation history', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'wingman-pi-'));
  try {
    const models = createModels();
    const faux = fauxProvider();
    models.setProvider(faux.provider);
    faux.setResponses([fauxAssistantMessage('First answer'), (transcript) => {
      assert.ok(JSON.stringify(transcript).includes('First answer'));
      return fauxAssistantMessage('Second answer');
    }]);
    const model = faux.getModel();
    const options = { directory, models, provider: model.provider, modelId: model.id };
    assert.equal((await answerJob(payload, options)).answer, 'First answer');
    assert.equal((await answerJob(payload, options)).answer, 'First answer');
    assert.equal(faux.state.callCount, 1);
    assert.equal((await answerJob({ ...payload, request_id: 'event-2', question: 'Follow-up?' }, options)).answer, 'Second answer');
    assert.equal(faux.state.callCount, 2);
  } finally { await rm(directory, { recursive: true, force: true }); }
});

test('outbox resumes after restart without regenerating answer; retry admits only one job', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'wingman-outbox-'));
  let jobs;
  try {
    const path = join(directory, 'jobs.sqlite');
    jobs = new Jobs(path);
    const input = { ...payload, slack: { channel: 'C1', thread_ts: '1.2' } };
    const job = jobs.submit(input);
    assert.equal(jobs.submit(input).id, job.id);
    assert.throws(() => jobs.submit({ ...input, question: 'Different' }), /reused/);
    let calls = 0;
    const answer = async () => { calls++; return { answer: 'Persisted', sources: [], confidence: 'low' }; };
    await processJob(jobs, job, answer, async () => { throw new Error('Network failed'); });
    assert.equal(jobs.get(job.id).status, 'delivering');
    jobs.close();
    jobs = new Jobs(path);
    jobs.db.prepare('UPDATE jobs SET retry_at=0').run();
    let delivered;
    await processJob(jobs, jobs.next(), answer, async (_id, _target, text) => { delivered = text; });
    assert.equal(calls, 1);
    assert.equal(delivered, 'Persisted');
    assert.equal(jobs.get(job.id).status, 'done');
  } finally { jobs?.close(); await rm(directory, { recursive: true, force: true }); }
});

test('a process killed during generation resumes the admitted Pi submission', { timeout: 15000 }, async () => {
  const { fork } = await import('node:child_process');
  const { once } = await import('node:events');
  const directory = await mkdtemp(join(tmpdir(), 'wingman-crash-'));
  let child;
  try {
    child = fork(new URL('./fixtures/interrupted.mjs', import.meta.url), [directory, JSON.stringify(payload)], { stdio: ['ignore', 'ignore', 'inherit', 'ipc'] });
    await once(child, 'message');
    const exited = once(child, 'exit');
    child.kill('SIGKILL');
    await exited;
    const models = createModels();
    const faux = fauxProvider();
    models.setProvider(faux.provider);
    faux.setResponses([fauxAssistantMessage('Recovered answer')]);
    const model = faux.getModel();
    const result = await answerJob(payload, { directory, models, provider: model.provider, modelId: model.id });
    assert.equal(result.answer, 'Recovered answer');
    assert.equal(faux.state.callCount, 1);
  } finally {
    child?.kill('SIGKILL');
    await rm(directory, { recursive: true, force: true });
  }
});


test('model failure sends a persisted Slack failure notification', async () => {
  const jobs = new Jobs(':memory:');
  try {
    const job = jobs.submit({ ...payload, slack: { channel: 'C1' } });
    let text;
    await processJob(jobs, job, async () => { throw new Error('Provider failed'); },
      async (_id, _target, answer) => { text = answer; });
    assert.match(text, /couldn't complete/);
    assert.equal(jobs.get(job.id).status, 'failed');
    assert.equal(jobs.next(), undefined);
  } finally { jobs.close(); }
});
