# Retrieval tuning

Wingman retrieves up to `RETRIEVAL_TOP_K` chunks, defaulting to 5. A request with
a channel ID searches only that channel before applying the limit. An unscoped
request searches the whole collection.

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

The fixture tests use temporary local Chroma storage and fixed embeddings.
They make no embedding, model or Slack calls. To show the captured transcript
with the query, chunks and distances before and after filtering, run the backend
gate with captured output for passing tests enabled.

```sh
PYTEST_ADDOPTS=-rP mise run test-backend
```
