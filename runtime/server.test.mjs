import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fork } from 'node:child_process';
import { once } from 'node:events';
import { mkdtemp, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

for (const [provider, model] of [['openai', 'gpt-4.1'], ['mimo', 'mimo-v2.6-flash']]) {
test(`runtime starts with ${provider} catalog and protects job routes`, { timeout: 10000 }, async () => {
  const directory = await mkdtemp(join(tmpdir(), 'wingman-server-'));
  const child = fork(new URL('./server.mjs', import.meta.url), [], {
    stdio: ['ignore', 'ignore', 'inherit', 'ipc'],
    env: { ...process.env, PI_PORT: '0', PI_HOST: '127.0.0.1', PI_DATA_DIR: directory,
      PI_RUNTIME_TOKEN: 'test-secret', PI_PROVIDER: provider, OPENROUTER_API_KEY: 'unused-test-key', OPENAI_API_KEY: '', LLM_MODEL: model },
  });
  try {
    const [{ port }] = await once(child, 'message');
    const url = `http://127.0.0.1:${port}`;
    assert.equal((await fetch(`${url}/health`)).status, 200);
    assert.equal((await fetch(`${url}/jobs`)).status, 401);
    const headers = { authorization: 'Bearer test-secret', 'content-type': 'application/json' };
    assert.equal((await fetch(`${url}/jobs`, { method: 'POST', headers, body: '{}' })).status, 400);
    assert.equal((await fetch(`${url}/jobs`, { method: 'POST', headers, body: '{bad' })).status, 400);
    assert.equal((await fetch(`${url}/jobs/${'0'.repeat(64)}`, { headers })).status, 404);
  } finally {
    const exited = once(child, 'exit');
    child.kill('SIGTERM');
    await exited;
    await rm(directory, { recursive: true, force: true });
  }
});

}
