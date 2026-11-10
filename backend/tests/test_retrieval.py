"""Channel retrieval regressions using local Chroma and fixed embeddings."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_community.vectorstores import Chroma
from langchain_core.embeddings import Embeddings
import pytest
from chromadb.telemetry.product.posthog import Posthog

from app.config import settings
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
def vector(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "RETRIEVAL_TOP_K", 2)
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
    store.vector_store.add_texts(
        ["Other channel first", "Other channel second", "Shared document",
         "Target channel first", "Target channel second"],
        [{"source": "slack", "channel_id": "COTHER"},
         {"source": "slack", "channel_id": "COTHER"},
         {"source": "api"},
         {"source": "slack", "channel_id": "CTARGET"},
         {"source": "slack", "channel_id": "CTARGET"}],
    )
    return store


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


def test_empty_channel_does_not_fall_back_to_global_results(vector):
    assert vector.similarity_search("How do I connect?", channel_id="CEMPTY") == []


@pytest.mark.parametrize("path", ["api", "slack"])
def test_rag_payload_uses_scoped_matches(vector, monkeypatch, path):
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

    assert payload["context"] == (
        "From slack:\nTarget channel first\n\nFrom slack:\nTarget channel second"
    )
    assert payload["sources"] == [
        {"source": "slack", "channel_id": "CTARGET"},
        {"source": "slack", "channel_id": "CTARGET"},
    ]
