"""Local proof process only: deny Slack and use fixture Chroma embeddings."""
from pathlib import Path
from slack_sdk import WebClient
from slack_bolt.adapter.socket_mode import SocketModeHandler


def blocked(*args, **kwargs):
    raise AssertionError("Live Slack calls and Socket Mode are forbidden in this proof process")


WebClient.auth_test = lambda *args, **kwargs: {
    "ok": True, "bot_id": "BTEST", "user_id": "UTEST", "team_id": "TTEST",
}
WebClient.api_call = blocked
SocketModeHandler.start = blocked

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.telemetry.product.posthog import Posthog
from langchain_community.vectorstores import Chroma
from langchain_core.embeddings import Embeddings
from app.vector_store import vector_store

Posthog.capture = lambda *args, **kwargs: None
proof_dir = Path(__file__).resolve().parent


class FixedEmbeddings(Embeddings):
    def embed_documents(self, texts):
        # A marker file injects a recoverable provider failure for the transcript.
        if (proof_dir / "fail-embedding").exists():
            raise RuntimeError("Fixture embedding outage")
        return [[float(len("Reset VPN via IT portal.") - len(text) + 1), 1.0] for text in texts]

    def embed_query(self, text):
        return [0.0, 1.0]


vector_store.vector_store = Chroma(
    client=chromadb.PersistentClient(
        path=str(proof_dir / "chroma"), settings=ChromaSettings(anonymized_telemetry=False),
    ),
    collection_name="document-delete-proof", embedding_function=FixedEmbeddings(),
)
vector_store._initialized = True

# Allow a repeatable deletion outage without changing the application.
original_delete = vector_store.vector_store.delete

def fixture_delete(*args, **kwargs):
    if (proof_dir / "fail-delete").exists():
        raise RuntimeError("Fixture Chroma deletion outage")
    return original_delete(*args, **kwargs)

vector_store.vector_store.delete = fixture_delete
