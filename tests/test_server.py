import pytest

from cgm_mcp import server
from cgm_mcp.utils.config import Config, LLMConfig


@pytest.mark.asyncio
async def test_main_uses_supplied_config(monkeypatch):
    received = []

    class FakeServer:
        def __init__(self, config):
            received.append(config)

        async def run(self):
            pass

    monkeypatch.setattr(server, "CGMServer", FakeServer)
    config = Config(llm_config=LLMConfig(provider="mock", model="configured-model"))

    await server.main(config)

    assert received == [config]
