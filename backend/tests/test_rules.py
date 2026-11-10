"""Unit tests for deterministic operator rules and the RAG short-circuit."""
import json
from types import SimpleNamespace
from unittest.mock import Mock

from app import rag as rag_module
from app.rules import OperatorRule, RuleEngine, load_rules, parse_rules


def engine(*rules):
    return RuleEngine(list(rules))


def rule(rule_id, keywords, response="canned", **kwargs):
    return OperatorRule(id=rule_id, keywords=tuple(keywords), response=response, **kwargs)


class TestMatching:
    def test_contains_is_case_insensitive(self):
        match = engine(rule("vpn", ["reset vpn"])).match("How do I RESET VPN access?")
        assert match is not None
        assert match.rule.id == "vpn"
        assert match.rule.response == "canned"

    def test_contains_needs_the_keyword(self):
        assert engine(rule("vpn", ["reset vpn"])).match("How do I reset email?") is None

    def test_any_keyword_can_match(self):
        match = engine(rule("hours", ["opening hours", "when open"])).match("When open?")
        assert match is not None
        assert match.matched_keyword == "when open"

    def test_exact_needs_the_whole_question(self):
        eng = engine(rule("ping", ["ping"], match_type="exact"))
        assert eng.match("  Ping ") is not None
        assert eng.match("ping the server") is None

    def test_regex_match(self):
        eng = engine(rule("ticket", [r"ticket #?\d+"], match_type="regex"))
        assert eng.match("Where is ticket #4821?") is not None
        assert eng.match("Where is my ticket?") is None

    def test_blank_question_never_matches(self):
        eng = engine(rule("vpn", ["vpn"]))
        assert eng.match("") is None
        assert eng.match("   ") is None
        assert eng.match(None) is None

    def test_no_rules_is_a_no_op(self):
        assert RuleEngine().match("anything at all") is None


class TestOrderingAndEnabled:
    def test_higher_priority_wins(self):
        eng = engine(
            rule("low", ["vpn"], response="low", priority=1),
            rule("high", ["vpn"], response="high", priority=10),
        )
        assert eng.match("vpn help").rule.response == "high"

    def test_config_order_breaks_priority_ties(self):
        eng = engine(
            rule("first", ["vpn"], response="first"),
            rule("second", ["vpn"], response="second"),
        )
        assert eng.match("vpn help").rule.response == "first"

    def test_disabled_rule_never_matches(self):
        eng = engine(rule("off", ["vpn"], enabled=False))
        assert eng.match("vpn help") is None
        assert eng.rules == []


class TestConfigLoading:
    def test_parse_valid_rules(self):
        rules = parse_rules([
            {"id": "a", "keywords": ["vpn"], "response": "Use the portal."},
            {"id": "b", "keywords": ["hours"], "response": "9 to 5.", "priority": 3, "match_type": "exact"},
        ])
        assert [r.id for r in rules] == ["a", "b"]
        assert rules[1].priority == 3
        assert rules[1].match_type == "exact"

    def test_parse_skips_invalid_entries(self):
        rules = parse_rules([
            {"keywords": ["vpn"], "response": "no id"},
            {"id": "x", "keywords": [], "response": "no keywords"},
            {"id": "y", "keywords": ["vpn"], "response": ""},
            {"id": "z", "keywords": ["vpn"], "response": "ok", "match_type": "fuzzy"},
            {"id": "w", "keywords": ["vpn"], "response": "ok", "priority": "high"},
            "not an object",
            {"id": "good", "keywords": ["vpn"], "response": "kept"},
        ])
        assert [r.id for r in rules] == ["good"]

    def test_parse_skips_bad_regex(self):
        assert parse_rules([
            {"id": "bad", "keywords": ["[unclosed"], "response": "x", "match_type": "regex"},
        ]) == []

    def test_parse_rejects_non_list(self):
        assert parse_rules({"id": "a"}) == []
        assert parse_rules(None) == []

    def test_load_from_json_text(self):
        text = json.dumps([{"id": "a", "keywords": ["vpn"], "response": "portal"}])
        assert RuleEngine.from_config(json_text=text).match("vpn?").rule.response == "portal"

    def test_load_invalid_json_is_empty(self):
        assert load_rules(json_text="{not json") == []
        assert load_rules(json_text="") == []
        assert load_rules() == []

    def test_load_from_file_and_file_wins(self, tmp_path):
        path = tmp_path / "rules.json"
        path.write_text(json.dumps([
            {"id": "file", "keywords": ["vpn"], "response": "from file"},
        ]), encoding="utf-8")
        inline = json.dumps([{"id": "inline", "keywords": ["vpn"], "response": "from inline"}])
        eng = RuleEngine.from_config(json_text=inline, file_path=str(path))
        assert eng.match("vpn?").rule.response == "from file"

    def test_load_missing_file_is_empty(self, tmp_path):
        assert load_rules(file_path=str(tmp_path / "nope.json")) == []

    def test_from_settings_reads_both_fields(self):
        fake = SimpleNamespace(
            OPERATOR_RULES_JSON=json.dumps([
                {"id": "a", "keywords": ["vpn"], "response": "portal"},
            ]),
            OPERATOR_RULES_FILE=None,
        )
        assert RuleEngine.from_settings(fake).match("vpn help") is not None
        empty = SimpleNamespace(OPERATOR_RULES_JSON=None, OPERATOR_RULES_FILE=None)
        assert RuleEngine.from_settings(empty).match("vpn help") is None


