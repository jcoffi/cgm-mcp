#!/usr/bin/env python3
"""Tests for the Ollama Cloud provider."""

import pytest

from cgm_mcp.utils import llm_client
from cgm_mcp.utils.config import LLMConfig
from cgm_mcp.utils.llm_client import LLMClient


@pytest.mark.asyncio
async def test_ollama_cloud_client_uses_ollama_generation_contract(monkeypatch):
    requests = []

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"response": "Hello from Ollama Cloud!"}

    class Client:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            pass

        async def post(self, url, *, headers, json):
            requests.append((url, headers, json))
            return Response()

    monkeypatch.setattr(llm_client.httpx, "AsyncClient", Client)
    config = LLMConfig(
        provider="ollama_cloud",
        model="gemma4:cloud",
        api_key="test-key",
        api_base="https://ollama.com",
        temperature=0.1,
        max_tokens=500,
        timeout=60,
    )

    assert await LLMClient(config).generate("Hello") == "Hello from Ollama Cloud!"
    assert requests == [
        (
            "https://ollama.com/api/generate",
            {"Authorization": "Bearer test-key", "Content-Type": "application/json"},
            {
                "model": "gemma4:cloud",
                "prompt": "Hello",
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 500},
            },
        )
    ]
