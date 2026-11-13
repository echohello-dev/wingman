# Retrieval tuning

Wingman retrieves up to `RETRIEVAL_TOP_K` chunks, defaulting to 5. A request with
a channel ID searches only that channel before applying the limit. An unscoped
request searches the whole collection.

Documents are split into overlapping character windows. `CHUNK_SIZE` must be
positive, and `CHUNK_OVERLAP` must be non-negative and smaller than `CHUNK_SIZE`.
Invalid settings are rejected at startup, before indexing can begin. Splitting
stops when a chunk reaches the end of the content; it does not index redundant
trailing overlap fragments. Existing stored fragments are not removed by this
change. Rebuild the collection from its original sources to remove them.

Set `RETRIEVAL_MAX_DISTANCE` to exclude weak matches from the retrieved context.
Leave it unset to keep all top-k matches, which preserves the default behaviour.
Restart the backend and bot after changing the setting.

```sh
RETRIEVAL_TOP_K=5
RETRIEVAL_MAX_DISTANCE=0.5
```

The cutoff is inclusive. A chunk with distance equal to the cutoff is kept.
Zero is valid and keeps only chunks with zero distance. Negative values,
infinity and NaN are rejected at startup.

Distances are raw Chroma distances, with lower values indicating closer vectors.
Wingman's default collection uses squared L2 distance. Values depend on the
embedding model and collection metric, so `0.5` is an example, not a recommended
threshold. Calibrate the cutoff against representative questions and known
relevant chunks before enabling it. Changing the embedding model or collection
metric requires recalibration.

The shared vector store returns each chunk's distance alongside its content and
metadata. Filtering applies to both API questions and Slack job payloads. Raw
distances are internal retrieval diagnostics; the public answer and source
schemas remain unchanged. Operator rules still bypass retrieval.

If every chunk is excluded, generation receives empty retrieved context. Pi
conversation history can still contribute to an answer. This setting does not
implement a refusal policy or guarantee that an answer is grounded.

Slack thread indexing uses a stable chunk ID built from the channel ID and
message timestamp. Re-indexing the same messages updates their content and
embeddings instead of appending duplicates. This applies to the bot and the
`/api/index/thread` endpoint through their shared RAG engine. Messages without
text or a timestamp are skipped; absent user and thread metadata is omitted.

Existing chunks stored with random IDs are not removed automatically. Rebuild
those collections from their original sources to remove historical duplicates.
Re-indexing only updates messages present in the supplied thread; it does not
remove chunks for deleted Slack messages or handle Slack edit/delete events.

`POST /api/index/thread?channel_id=...&thread_ts=...` indexes the saved root
message and its saved replies in timestamp order, within the requested channel.
The root is included even when its `thread_ts` is absent. A root-only thread is
valid; saved replies can also be indexed when the root was never stored. If
neither the root nor any replies are saved in that channel, the API returns
HTTP 404. It does not fetch missing messages from Slack.

The fixture tests use temporary local Chroma storage and fixed embeddings.
They make no embedding, model or Slack calls. To show the captured transcript
with the query, chunks and distances before and after filtering or repeated
thread indexing, run the backend
gate with captured output for passing tests enabled.

```sh
PYTEST_ADDOPTS=-rP mise run test-backend
```
