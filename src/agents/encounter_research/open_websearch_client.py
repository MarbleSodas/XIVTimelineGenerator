"""Client for the open-webSearch MCP server over stdio."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any

from .models import SearchResult, SourceDocument

DEFAULT_PROTOCOL_VERSION = "2024-11-05"


class MCPProtocolError(RuntimeError):
    """Raised when the MCP server returns an invalid response."""


class MCPStdioSession:
    def __init__(
        self,
        command: list[str],
        env: dict[str, str] | None = None,
        cwd: Path | None = None,
    ):
        self.command = command
        self.env = env
        self.cwd = cwd
        self._process: subprocess.Popen[bytes] | None = None
        self._next_id = 1

    def start(self) -> None:
        if self._process is not None:
            return

        self._process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=str(self.cwd) if self.cwd is not None else None,
            env=self.env,
        )
        response = self._request(
            "initialize",
            {
                "protocolVersion": DEFAULT_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "xiv-timeline-generator",
                    "version": "0.1.0",
                },
            },
        )
        protocol_version = response.get("protocolVersion")
        if not protocol_version:
            raise MCPProtocolError("open-webSearch did not return an MCP protocol version")
        self._notify("notifications/initialized", {})

    def close(self) -> None:
        if self._process is None:
            return
        try:
            if self._process.stdin is not None:
                self._process.stdin.close()
        finally:
            self._process.terminate()
            self._process.wait(timeout=5)
            self._process = None

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._request(
            "tools/call",
            {
                "name": name,
                "arguments": arguments,
            },
        )

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        self._send_message(
            {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
            }
        )

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        self._send_message(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            }
        )
        while True:
            message = self._read_message()
            if message.get("id") != request_id:
                continue
            if "error" in message:
                error = message["error"]
                raise MCPProtocolError(
                    f"MCP request failed: {error.get('message', 'Unknown error')}"
                )
            result = message.get("result")
            if not isinstance(result, dict):
                raise MCPProtocolError("MCP server returned a non-object result payload")
            return result

    def _send_message(self, payload: dict[str, Any]) -> None:
        if self._process is None or self._process.stdin is None:
            raise MCPProtocolError("MCP process is not running")
        body = json.dumps(payload).encode("utf-8")
        message = b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n" + body
        self._process.stdin.write(message)
        self._process.stdin.flush()

    def _read_message(self) -> dict[str, Any]:
        if self._process is None or self._process.stdout is None:
            raise MCPProtocolError("MCP process is not running")

        headers: dict[str, str] = {}
        while True:
            line = self._process.stdout.readline()
            if line == b"":
                raise MCPProtocolError("MCP server closed stdout unexpectedly")
            if line in (b"\r\n", b"\n"):
                break
            name, _, value = line.decode("utf-8").partition(":")
            headers[name.strip().lower()] = value.strip()

        content_length = headers.get("content-length")
        if content_length is None:
            raise MCPProtocolError("MCP message missing Content-Length header")

        body = self._process.stdout.read(int(content_length))
        if len(body) != int(content_length):
            raise MCPProtocolError("Incomplete MCP message body")
        return json.loads(body.decode("utf-8"))


class OpenWebSearchClient:
    def __init__(
        self,
        command: str = "npx",
        package: str = "open-websearch@latest",
        engines: list[str] | None = None,
        session: MCPStdioSession | None = None,
    ):
        self.command = command
        self.package = package
        self.engines = engines or ["duckduckgo", "bing", "exa"]
        self._session = session

    def search(
        self,
        query: str,
        limit: int = 5,
        engines: list[str] | None = None,
    ) -> list[SearchResult]:
        payload = self._call_tool(
            "search",
            {
                "query": query,
                "limit": limit,
                "engines": engines or self.engines,
            },
        )
        results = payload.get("results") or []
        return [
            SearchResult(
                title=str(item.get("title") or ""),
                url=str(item.get("url") or ""),
                description=str(item.get("description") or ""),
                source=str(item.get("source") or ""),
                engine=str(item.get("engine") or ""),
            )
            for item in results
            if item.get("url")
        ]

    def fetch_web_content(self, url: str, max_chars: int = 30000) -> SourceDocument:
        payload = self._call_tool(
            "fetchWebContent",
            {
                "url": url,
                "maxChars": max_chars,
            },
        )
        return SourceDocument(
            site=self._site_for_url(url),
            url=str(payload.get("url") or url),
            final_url=str(payload.get("finalUrl") or url),
            title=str(payload.get("title") or ""),
            content=str(payload.get("content") or ""),
            content_type=str(payload.get("contentType") or ""),
            truncated=bool(payload.get("truncated")),
        )

    def close(self) -> None:
        if self._session is not None:
            self._session.close()

    def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        session = self._ensure_session()
        result = session.call_tool(tool_name, arguments)
        if result.get("isError"):
            message = self._extract_text(result)
            raise MCPProtocolError(message or f"{tool_name} failed")

        text = self._extract_text(result)
        if not text:
            raise MCPProtocolError(f"{tool_name} returned no text content")

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as error:
            raise MCPProtocolError(f"{tool_name} returned non-JSON text: {error}") from error

        if not isinstance(payload, dict):
            raise MCPProtocolError(f"{tool_name} returned a non-object JSON payload")
        return payload

    def _ensure_session(self) -> MCPStdioSession:
        if self._session is None:
            self._session = MCPStdioSession(
                command=self._build_command(),
                env=self._build_env(),
            )
        self._session.start()
        return self._session

    def _build_command(self) -> list[str]:
        parts = shlex.split(self.command)
        if not parts:
            raise ValueError("open-webSearch command cannot be empty")
        if parts[0] == "npx":
            return [*parts, self.package]
        return parts

    def _build_env(self) -> dict[str, str]:
        env = dict(os.environ)
        env.setdefault("MODE", "stdio")
        env.setdefault("DEFAULT_SEARCH_ENGINE", self.engines[0] if self.engines else "duckduckgo")
        env["ALLOWED_SEARCH_ENGINES"] = ",".join(self.engines)
        return env

    @staticmethod
    def _extract_text(result: dict[str, Any]) -> str:
        contents = result.get("content") or []
        chunks: list[str] = []
        for item in contents:
            if isinstance(item, dict) and item.get("type") == "text":
                chunks.append(str(item.get("text") or ""))
        return "\n".join(chunk for chunk in chunks if chunk)

    @staticmethod
    def _site_for_url(url: str) -> str:
        lowered = url.lower()
        if "icy-veins.com" in lowered:
            return "icy-veins"
        if "hardcoregamer.com" in lowered:
            return "hardcore-gamer"
        return "web"
