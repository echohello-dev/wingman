"""Capture only loopback fixture API behaviour using curl."""
import json
import shlex
import subprocess
from pathlib import Path

base = "http://127.0.0.1:18055"
marker = Path(__file__).resolve().parents[1] / "offline-delete/fail-delete"

def request(method, path, expected, payload=None):
    args = ["curl", "-sS", "-X", method, base + path]
    if payload is not None:
        args += ["-H", "Content-Type: application/json", "-d", json.dumps(payload)]
    args += ["-w", "\n%{http_code}"]
    print("$ " + shlex.join(args), flush=True)
    result = subprocess.run(args, capture_output=True, text=True, check=True)
    body, status = result.stdout.rsplit("\n", 1)
    value = json.loads(body)
    print("HTTP " + status)
    print(json.dumps(value, indent=2))
    print()
    assert int(status) == expected, (body, status, expected)
    return value

print("Local SQLite and Chroma, fixed embeddings, Slack authentication mocked and API calls blocked.")
print("No real tokens, remote databases, model calls or paid embeddings. Distances are fixture squared L2 values.")
request("GET", "/health", 200)
payload = {"title": "VPN guide", "content": "Reset VPN via IT portal.", "source": "api"}
first = request("POST", "/api/documents", 200, payload)["id"]
second = request("POST", "/api/documents", 200, payload)["id"]
query = {"question": "How do I reset VPN?"}
before = request("POST", "/api/retrieval/preview", 200, query)
assert len(before["items"]) == 2
assert {item["metadata"]["document_id"] for item in before["items"]} == {first, second}
assert [item["distance"] for item in before["items"]] == [1.0, 1.0]
print("Inject fixture Chroma deletion outage.")
marker.touch()
try:
    failed = request("DELETE", f"/api/documents/{first}", 503)
    assert failed["detail"]["document_id"] == first
    request("GET", f"/api/documents/{first}", 200)
finally:
    marker.unlink()
print("Remove fixture outage and retry the same saved ID.")
request("DELETE", f"/api/documents/{first}", 200)
request("GET", f"/api/documents/{first}", 404)
request("POST", f"/api/documents/{first}/index", 404)
request("DELETE", f"/api/documents/{first}", 404)
remaining = request("GET", "/api/documents", 200)
assert [item["id"] for item in remaining["items"]] == [second]
after = request("POST", "/api/retrieval/preview", 200, query)
assert len(after["items"]) == 1
assert after["items"][0]["metadata"]["document_id"] == second
assert after["items"][0]["content"] == payload["content"]
assert after["items"][0]["distance"] == 1.0
request("DELETE", "/api/documents/invalid", 422)
print("All curl status, ownership, saved-record and raw-distance assertions passed.")
