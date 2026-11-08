# Operator rules

Operator rules pin an approved answer to a question pattern. When a rule
fires, Wingman returns the canned response straight away, without retrieval
or a generated answer. Use them when the generic answer is wrong or stale
and the correct wording is known.

Rules are checked on the `/api/ask` path through `RAGEngine.generate_response`
in [backend/app/rag.py](../backend/app/rag.py). The matcher lives in
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

## Current limits

Rules apply to the API ask path in this slice. Slack delivery still goes
through the Pi Durable job flow, so wiring rules into the Slack handlers is
a follow-up. Combining a rule with fetched source data before summarising
is also still open under the parent issue.
