import json

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
