"""Indexing and retrieval regressions using local Chroma and fixed embeddings."""
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import chromadb
import pytest
from chromadb.config import Settings as ChromaSettings
from chromadb.telemetry.product.posthog import Posthog
from langchain_community.vectorstores import Chroma
from langchain_core.embeddings import Embeddings
from pydantic import ValidationError

from app.config import Settings, settings
from app.rules import RuleEngine
from app.vector_store import VectorStore


class FixtureEmbeddings(Embeddings):
    def embed_documents(self, texts):
        distances = {
            "Other channel first": 0.0,
            "Other channel second": 0.1,
            "Shared document": 0.2,
            "Target channel first": 1.0,
            "Target channel second": 2.0,
        }
        return [[distances[text], 1.0] for text in texts]

    def embed_query(self, text):
        return [0.0, 1.0]


@pytest.fixture
def empty_vector(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "RETRIEVAL_TOP_K", 2)
    monkeypatch.setattr(settings, "RETRIEVAL_MAX_DISTANCE", None)
    monkeypatch.setattr(Posthog, "capture", lambda *args, **kwargs: None)
    client = chromadb.PersistentClient(
        path=str(tmp_path), settings=ChromaSettings(anonymized_telemetry=False),
    )
    store = VectorStore()
    store.vector_store = Chroma(
        client=client, collection_name="retrieval-fixture",
        embedding_function=FixtureEmbeddings(),
    )
    store._initialized = True
    return store


@pytest.fixture
def vector(empty_vector):
    empty_vector.add_documents(
        ["Other channel first", "Other channel second", "Shared document",
         "Target channel first", "Target channel second"],
        [{"source": "slack", "channel_id": "COTHER"},
         {"source": "slack", "channel_id": "COTHER"},
         {"source": "api"},
         {"source": "slack", "channel_id": "CTARGET"},
         {"source": "slack", "channel_id": "CTARGET"}],
    )
    return empty_vector


@pytest.mark.parametrize("channel_id", [None, "CTARGET"])
@pytest.mark.parametrize("max_distance", [None, 1.0])
def test_search_empty_collection_returns_no_matches(
    empty_vector, monkeypatch, channel_id, max_distance,
):
    monkeypatch.setattr(settings, "RETRIEVAL_MAX_DISTANCE", max_distance)
    assert empty_vector.similarity_search(
        "How do I connect?", channel_id=channel_id,
    ) == []


def test_first_document_can_be_indexed_and_retrieved(empty_vector):
    ids = empty_vector.add_documents(
        ["Target channel first"], [{"source": "slack", "channel_id": "CTARGET"}],
    )
    assert len(ids) == 1
    assert empty_vector.similarity_search("How do I connect?", channel_id="CTARGET") == [
        {
            "content": "Target channel first",
            "metadata": {"source": "slack", "channel_id": "CTARGET"},
            "distance": 1.0,
        },
    ]


@pytest.mark.parametrize("operation", ["add", "search"])
def test_missing_adapter_still_raises(monkeypatch, operation):
    store = VectorStore()
    monkeypatch.setattr(store, "_ensure_initialized", lambda: None)
    with pytest.raises(RuntimeError, match="Vector store not initialized"):
        if operation == "add":
            store.add_documents(["Target channel first"])
        else:
            store.similarity_search("How do I connect?")


def test_channel_filter_runs_before_top_k(vector):
    results = vector.similarity_search("How do I connect?", channel_id="CTARGET")
    assert [item["content"] for item in results] == [
        "Target channel first", "Target channel second",
    ]


def test_unscoped_search_preserves_global_ranking_and_explicit_k(vector):
    results = vector.similarity_search("How do I connect?", k=3)
    assert [item["content"] for item in results] == [
        "Other channel first", "Other channel second", "Shared document",
    ]
    assert [item["distance"] for item in results] == pytest.approx([0.0, 0.01, 0.04])


def test_distance_cutoff_is_inclusive_and_preserves_channel_scope(vector, monkeypatch):
    query = "How do I connect?"
    before = vector.similarity_search(query, channel_id="CTARGET")
    monkeypatch.setattr(settings, "RETRIEVAL_MAX_DISTANCE", 1.0)
    after = vector.similarity_search(query, channel_id="CTARGET")

    assert [item["distance"] for item in before] == [1.0, 4.0]
    assert after == [before[0]]
    print(json.dumps({
        "query": query,
        "channel_id": "CTARGET",
        "top_k": 2,
        "max_distance": 1.0,
        "before": before,
        "after": after,
    }, indent=2))


def test_zero_distance_cutoff_keeps_only_exact_vector_matches(vector, monkeypatch):
    monkeypatch.setattr(settings, "RETRIEVAL_MAX_DISTANCE", 0.0)
    results = vector.similarity_search("How do I connect?", k=5)
    assert [item["content"] for item in results] == ["Other channel first"]
    assert results[0]["distance"] == 0.0


@pytest.mark.parametrize("value", [-1, "nan", "inf", "-inf", "invalid"])
def test_invalid_distance_config_is_rejected(value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, RETRIEVAL_MAX_DISTANCE=value)


@pytest.mark.parametrize("value", [None, 0, "1.5"])
def test_distance_config_accepts_unset_or_nonnegative_finite_values(value):
    config = Settings(_env_file=None, RETRIEVAL_MAX_DISTANCE=value)
    assert config.RETRIEVAL_MAX_DISTANCE == (float(value) if value is not None else None)


def test_empty_channel_does_not_fall_back_to_global_results(vector):
    assert vector.similarity_search("How do I connect?", channel_id="CEMPTY") == []


@pytest.mark.parametrize("path", ["api", "slack"])
@pytest.mark.parametrize("max_distance,expected_count", [(None, 2), (1.0, 1), (0.0, 0)])
def test_rag_payload_uses_scoped_matches(
    vector, monkeypatch, path, max_distance, expected_count,
):
    monkeypatch.setattr(settings, "RETRIEVAL_MAX_DISTANCE", max_distance)
    monkeypatch.setitem(sys.modules, "app.vector_store", SimpleNamespace(vector_store=vector))
    spec = importlib.util.spec_from_file_location(
        "retrieval_rag_under_test", Path(__file__).parents[1] / "app/rag.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.rules, "rule_engine", RuleEngine([]))
    generate = Mock(return_value={"answer": "fixture answer"})
    submit = Mock(return_value={"id": "fixture-job", "status": "pending"})
    monkeypatch.setattr(module.agent_runtime, "generate", generate)
    monkeypatch.setattr(module.agent_runtime, "submit", submit)

    if path == "api":
        module.rag_engine.generate_response(
            "How do I connect?", channel_id="CTARGET", request_id="fixture-api",
        )
        payload = generate.call_args.args[0]
    else:
        module.rag_engine.submit_slack(
            "How do I connect?", "CTARGET", "fixture:thread", "fixture-slack", "1.2",
        )
        payload = submit.call_args.args[0]
        assert payload["slack"] == {"channel": "CTARGET", "thread_ts": "1.2"}

    expected_context = [
        "From slack:\nTarget channel first", "From slack:\nTarget channel second",
    ]
    assert payload["context"] == "\n\n".join(expected_context[:expected_count])
    assert payload["sources"] == [
        {"source": "slack", "channel_id": "CTARGET"},
        {"source": "slack", "channel_id": "CTARGET"},
    ][:expected_count]
