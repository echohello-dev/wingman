"""
Deterministic operator rules for canned answers.

Operators can pin an exact answer to a question pattern so Wingman replies
with approved wording instead of a generated answer. Rules are checked
before retrieval and generation. An empty or invalid config is a no-op,
and a bad rule is logged and skipped rather than breaking startup.
"""
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Optional

logger = logging.getLogger(__name__)

MATCH_TYPES = ("contains", "exact", "regex")


@dataclass(frozen=True)
class OperatorRule:
    """One canned answer pinned to one or more question patterns."""

    id: str
    keywords: tuple
    response: str
    match_type: str = "contains"
    priority: int = 0
    enabled: bool = True


@dataclass(frozen=True)
class RuleMatch:
    """A successful match, with the pattern that fired."""

    rule: OperatorRule
    matched_keyword: str


def _parse_rule(raw: Any) -> Optional[OperatorRule]:
    """Validate one raw config entry. Return None when it is unusable."""
    if not isinstance(raw, dict):
        logger.warning("Skipping operator rule that is not an object: %r", raw)
        return None

    rule_id = raw.get("id")
    keywords = raw.get("keywords")
    response = raw.get("response")
    match_type = raw.get("match_type", "contains")
    priority = raw.get("priority", 0)
    enabled = raw.get("enabled", True)

    if not isinstance(rule_id, str) or not rule_id.strip():
        logger.warning("Skipping operator rule with a missing id: %r", raw)
        return None
    if (
        not isinstance(keywords, list)
        or not keywords
        or not all(isinstance(k, str) and k.strip() for k in keywords)
    ):
        logger.warning("Skipping operator rule %s with no usable keywords", rule_id)
        return None
    if not isinstance(response, str) or not response.strip():
        logger.warning("Skipping operator rule %s with an empty response", rule_id)
        return None
    if match_type not in MATCH_TYPES:
        logger.warning(
            "Skipping operator rule %s with unknown match_type %r", rule_id, match_type
        )
        return None
    if not isinstance(priority, int) or isinstance(priority, bool):
        logger.warning("Skipping operator rule %s with a non-integer priority", rule_id)
        return None
    if not isinstance(enabled, bool):
        logger.warning("Skipping operator rule %s with a non-boolean enabled flag", rule_id)
        return None
    if match_type == "regex":
        for keyword in keywords:
            try:
                re.compile(keyword)
            except re.error as exc:
                logger.warning("Skipping operator rule %s with bad regex %r: %s", rule_id, keyword, exc)
                return None

    return OperatorRule(
        id=rule_id.strip(),
        keywords=tuple(k.strip() for k in keywords),
        response=response,
        match_type=match_type,
        priority=priority,
        enabled=enabled,
    )


def parse_rules(raw_rules: Any) -> List[OperatorRule]:
    """Validate a decoded JSON value into rules, skipping bad entries."""
    if raw_rules is None:
        return []
    if not isinstance(raw_rules, list):
        logger.warning("Operator rules config is not a list, ignoring it")
        return []
    rules = []
    for raw in raw_rules:
        rule = _parse_rule(raw)
        if rule is not None:
            rules.append(rule)
    return rules


def load_rules(json_text: Optional[str] = None, file_path: Optional[str] = None) -> List[OperatorRule]:
    """Load rules from inline JSON or a JSON file. File wins when both are set."""
    text = json_text
    if file_path:
        path = Path(file_path)
        if not path.is_file():
            logger.error("Operator rules file not found: %s", file_path)
            return []
        text = path.read_text(encoding="utf-8")
    if not text or not text.strip():
        return []
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error("Operator rules config is not valid JSON: %s", exc)
        return []
    return parse_rules(decoded)


class RuleEngine:
    """Matches a question against the enabled operator rules."""

    def __init__(self, rules: Iterable[OperatorRule] = ()):
        # Higher priority first. The sort is stable, so config order
        # breaks ties between rules with equal priority.
        self._rules = sorted(
            (rule for rule in rules if rule.enabled),
            key=lambda rule: -rule.priority,
        )

    @property
    def rules(self) -> List[OperatorRule]:
        return list(self._rules)

    @classmethod
    def from_config(cls, json_text: Optional[str] = None, file_path: Optional[str] = None) -> "RuleEngine":
        return cls(load_rules(json_text=json_text, file_path=file_path))

    @classmethod
    def from_settings(cls, settings_obj: Any = None) -> "RuleEngine":
        if settings_obj is None:
            from app.config import settings as settings_obj
        return cls.from_config(
            json_text=getattr(settings_obj, "OPERATOR_RULES_JSON", None),
            file_path=getattr(settings_obj, "OPERATOR_RULES_FILE", None),
        )

    def match(self, question: Optional[str]) -> Optional[RuleMatch]:
        """Return the first matching rule, or None when nothing fires."""
        if not question or not question.strip():
            return None
        text = question.strip()
        lowered = text.lower()
        for rule in self._rules:
            for keyword in rule.keywords:
                if self._matches(rule, keyword, text, lowered):
                    return RuleMatch(rule=rule, matched_keyword=keyword)
        return None

    @staticmethod
    def _matches(rule: OperatorRule, keyword: str, text: str, lowered: str) -> bool:
        if rule.match_type == "exact":
            return lowered == keyword.lower()
        if rule.match_type == "regex":
            return re.search(keyword, text, re.IGNORECASE) is not None
        return keyword.lower() in lowered


# Global instance, following the module-level singleton pattern in this codebase.
rule_engine = RuleEngine.from_settings()
