# Operator rules

Operator rules pin an approved answer to a question pattern. When a rule
fires, Wingman returns the canned response straight away, without retrieval
or a generated answer. Use them when the generic answer is wrong or stale
and the correct wording is known.

Rules are checked on the `/api/ask` path through `RAGEngine.generate_response`
and on the Slack submit path through `RAGEngine.submit_slack` in
[backend/app/rag.py](../backend/app/rag.py). Slack's pinned answers use the Pi
outbox for delivery without model generation. The matcher lives in
[backend/app/rules.py](../backend/app/rules.py).

## Configure

Set one of these in `.env`. The file wins when both are set. With neither
set, or with an empty value, rules are a no-op.

```bash
# Inline JSON
OPERATOR_RULES_JSON=[{"id":"vpn-reset","keywords":["reset vpn"],"response":"Use the IT portal to reset VPN access."}]

# Or a JSON file with the same list shape
OPERATOR_RULES_FILE=/path/to/operator-rules.json
```

## Rule shape

| Field | Required | Notes |
| --- | --- | --- |
| `id` | yes | Short unique name, reported in the response sources |
| `keywords` | yes | One or more patterns; any one can fire the rule |
| `response` | yes | The exact answer returned |
| `match_type` | no | `contains` (default), `exact` or `regex` |
| `priority` | no | Higher wins first; config order breaks ties. Default 0 |
| `enabled` | no | Set `false` to park a rule without deleting it. Default true |

Matching is case-insensitive. `contains` checks whether the pattern appears
anywhere in the question, `exact` needs the whole question to equal the
pattern, and `regex` treats the pattern as a regular expression searched
against the question.

## Example

```json
[
  {
    "id": "vpn-reset",
    "keywords": ["reset vpn", "vpn password"],
    "response": "Use the IT portal at https://it.example.com/vpn to reset VPN access.",
    "priority": 10
  },
  {
    "id": "office-hours",
    "keywords": ["office hours"],
    "match_type": "exact",
    "response": "The support desk runs 9am to 5pm, Monday to Friday."
  }
]
```

## Failure behaviour

A rule with a missing id, no usable keywords, an empty response, an unknown
match type, a non-integer priority or a bad regex is logged and skipped.
Invalid JSON, a missing file or a non-list config loads as no rules. Bad
config never stops the backend from starting.

## Preview the winning rule

`POST /api/rules/preview` uses the backend's loaded matcher to show which rule
would answer a question. It does not retrieve chunks, generate an answer,
submit a Pi job, write to the database or send a Slack message. An unmatched
question returns a null match without falling back to generation.

```sh
curl -sS http://localhost:8000/api/rules/preview \
  -H 'Content-Type: application/json' \
  -d '{"question":"How do I RESET VPN access?"}'
```

With the example rules above, the response is:

```json
{
  "question": "How do I RESET VPN access?",
  "match": {
    "rule_id": "vpn-reset",
    "match_type": "contains",
    "matched_keyword": "reset vpn",
    "priority": 10,
    "response": "Use the IT portal at https://it.example.com/vpn to reset VPN access."
  }
}
```

The winner follows the existing priority, config-order and enabled-rule policy.
The response preserves the approved answer's formatting. Surrounding question
whitespace is trimmed; missing, blank and non-string questions return HTTP 422
before matching. No match returns HTTP 200 with `"match": null`. Matcher failures
return HTTP 503 with a generic detail rather than configuration internals.

Rules are loaded once per process. Preview does not reload a file or validate
unsaved configuration. Restart both backend and bot after changing the rule
configuration; a backend preview cannot confirm what a separately running bot
has loaded. For Slack mentions, preview the question after removing the bot
mention, as the handler does before matching.

Like the other management endpoints, preview has no built-in authentication.
Keep it behind trusted access controls: it returns the full approved answer
and the pattern that matched, which can contain internal information. It
does not evaluate source permissions or whether the answer is still correct.

## Current limits

Combining a rule with fetched source data before summarising remains open
under the parent issue. Preview inspects the current deterministic winner;
it does not list shadowed rules or change matching policy.
