import { DatabaseSync } from 'node:sqlite';
import { createHash } from 'node:crypto';

export class Jobs {
  constructor(path) {
    this.db = new DatabaseSync(path);
    this.db.exec(`PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;
      CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY, payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
        result TEXT, error TEXT, attempts INTEGER NOT NULL DEFAULT 0,
        retry_at INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL
      )`);
  }
  submit(payload) {
    const id = createHash('sha256').update(payload.request_id).digest('hex');
    const previous = this.get(id);
    if (previous) {
      const old = previous.payload;
      if (old.question !== payload.question || old.conversation_id !== payload.conversation_id ||
          JSON.stringify(old.slack) !== JSON.stringify(payload.slack)) {
        throw Object.assign(new Error('Request ID reused for different input'), { statusCode: 409 });
      }
      return previous;
    }
    this.db.prepare('INSERT INTO jobs(id,payload,created_at) VALUES(?,?,?)')
      .run(id, JSON.stringify(payload), Date.now());
    return this.get(id);
  }
  get(id) {
    const row = this.db.prepare('SELECT * FROM jobs WHERE id=?').get(id);
    return row && { ...row, payload: JSON.parse(row.payload), result: row.result && JSON.parse(row.result) };
  }
  next() {
    const row = this.db.prepare(`SELECT id FROM jobs WHERE status IN ('pending','delivering')
      AND retry_at<=? ORDER BY created_at, rowid LIMIT 1`).get(Date.now());
    return row && this.get(row.id);
  }
  generated(id, result, slack) {
    this.db.prepare('UPDATE jobs SET result=?,status=?,error=NULL WHERE id=?')
      .run(JSON.stringify(result), slack ? 'delivering' : 'done', id);
  }
  delivered(id, generationFailed = false) {
    if (generationFailed) {
      this.db.prepare("UPDATE jobs SET status='failed',error='Generation failed' WHERE id=?").run(id);
    } else {
      this.db.prepare("UPDATE jobs SET status='done',error=NULL WHERE id=?").run(id);
    }
  }
  failed(id, error) {
    this.db.prepare("UPDATE jobs SET status='failed',error=? WHERE id=?").run(String(error), id);
  }
  deliveryFailed(id, error) {
    this.db.prepare(`UPDATE jobs SET attempts=attempts+1,error=?,retry_at=?,
      status=CASE WHEN attempts>=9 THEN 'delivery_failed' ELSE 'delivering' END WHERE id=?`)
      .run(String(error), Date.now() + 30000, id);
  }
  close() { this.db.close(); }
}

export async function processJob(jobs, job, answer, deliver) {
  if (!job.result) {
    try {
      job.result = await answer(job.payload);
      jobs.generated(job.id, job.result, Boolean(job.payload.slack));
    } catch (error) {
      if (!job.payload.slack) {
        jobs.failed(job.id, error.message);
        return;
      }
      // Persist failure notification too: a restart must not strand the user.
      job.result = {
        answer: "I couldn't complete your question. Please try again.",
        sources: [], confidence: 'low', generation_failed: true,
      };
      jobs.generated(job.id, job.result, true);
    }
  }
  if (job.payload.slack) {
    try {
      await deliver(job.id, job.payload.slack, job.result.answer);
      jobs.delivered(job.id, job.result.generation_failed);
    } catch (error) {
      jobs.deliveryFailed(job.id, error.message);
    }
  }
}
