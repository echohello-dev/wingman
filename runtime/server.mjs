import { createServer } from 'node:http';
import { mkdir } from 'node:fs/promises';
import { join } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { createModels } from '@earendil-works/pi-ai/models';
import { openaiProvider } from '@earendil-works/pi-ai/providers/openai';
import { openrouterProvider } from '@earendil-works/pi-ai/providers/openrouter';
import { xiaomiTokenPlanSgpProvider } from '@earendil-works/pi-ai/providers/xiaomi-token-plan-sgp';
import { answerJob } from './agent.mjs';
import { Jobs, processJob } from './jobs.mjs';

const directory = process.env.PI_DATA_DIR || './data';
await mkdir(directory, { recursive: true });
const token = process.env.PI_RUNTIME_TOKEN;
if (!token) throw new Error('PI_RUNTIME_TOKEN is required');
const selectedProvider = process.env.PI_PROVIDER || (process.env.OPENROUTER_API_KEY ? 'openrouter' : 'openai');
const providers = { openai: openaiProvider, openrouter: openrouterProvider,
  mimo: xiaomiTokenPlanSgpProvider, 'xiaomi-token-plan-sgp': xiaomiTokenPlanSgpProvider };
if (!Object.hasOwn(providers, selectedProvider)) throw new Error(`Unsupported PI_PROVIDER: ${selectedProvider}`);
const baseProvider = providers[selectedProvider]();
const provider = baseProvider.id;
const defaults = { openai: 'gpt-4.1', openrouter: 'openai/gpt-4.1', 'xiaomi-token-plan-sgp': 'mimo-v2.6-flash' };
const modelId = process.env.LLM_MODEL || defaults[provider];
const models = createModels();
models.setProvider({
  ...baseProvider,
  streamSimple: (model, transcript, options) => baseProvider.streamSimple(model, transcript, {
    ...options,
    temperature: Number(process.env.LLM_TEMPERATURE || 0.7),
    maxTokens: Number(process.env.LLM_MAX_TOKENS || 2000),
  }),
});
if (!models.getModel(provider, modelId)) throw new Error(`Unknown Pi model: ${provider}/${modelId}`);
const jobs = new Jobs(join(directory, 'jobs.sqlite'));
let stopping = false;

async function deliver(id, target, text) {
  const response = await fetch('https://slack.com/api/chat.postMessage', {
    method: 'POST', signal: AbortSignal.timeout(30000),
    headers: { authorization: `Bearer ${process.env.SLACK_BOT_TOKEN}`, 'content-type': 'application/json' },
    body: JSON.stringify({ channel: target.channel, thread_ts: target.thread_ts, text,
      // Stable UUID across delivery retries. Slack delivery remains at-least-once.
      client_msg_id: `${id.slice(0,8)}-${id.slice(8,12)}-4${id.slice(13,16)}-a${id.slice(17,20)}-${id.slice(20,32)}` }),
  });
  const body = await response.json();
  if (!response.ok || !body.ok) throw new Error(`Slack delivery failed: ${body.error || response.status}`);
}

const worker = (async () => {
  while (!stopping) {
    const job = jobs.next();
    if (job) await processJob(jobs, job,
      payload => answerJob(payload, { directory, models, provider, modelId }), deliver);
    else await delay(250);
  }
})();
worker.catch(error => { console.error(error); process.exit(1); });

const server = createServer(async (request, response) => {
  const send = (status, body) => {
    response.writeHead(status, { 'content-type': 'application/json' });
    response.end(JSON.stringify(body));
  };
  try {
    if (request.method === 'GET' && request.url === '/health') return send(200, { status: 'healthy' });
    if (request.headers.authorization !== `Bearer ${token}`) return send(401, { error: 'Unauthorized' });
    if (request.method === 'POST' && request.url === '/jobs') {
      let raw = '';
      for await (const chunk of request) {
        raw += chunk;
        if (Buffer.byteLength(raw) > 2_000_000) return send(413, { error: 'Input too large' });
      }
      let body;
      try { body = JSON.parse(raw); } catch { return send(400, { error: 'Invalid JSON' }); }
      if (!body || !['request_id','conversation_id','question','context'].every(key => typeof body[key] === 'string') ||
          !body.request_id || !body.conversation_id || !body.question || !Array.isArray(body.sources) ||
          (body.slack && (typeof body.slack.channel !== 'string' ||
           (body.slack.thread_ts != null && typeof body.slack.thread_ts !== 'string')))) {
        return send(400, { error: 'Invalid job' });
      }
      const job = jobs.submit(body);
      return send(202, { id: job.id, status: job.status });
    }
    const match = request.url?.match(/^\/jobs\/([a-f0-9]{64})$/);
    if (request.method === 'GET' && match) {
      const job = jobs.get(match[1]);
      return job ? send(200, { id: job.id, status: job.status, result: job.result, error: job.error }) : send(404, { error: 'Unknown job' });
    }
    send(404, { error: 'Not found' });
  } catch (error) {
    console.error(error.message);
    send(error.statusCode || 500, { error: error.statusCode ? error.message : 'Runtime request failed' });
  }
});
server.listen(Number(process.env.PI_PORT || 8002), process.env.PI_HOST || '127.0.0.1', () => {
  process.send?.({ port: server.address().port });
});
for (const signal of ['SIGINT','SIGTERM']) process.once(signal, async () => {
  stopping = true;
  server.close();
  // Let the current commit finish; Docker may kill us, and Pi resumes on restart.
  await worker;
  jobs.close();
});
