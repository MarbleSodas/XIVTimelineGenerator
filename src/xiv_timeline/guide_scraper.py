"""LLM-driven guide agent for FFXIV boss guides.

Instead of hard-coding URL patterns and manually parsing HTML, this module
exposes a ``GuideAgent`` that uses the LLM + a ``fetch_url`` tool to
discover and extract guide content from strategy sites.
"""

import logging
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

from xiv_timeline.llm import get_llm

logger = logging.getLogger("xiv_timeline.guide_agent")

# ---------------------------------------------------------------------------
# Lightweight hints — just enough to seed the agent, not an exhaustive map
# ---------------------------------------------------------------------------

BOSS_GUIDE_HINTS: dict[str, list[str]] = {
    # Dawntrail
    "black-cat": ["aac-light-heavyweight-m1-savage-raid-guide"],
    "honey-b-lovely": ["aac-light-heavyweight-m2-savage-raid-guide"],
    "brute-bomber": ["aac-light-heavyweight-m3-savage-raid-guide"],
    "wicked-thunder": ["aac-light-heavyweight-m4-savage-raid-guide"],
    "r12s": ["the-twelfth-circle-savage-raid-guide"],
    "r11s": ["the-eleventh-circle-savage-raid-guide"],
    "r10s": ["the-tenth-circle-savage-raid-guide"],
    "r9s": ["the-ninth-circle-savage-raid-guide"],
    "r8s": ["the-eighth-circle-savage-raid-guide"],
    "r7s": ["the-seventh-circle-savage-raid-guide"],
    "r6s": ["the-sixth-circle-savage-raid-guide"],
    "r5s": ["the-fifth-circle-savage-raid-guide"],
    "r4s": ["the-fourth-circle-savage-raid-guide"],
    "r3s": ["the-third-circle-savage-raid-guide"],
    "r2s": ["the-second-circle-savage-raid-guide"],
    "r1s": ["the-first-circle-savage-raid-guide"],
    # Endwalker
    "p12s": [
        "the-twelfth-circle-savage-part-one-raid-guide",
        "the-twelfth-circle-savage-part-two-raid-guide",
    ],
    "p11s": ["the-eleventh-circle-savage-raid-guide"],
    "p10s": ["the-tenth-circle-savage-raid-guide"],
    "p9s": ["the-ninth-circle-savage-raid-guide"],
    "p8s": ["the-eighth-circle-savage-raid-guide"],
    "p7s": ["the-seventh-circle-savage-raid-guide"],
    "p6s": ["the-sixth-circle-savage-raid-guide"],
    "p5s": ["the-fifth-circle-savage-raid-guide"],
    "p4s": ["the-fourth-circle-savage-raid-guide"],
    "p3s": ["the-third-circle-savage-raid-guide"],
    "p2s": ["the-second-circle-savage-raid-guide"],
    "p1s": ["the-first-circle-savage-raid-guide"],
    # Ultimates
    "the_omega_protocol": ["the-omega-protocol-raid-guide"],
    "dragonsongs_reprise_ultimate": ["dragonsongs-reprise-ultimate-raid-guide"],
    "tea": ["the-epic-of-alexander-ultimate-raid-guide"],
}

# ---------------------------------------------------------------------------
# URL fetcher (used as a tool by the agent)
# ---------------------------------------------------------------------------