class TestRagShortCircuit:
    def _install_engine(self, monkeypatch, eng):
        monkeypatch.setattr(rag_module.rules, "rule_engine", eng)

    def test_matched_question_skips_retrieval_and_generation(self, monkeypatch):
        self._install_engine(monkeypatch, engine(rule("vpn", ["reset vpn"], response="Use the portal.")))
        search = Mock(side_effect=AssertionError("retrieval must not run"))
        generate = Mock(side_effect=AssertionError("generation must not run"))
        monkeypatch.setattr(rag_module.vector_store, "similarity_search", search)
        monkeypatch.setattr(rag_module.agent_runtime, "generate", generate)

        result = rag_module.rag_engine.generate_response("How do I reset VPN access?")

        assert result == {
            "answer": "Use the portal.",
            "sources": [{"source": "operator_rule", "rule_id": "vpn"}],
            "confidence": "high",
        }

    def test_unmatched_question_still_uses_generation(self, monkeypatch):
        self._install_engine(monkeypatch, engine(rule("vpn", ["reset vpn"])))
        monkeypatch.setattr(rag_module.vector_store, "similarity_search", lambda _: [])
        expected = {"answer": "generated", "sources": [], "confidence": "low"}
        monkeypatch.setattr(rag_module.agent_runtime, "generate", lambda _: expected)

        assert rag_module.rag_engine.generate_response("What is RAG?") == expected


class TestSlackShortCircuit:
    def _install_engine(self, monkeypatch, eng):
        monkeypatch.setattr(rag_module.rules, "rule_engine", eng)

    def test_matched_slack_question_skips_retrieval_and_carries_pinned_answer(self, monkeypatch):
        self._install_engine(monkeypatch, engine(rule("vpn", ["reset vpn"], response="Use the portal.")))
        search = Mock(side_effect=AssertionError("retrieval must not run"))
        monkeypatch.setattr(rag_module.vector_store, "similarity_search", search)
        submitted = {}
        def fake_submit(payload):
            submitted["payload"] = payload
            return {"id": "job-1", "status": "pending"}
        monkeypatch.setattr(rag_module.agent_runtime, "submit", fake_submit)

        result = rag_module.rag_engine.submit_slack(
            "How do I reset VPN access?", "C1", "team:thread:C1:1.2", "event-1", "1.2"
        )

        assert result == {"id": "job-1", "status": "pending"}
        payload = submitted["payload"]
        assert payload["operator_answer"] == "Use the portal."
        assert payload["sources"] == [{"source": "operator_rule", "rule_id": "vpn"}]
        assert payload["context"] == ""
        assert payload["question"] == "How do I reset VPN access?"
        assert payload["request_id"] == "event-1"
        assert payload["conversation_id"] == "team:thread:C1:1.2"
        assert payload["slack"] == {"channel": "C1", "thread_ts": "1.2"}

    def test_unmatched_slack_question_uses_retrieval_without_pinned_answer(self, monkeypatch):
        self._install_engine(monkeypatch, engine(rule("vpn", ["reset vpn"])))
        monkeypatch.setattr(
            rag_module.vector_store, "similarity_search",
            lambda _, **kwargs: [{"content": "Doc", "metadata": {"source": "slack", "channel_id": "C1"}}],
        )
        submitted = {}
        def fake_submit(payload):
            submitted["payload"] = payload
            return {"id": "job-2", "status": "pending"}
        monkeypatch.setattr(rag_module.agent_runtime, "submit", fake_submit)

        rag_module.rag_engine.submit_slack("What is RAG?", "C1", "team:thread:C1:1.2", "event-2", "1.2")

        payload = submitted["payload"]
        assert "operator_answer" not in payload
        assert "Doc" in payload["context"]
        assert payload["slack"] == {"channel": "C1", "thread_ts": "1.2"}
