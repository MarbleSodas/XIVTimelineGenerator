import json

import pytest
import requests

import fflogs.env as env_module
from agents.encounter_research.minimax_client import MiniMaxClient
from agents.encounter_research.open_websearch_client import OpenWebSearchClient


class FakeMcpSession:
    def __init__(self, responses):
        self.responses = responses
        self.started = False
        self.closed = False

    def start(self):
        self.started = True

    def close(self):
        self.closed = True

    def call_tool(self, name, arguments):
        return self.responses[name]


def test_open_websearch_search_parses_canned_mcp_response():
    session = FakeMcpSession(
        {
            "search": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "query": "M11S",
                                "results": [
                                    {
                                        "title": "M11S guide",
                                        "url": "https://www.icy-veins.com/ffxiv/m11s-guide",
                                        "description": "Guide",
                                        "source": "Icy Veins",
                                        "engine": "duckduckgo",
                                    }
                                ],
                            }
                        ),
                    }
                ]
            }
        }
    )
    client = OpenWebSearchClient(session=session)

    results = client.search("M11S", limit=1)

    assert session.started is True
    assert len(results) == 1
    assert results[0].title == "M11S guide"
    assert results[0].engine == "duckduckgo"


def test_open_websearch_fetch_content_parses_canned_payload():
    session = FakeMcpSession(
        {
            "fetchWebContent": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "url": "https://www.hardcoregamer.com/m11s",
                                "finalUrl": "https://www.hardcoregamer.com/m11s",
                                "title": "Hardcore Gamer Guide",
                                "contentType": "text/html",
                                "truncated": False,
                                "content": "Boss guide body",
                            }
                        ),
                    }
                ]
            }
        }
    )
    client = OpenWebSearchClient(session=session)

    document = client.fetch_web_content("https://www.hardcoregamer.com/m11s")

    assert document.site == "hardcore-gamer"
    assert document.title == "Hardcore Gamer Guide"
    assert document.content == "Boss guide body"


def test_minimax_client_strips_markdown_fences_and_parses_json(monkeypatch):
    client = MiniMaxClient(api_key="test-key")
    responses = iter(
        [
            "```json\n{\"actions\": [{\"action_name\": \"Crown of Arcadia\"}]}\n```",
        ]
    )
    monkeypatch.setattr(client, "_request_content", lambda **_: next(responses))

    payload = client.chat_json("system", "user")

    assert payload["actions"][0]["action_name"] == "Crown of Arcadia"


def test_minimax_client_retries_after_malformed_json(monkeypatch):
    client = MiniMaxClient(api_key="test-key")
    responses = iter(
        [
            "not json",
            "{\"status\": \"matched\", \"confidence\": 0.9}",
        ]
    )
    monkeypatch.setattr(client, "_request_content", lambda **_: next(responses))

    payload = client.chat_json("system", "user", max_retries=2)

    assert payload["status"] == "matched"
    assert payload["confidence"] == 0.9


def test_minimax_client_retries_after_request_timeout(monkeypatch):
    client = MiniMaxClient(api_key="test-key")
    responses = iter(
        [
            requests.Timeout("read timed out"),
            "{\"selected_slot_ids\": [\"slot-0001\"]}",
        ]
    )

    def fake_request_content(**kwargs):
        response = next(responses)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(client, "_request_content", fake_request_content)

    payload = client.chat_json("system", "user", max_retries=2)

    assert payload["selected_slot_ids"] == ["slot-0001"]


def test_minimax_client_prefers_minimax_env_configuration(monkeypatch):
    monkeypatch.setenv("XIV_TIMELINE_SKIP_DOTENV", "1")
    monkeypatch.setenv("MINIMAX_API_KEY", "minimax-key")
    monkeypatch.setenv("MINIMAX_BASE_URL", "https://minimax.example/v1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setattr(env_module, "_HAS_LOADED_PROJECT_ENV", False)

    client = MiniMaxClient()

    assert client.api_key == "minimax-key"
    assert client.base_url == "https://minimax.example/v1"


def test_minimax_client_loads_credentials_from_dotenv(monkeypatch, tmp_path):
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "MINIMAX_API_KEY=dotenv-key\nMINIMAX_BASE_URL=https://dotenv.example/v1\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.delenv("MINIMAX_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("XIV_TIMELINE_SKIP_DOTENV", raising=False)
    monkeypatch.setenv("XIV_TIMELINE_DOTENV_PATH", str(dotenv_path))
    monkeypatch.setattr(env_module, "_HAS_LOADED_PROJECT_ENV", False)

    client = MiniMaxClient()

    assert client.api_key == "dotenv-key"
    assert client.base_url == "https://dotenv.example/v1"


def test_minimax_client_errors_when_no_supported_api_key_is_configured(monkeypatch):
    monkeypatch.setenv("XIV_TIMELINE_SKIP_DOTENV", "1")
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(env_module, "_HAS_LOADED_PROJECT_ENV", False)

    client = MiniMaxClient(api_key=None)

    with pytest.raises(RuntimeError, match="MINIMAX_API_KEY or OPENAI_API_KEY"):
        client.chat_json("system", "user", max_retries=0)
