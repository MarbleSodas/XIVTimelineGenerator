"""Guide scraper for FFXIV boss guides."""

import re
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup


class GuideScraper:
    """Scraper for FFXIV boss guides from various websites."""

    def __init__(self):
        """Initialize the scraper."""
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "XIVTimelineGenerator/1.0 (FFXIV Timeline Tool)",
            },
        )

    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()

    def _normalize_boss_name(self, boss_name: str) -> str:
        """Normalize boss name for URL generation."""
        # Remove special characters and convert to lowercase
        name = re.sub(r'[^a-zA-Z0-9\s-]', '', boss_name)
        name = name.lower().strip()
        name = re.sub(r'\s+', '-', name)
        return name

    async def fetch_icyveins_guide(self, boss_name: str) -> dict[str, Any]:
        """
        Fetch guide content from Icy Veins.

        Args:
            boss_name: Name of the boss

        Returns:
            Dictionary containing guide content
        """
        normalized_name = self._normalize_boss_name(boss_name)
        url = f"https://www.icy-veins.com/ffxiv/{normalized_name}-guide"

        try:
            response = await self.http_client.get(url)
            if response.status_code != 200:
                return {"success": False, "error": f"HTTP {response.status_code}", "url": url}

            soup = BeautifulSoup(response.text, "lxml")

            # Extract guide content
            content = self._extract_icyveins_content(soup, boss_name)

            return {
                "success": True,
                "source": "icy-veins",
                "url": url,
                "title": soup.title.string if soup.title else boss_name,
                "content": content,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "url": url}

    def _extract_icyveins_content(self, soup: BeautifulSoup, boss_name: str) -> dict[str, Any]:
        """Extract structured content from Icy Veins guide."""
        result = {
            "overview": "",
            "phases": [],
            "mechanics": [],
            "variations": [],
            "tips": [],
        }

        # Find main content area
        main_content = soup.find("article") or soup.find("main") or soup.find("div", class_=re.compile(r"content|guide"))

        if not main_content:
            return result

        # Extract overview (first paragraph)
        paragraphs = main_content.find_all("p")
        if paragraphs:
            result["overview"] = paragraphs[0].get_text(strip=True)

        # Extract sections for mechanics
        headings = main_content.find_all(["h2", "h3"])
        current_section = {"title": "", "content": ""}

        for heading in headings:
            heading_text = heading.get_text(strip=True).lower()

            # Check if it's a phase section
            if "phase" in heading_text:
                if current_section["title"]:
                    result["mechanics"].append(current_section)
                current_section = {"title": heading.get_text(strip=True), "content": "", "type": "phase"}
            # Check for variations
            elif any(kw in heading_text for kw in ["variation", "skip", "alternative", "strategy"]):
                if current_section["title"]:
                    result["mechanics"].append(current_section)
                current_section = {"title": heading.get_text(strip=True), "content": "", "type": "variation"}
            # Regular mechanic section
            else:
                if current_section["title"]:
                    result["mechanics"].append(current_section)
                current_section = {"title": heading.get_text(strip=True), "content": "", "type": "mechanic"}

            # Get content under this heading
            next_elem = heading.find_next_sibling()
            section_content = []
            while next_elem and next_elem.name and next_elem.name not in ["h2", "h3", "h4"]:
                if next_elem.name in ["p", "ul", "ol"]:
                    section_content.append(next_elem.get_text(strip=True))
                next_elem = next_elem.find_next_sibling()
            current_section["content"] = " ".join(section_content)

        if current_section["title"]:
            result["mechanics"].append(current_section)

        # Extract variation notes
        for mechanic in result["mechanics"]:
            if mechanic.get("type") == "variation":
                result["variations"].append({
                    "title": mechanic["title"],
                    "description": mechanic["content"],
                })

        return result

    async def fetch_hardcoregamer_guide(self, boss_name: str) -> dict[str, Any]:
        """
        Fetch guide content from Hardcore Gamer.

        Args:
            boss_name: Name of the boss

        Returns:
            Dictionary containing guide content
        """
        normalized_name = self._normalize_boss_name(boss_name)
        url = f"https://hardcoregamer.com/?s={normalized_name}+ffxiv"

        try:
            # First search for the guide
            search_response = await self.http_client.get(url)
            if search_response.status_code != 200:
                return {"success": False, "error": f"HTTP {search_response.status_code}", "url": url}

            # Try to find guide link
            soup = BeautifulSoup(search_response.text, "lxml")
            guide_link = soup.find("a", href=re.compile(r"ffxiv.*guide|ffxiv.*boss"))

            if guide_link and guide_link.get("href"):
                guide_url = guide_link["href"]
                guide_response = await self.http_client.get(guide_url)
                if guide_response.status_code == 200:
                    guide_soup = BeautifulSoup(guide_response.text, "lxml")
                    content = self._extract_hardcoregamer_content(guide_soup, boss_name)
                    return {
                        "success": True,
                        "source": "hardcore-gamer",
                        "url": guide_url,
                        "title": guide_soup.title.string if guide_soup.title else boss_name,
                        "content": content,
                    }

            return {
                "success": False,
                "error": "Guide not found",
                "url": url,
                "content": {},
            }
        except Exception as e:
            return {"success": False, "error": str(e), "url": url}

    def _extract_hardcoregamer_content(self, soup: BeautifulSoup, boss_name: str) -> dict[str, Any]:
        """Extract structured content from Hardcore Gamer guide."""
        result = {
            "overview": "",
            "phases": [],
            "mechanics": [],
            "tips": [],
        }

        # Find main content
        main_content = soup.find("article") or soup.find("main") or soup.find("div", class_=re.compile(r"content|post"))

        if not main_content:
            return result

        # Extract paragraphs
        paragraphs = main_content.find_all("p")
        if paragraphs:
            result["overview"] = paragraphs[0].get_text(strip=True)

        return result

    async def fetch_all_guides(self, boss_name: str) -> dict[str, Any]:
        """
        Fetch guides from all supported sources.

        Args:
            boss_name: Name of the boss

        Returns:
            Dictionary containing guides from all sources
        """
        results = {
            "boss_name": boss_name,
            "guides": {},
        }

        # Fetch from Icy Veins
        icyveins = await self.fetch_icyveins_guide(boss_name)
        results["guides"]["icy-veins"] = icyveins

        # Fetch from Hardcore Gamer
        hardcore = await self.fetch_hardcoregamer_guide(boss_name)
        results["guides"]["hardcore-gamer"] = hardcore

        return results
