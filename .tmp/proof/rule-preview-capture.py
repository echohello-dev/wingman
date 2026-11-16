"""Capture curl requests against the offline backend started on port 18059."""
import json
from pathlib import Path
import shlex
import subprocess


base = "http://127.0.0.1:18059"
transcript = [
    "Offline operator-rule preview with rule-preview-config.json.",
    "Slack API, Socket Mode, retrieval and Pi calls raise in the proof process.",
    "No chunks or distances apply: this endpoint only inspects loaded rules.",
]


def request(path, payload=None, status=200):
    command = ["curl", "--silent", "--show-error", "--include", "--max-time", "10", f"{base}{path}"]
    if payload is not None:
        command += ["-H", "Content-Type: application/json", "-d", json.dumps(payload)]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    headers, body = result.stdout.split("\n\n", 1)
    assert f" {status} " in headers.splitlines()[0], result.stdout
    data = json.loads(body)
    transcript.extend(["", "$ " + shlex.join(command), headers, json.dumps(data, indent=2)])
    return data


assert request("/health") == {"status": "healthy"}
winning = request("/api/rules/preview", {"question": "  How do I RESET VPN access?\n"})
assert winning["question"] == "How do I RESET VPN access?"
assert winning["match"]["rule_id"] == "vpn-reset"
assert winning["match"]["priority"] == 10
assert request("/api/rules/preview", {"question": "OFFICE HOURS"})["match"]["match_type"] == "exact"
assert request("/api/rules/preview", {"question": "Where is TICKET #4821?"})["match"]["match_type"] == "regex"
assert request("/api/rules/preview", {"question": "How do I reset email?"})["match"] is None
request("/api/rules/preview", {"question": " \n\t "}, status=422)
request("/api/rules/preview", {"question": 123}, status=422)
answer = request("/api/ask", {"question": "How do I RESET VPN access?"})
assert answer["answer"] == winning["match"]["response"]
assert answer["sources"] == [{"source": "operator_rule", "rule_id": winning["match"]["rule_id"]}]
transcript.extend(["", "All response assertions passed. Preview and API answer select the same rule."])
Path(__file__).with_name("rule-preview-api.txt").write_text("\n".join(transcript) + "\n")