async def fetch_url_text(url: str, *, timeout: float = 20.0) -> str:
    """Fetch *url*, strip HTML boilerplate, return readable text (≤ 6000 chars)."""
    async with httpx.AsyncClient(
        timeout=timeout,
        headers={"User-Agent": "XIVTimelineGenerator/2.0"},
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")

    # Remove noise
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    # Collapse blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:6000]


# ---------------------------------------------------------------------------
# Guide agent
# ---------------------------------------------------------------------------


class GuideAgent:
    """Uses an LLM to fetch and interpret FFXIV boss guides.

    Workflow:
    1. Build a list of candidate URLs from ``BOSS_GUIDE_HINTS`` (or fall
       back to a slug derived from the boss name).
    2. Fetch the first URL that returns content.
    3. Ask the LLM to extract structured phases, mechanics, and tips from
       the raw page text.
    """

    _EXTRACTION_SYSTEM = (
        "You are an expert FFXIV guide reader. Given the raw text of a boss "
        "strategy guide page, extract structured data in the following JSON format. "
        "Return ONLY valid JSON, no markdown fences or extra text.\n\n"
        '{"overview": "<1-2 sentence summary>", '
        '"phases": [{"title": "<phase name>", "content": "<mechanics description>", '
        '"tips": ["<tip1>", ...]}], '
        '"mechanics": [{"name": "<ability>", "description": "<what it does>"}]}'
    )

    def __init__(self):
        self._http = httpx.AsyncClient(
            timeout=25.0,
            headers={"User-Agent": "XIVTimelineGenerator/2.0"},
        )

    async def close(self):
        await self._http.aclose()

    async def fetch_guide(self, boss_name: str) -> dict[str, Any]:
        """Fetch and extract a guide for *boss_name*.

        Returns a dict with keys: success, source, url, content (structured).
        On failure, returns success=False with an error message.
        """
        urls = self._candidate_urls(boss_name)
        page_text: str | None = None
        used_url: str | None = None

        for url in urls:
            try:
                page_text = await fetch_url_text(url)
                if len(page_text) > 200:  # sanity check
                    used_url = url
                    break
            except Exception as exc:
                logger.debug("Failed to fetch %s: %s", url, exc)
                continue

        if not page_text or not used_url:
            return {
                "success": False,
                "error": f"No guide found for '{boss_name}'",
                "url": urls[0] if urls else None,
            }

        # Ask LLM to extract structured data
        content = await self._extract_content(page_text or "", boss_name)

        source = "icy-veins"
        if used_url and "hardcoregamer" in used_url:
            source = "hardcoregamer"

        return {
            "success": True,
            "source": source,
            "url": used_url,
            "content": content,
        }

    async def fetch_all_guides(self, boss_name: str) -> dict[str, Any]:
        """Fetch guides and package them in the expected format."""
        guide = await self.fetch_guide(boss_name)
        source = guide.get("source", "unknown")
        
        guides_dict = {}
        if guide.get("success"):
            guides_dict[source] = guide
            
        return {
            "boss_name": boss_name,
            "guides": guides_dict,
            "merged_ability_map": guide.get("content", {}).get("mechanics", []),
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _candidate_urls(self, boss_name: str) -> list[str]:
        """Use DDGS web search to find relevant guide URLs for this boss."""
        try:
            from ddgs import DDGS
        except ImportError:
            logger.warning("ddgs package not found, please install it.")
            return []

        query = f"ffxiv {boss_name} savage guide icy-veins hardcoregamer"
        urls = []
        
        try:
            results = DDGS().text(query, max_results=10)
            for res in results:
                href = res.get("href", "")
                if "icy-veins.com" in href or "hardcoregamer.com" in href:
                    urls.append(href)
        except Exception as exc:
            logger.error("DDGS web search failed: %s", exc)

        return urls

    async def _extract_content(
        self, page_text: str, boss_name: str
    ) -> dict[str, Any]:
        """Use the LLM to extract structured guide data from raw page text."""
        llm = get_llm()

        from langchain_core.messages import HumanMessage, SystemMessage

        prompt = (
            f"Extract the boss guide information for '{boss_name}' from "
            f"the following page text:\n\n{page_text[:5000]}"
        )

        try:
            response = await llm.ainvoke([
                SystemMessage(content=self._EXTRACTION_SYSTEM),
                HumanMessage(content=prompt),
            ])

            raw = str(response.content)

            # Strip reasoning tags if present
            if "</think>" in raw:
                raw = raw.split("</think>")[-1].strip()

            # Strip markdown fences
            raw = re.sub(r"^```json\s*", "", raw.strip())
            raw = re.sub(r"\s*```$", "", raw.strip())

            import json
            return json.loads(raw)
        except Exception as exc:
            logger.warning("LLM extraction failed for '%s': %s", boss_name, exc)
            return {
                "overview": "",
                "phases": [],
                "mechanics": [],
            }
