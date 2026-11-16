"""Operator rule preview tests with fixture config and blocked external work."""
import os
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SLACK_BOT_TOKEN", "xoxb-fixture-only")
os.environ.setdefault("SLACK_SIGNING_SECRET", "fixture-only")

with patch("slack_sdk.WebClient.auth_test", return_value={
    "ok": True, "bot_id": "BTEST", "user_id": "UTEST", "team_id": "TTEST",
}):
    import app.main as main

from app import agent_runtime, database, rules


@pytest.fixture
def rule_api(monkeypatch):
    blocked = Mock(side_effect=AssertionError("Preview must only match loaded rules"))
    monkeypatch.setattr(main.vector_store, "similarity_search", blocked)
    monkeypatch.setattr(agent_runtime, "generate", blocked)
    monkeypatch.setattr(agent_runtime, "submit", blocked)
    monkeypatch.setattr(database, "SessionLocal", blocked)
    monkeypatch.setattr("slack_sdk.WebClient.api_call", blocked)
    monkeypatch.setattr("slack_bolt.adapter.socket_mode.SocketModeHandler.start", blocked)
    monkeypatch.setattr(rules, "rule_engine", rules.RuleEngine())
    monkeypatch.setattr(main, "init_db", lambda: None)
    with TestClient(main.app, raise_server_exceptions=False) as client:
        # Startup storage is unrelated; the endpoint itself needs no database.
        yield client
    blocked.assert_not_called()


def install_rules(monkeypatch, *entries):
    monkeypatch.setattr(rules, "rule_engine", rules.RuleEngine(rules.parse_rules(list(entries))))


def rule(rule_id="vpn", **options):
    return {"id": rule_id, "keywords": ["reset vpn"], "response": "Use the IT portal.", **options}


def preview(client, question="How do I RESET VPN access?"):
    return client.post("/api/rules/preview", json={"question": question})


@pytest.mark.parametrize(("match_type", "keywords", "question", "winner"), [
    ("contains", ["vpn password", "reset vpn"], "How do I RESET VPN access?", "reset vpn"),
    ("exact", ["office hours"], "OFFICE HOURS", "office hours"),
    ("regex", [r"ticket #?\d+"], "Where is TICKET #4821?", r"ticket #?\d+"),
])
def test_preview_returns_winning_rule_and_exact_response(rule_api, monkeypatch, match_type, keywords, question, winner):
    response_text = "  Approved wording.\nKeep the formatting.  "
    install_rules(monkeypatch, rule(match_type=match_type, keywords=keywords, response=response_text, priority=3))
    response = preview(rule_api, question)
    assert response.status_code == 200
    assert response.json() == {
        "question": question,
        "match": {
            "rule_id": "vpn", "match_type": match_type, "matched_keyword": winner,
            "priority": 3, "response": response_text,
        },
    }


def test_preview_uses_priority_config_order_and_disabled_rule_policy(rule_api, monkeypatch):
    install_rules(monkeypatch,
        rule("low", priority=1), rule("disabled", priority=100, enabled=False),
        rule("first", priority=10), rule("second", priority=10),
    )
    assert preview(rule_api).json()["match"]["rule_id"] == "first"


@pytest.mark.parametrize("entries", [[], [rule()], [rule(enabled=False)]])
def test_preview_returns_null_for_no_match_without_falling_back_to_generation(rule_api, monkeypatch, entries):
    install_rules(monkeypatch, *entries)
    response = preview(rule_api, "How do I reset email?")
    assert response.status_code == 200
    assert response.json() == {"question": "How do I reset email?", "match": None}


def test_preview_trims_question_and_uses_current_shared_matcher(rule_api, monkeypatch):
    install_rules(monkeypatch, rule("first"))
    question = "How do I reset VPN?"
    response = preview(rule_api, f" \t{question}\n ")
    assert response.json()["question"] == question
    assert response.json()["match"]["rule_id"] == "first"
    install_rules(monkeypatch, rule("replacement"))
    assert preview(rule_api, question).json()["match"]["rule_id"] == "replacement"


@pytest.mark.parametrize("payload", [
    {}, {"question": ""}, {"question": " \n\t "}, {"question": None},
    {"question": 123}, {"question": True}, {"question": []}, {"question": {}},
])
def test_preview_rejects_invalid_input_before_matching(rule_api, monkeypatch, payload):
    matcher = Mock(side_effect=AssertionError("Invalid input must not reach matching"))
    monkeypatch.setattr(main.rag_engine, "match_operator_rule", matcher)
    assert rule_api.post("/api/rules/preview", json=payload).status_code == 422
    matcher.assert_not_called()


def test_preview_matches_api_answer_and_slack_job_without_submitting_a_job(rule_api, monkeypatch):
    install_rules(monkeypatch, rule("low"), rule("approved", priority=10))
    question = "How do I reset VPN?"
    matched = preview(rule_api, question).json()["match"]
    agent_runtime.submit.assert_not_called()
    answer = main.rag_engine.generate_response(question)
    assert answer["answer"] == matched["response"]
    assert answer["sources"] == [{"source": "operator_rule", "rule_id": matched["rule_id"]}]
    # Replace the blocked submit only for this separate parity check. Nothing is delivered.
    submit = Mock(return_value={"id": "fixture-job", "status": "pending"})
    monkeypatch.setattr(agent_runtime, "submit", submit)
    main.rag_engine.submit_slack(question, "CFIXTURE", "fixture-conversation", "fixture-request", "1.0")
    payload = submit.call_args.args[0]
    assert payload["operator_answer"] == matched["response"]
    assert payload["sources"] == answer["sources"]


def test_preview_reports_matcher_failure_without_exposing_details(rule_api, monkeypatch):
    monkeypatch.setattr(main.rag_engine, "match_operator_rule", Mock(side_effect=RuntimeError("private config details")))
    response = preview(rule_api)
    assert response.status_code == 503
    assert response.json() == {"detail": "Operator rule preview is unavailable"}
