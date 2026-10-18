---
number: 0004
date: 2026-10-19
status: Accepted
---

# 0004: Pi Durable agent runtime

## Context

Wingman generated each answer with a synchronous LangChain call. Conversation
history was recorded in PostgreSQL, but in-flight generation and Slack delivery
could be lost when the bot stopped.

## Decision

Use `@earendil-works/pi-durable` 1.3.0 in a dedicated Node service. Retain Python
for Slack ingestion, file extraction, Chroma retrieval, and the FastAPI dashboard
API. LangChain remains for embeddings and the vector store, not generation.

Pi stores one conversation per SQLite file on the `pi_data` Docker volume. A
separate SQLite outbox commits requests before acknowledgement and saves generated
answers before Slack delivery. The worker reopens pending conversations on startup;
Pi resumes unfinished submissions. Slack event timestamps and slash-command trigger
IDs provide stable request IDs. API callers may supply a request ID and conversation
ID; otherwise each request is isolated. Duplicate request IDs return the original
job, with changed questions or destinations rejected.

Only one runtime process may own this volume. It processes jobs sequentially and
closes each harness after the job, bounding open sessions. It installs no coding,
shell, or filesystem tools. Communication from Python uses a shared bearer token;
the runtime port is internal to Compose and binds to localhost for local development.

## Consequences

- Agent conversations and pending generation survive process/container restarts.
- Slack reply delivery retries independently of generation, up to ten attempts
  with a 30-second delay; exhausted delivery jobs remain `delivery_failed` in the
  outbox. Model failures become `failed` jobs; Slack users receive a queued failure
  notification. Inspect authenticated `GET /jobs/{id}`.
- Slack delivery is at-least-once. A crash after Slack accepts a message but before
  the local acknowledgement can produce a duplicate, despite a stable client ID.
- Slack now receives final messages, replacing the previous in-process progress
  streams. No external Slack calls occur in tests.
- Existing PostgreSQL conversation history is retained for audit but is not imported
  into Pi. New conversations use Pi history and its automatic compaction rather than
  the old time-window settings.
- The queue becomes durable after context retrieval and successful job admission.
  Retrieval failures and events lost before admission still depend on Slack retries.
- SQLite storage is tied to the volume: back it up and do not use `down -v` when
  preserving agent state. This is process recovery, not host-level replication.
- Pi Durable is experimental. Pin direct packages and lock transitive dependencies;
  validate storage compatibility and recovery before upgrading.
- This replaces the generation portion of ADR-0001; its storage, RAG retrieval,
  API, and frontend choices still apply.

## References

- [Pi Durable documentation](https://github.com/earendil-works/pi/tree/main/packages/durable)
- [Runtime operations](../pi-runtime.md)
- [Original architecture](0001-technology-stack-and-rag-architecture.md)
