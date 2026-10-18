"""Client for the single-owner Pi Durable service."""
import time
from uuid import uuid4

import httpx

from app.config import settings


def submit(payload: dict) -> dict:
    with httpx.Client(
        base_url=settings.PI_RUNTIME_URL,
        headers={"Authorization": f"Bearer {settings.PI_RUNTIME_TOKEN}"},
        timeout=30,
    ) as client:
        # An ambiguous network failure can be retried safely with the same ID.
        for attempt in range(3):
            try:
                response = client.post("/jobs", json=payload)
                response.raise_for_status()
                return response.json()
            except httpx.TransportError:
                if attempt == 2:
                    raise
                time.sleep(0.25 * (attempt + 1))


def generate(payload: dict) -> dict:
    job = submit(payload)
    deadline = time.monotonic() + settings.PI_WAIT_TIMEOUT_SECONDS
    with httpx.Client(
        base_url=settings.PI_RUNTIME_URL,
        headers={"Authorization": f"Bearer {settings.PI_RUNTIME_TOKEN}"},
        timeout=30,
    ) as client:
        while time.monotonic() < deadline:
            response = client.get(f"/jobs/{job['id']}")
            response.raise_for_status()
            state = response.json()
            if state["status"] == "done":
                return state["result"]
            if state["status"] in ("failed", "delivery_failed"):
                raise RuntimeError(state["error"] or "Pi job failed")
            time.sleep(0.25)
    raise TimeoutError(f"Pi job {job['id']} is still running; retry with the same request ID")


def request_id() -> str:
    return str(uuid4())
