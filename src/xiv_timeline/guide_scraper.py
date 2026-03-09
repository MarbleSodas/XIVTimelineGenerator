"""Guide scraper for FFXIV boss guides with ability mapping."""

import re
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup


# Boss name to Icy Veins URL pattern mapping
# Keys match cactbot file names (without .txt/.ts)
BOSS_URL_PATTERNS = {
    # ============ Dawntrail (07-dt) ============
    # Raids: r1n-r12n, r1s-r12s
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
    
    # Dawntrail Trials
    "zoraal-ja": ["zoraal-ja-raid-guide"],
    "valigarmanda": ["valigarmanda-raid-guide"],
    "arkveld": ["arkveld-raid-guide"],
    "doomtrain": ["doomtrain-raid-guide"],
    
    # ============ Endwalker (06-ew) ============
    # Raids: p1n-p12n, p1s-p12s
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
    
    # Endwalker Trials
    "zodiark": ["zodiark-raid-guide"],
    "endsinger": ["endsinger-raid-guide"],
    "barbariccia": ["barbariccia-raid-guide"],
    "barbariccia-ex": ["barbariccia-extreme-raid-guide"],
    
    # Endwalker Ultimates
    "the_omega_protocol": ["the-omega-protocol-raid-guide"],  # TOP
    "dragonsongs_reprise_ultimate": ["dragonsongs-reprise-ultimate-raid-guide"],  # DSR
    
    # ============ Shadowbringers (05-shb) ============
    # Raids: e1n-e12n, e1s-e12s
    "e12s": ["the-twelfth-circle-raid-guide"],
    "e11s": ["the-eleventh-circle-raid-guide"],
    "e10s": ["the-tenth-circle-raid-guide"],
    "e9s": ["the-ninth-circle-raid-guide"],
    "e8s": ["the-eighth-circle-raid-guide"],
    "e7s": ["the-seventh-circle-raid-guide"],
    "e6s": ["the-sixth-circle-raid-guide"],
    "e5s": ["the-fifth-circle-raid-guide"],
    "e4s": ["the-fourth-circle-raid-guide"],
    "e3s": ["the-third-circle-raid-guide"],
    "e2s": ["the-second-circle-raid-guide"],
    "e1s": ["the-first-circle-raid-guide"],
    
    # Shadowbringers Trials
    "diamond_weapon": ["diamond-weapon-raid-guide"],
    "emerald_weapon": ["emerald-weapon-raid-guide"],
    "ruby_weapon": ["ruby-weapon-raid-guide"],
    "hades": ["hades-raid-guide"],
    "innocence": ["innocence-raid-guide"],
    "titania": ["titania-raid-guide"],
    
    # Shadowbringers Ultimates
    "tea": ["the-epic-of-alexander-ultimate-raid-guide"],  # TEA
    "uco_ultimate": ["the-unending-coil-of-bahamut-ultimate-raid-guide"],  # UCOB
    
    # ============ Stormblood (04-sb) ============
    # Raids: o1n-o12n, o1s-o12s
    "o12s": ["the-twelfth-circle-raid-guide"],
    "o11s": ["the-eleventh-circle-raid-guide"],
    "o10s": ["the-tenth-circle-raid-guide"],
    "o9s": ["the-ninth-circle-raid-guide"],
    "o8s": ["the-eighth-circle-raid-guide"],
    "o7s": ["the-seventh-circle-raid-guide"],
    "o6s": ["the-sixth-circle-raid-guide"],
    "o5s": ["the-fifth-circle-raid-guide"],
    "o4s": ["the-fourth-circle-raid-guide"],
    "o3s": ["the-third-circle-raid-guide"],
    "o2s": ["the-second-circle-raid-guide"],
    "o1s": ["the-first-circle-raid-guide"],
    
    # Stormblood Trials
    "susano": ["susano-raid-guide"],
    "shinryu": ["shinryu-raid-guide"],
    "byakko": ["byakko-raid-guide"],
    "seiryu": ["seiryu-raid-guide"],
    "lakshmi": ["lakshmi-raid-guide"],
    "tsukuyomi": ["tsukuyomi-raid-guide"],
    "rathalos": ["rathalos-raid-guide"],
    
    # Stormblood Ultimates
    "ultimate": ["the-weapons-refrain-raid-guide"],  # Ultima
    
    # ============ Heavensward (03-hw) ============
    # Raids: a1n-a12n, a1s-a12s (savage only for most)
    "a12s": ["the-twelfth-circle-raid-guide"],
    "a11s": ["the-eleventh-circle-raid-guide"],
    "a10s": ["the-tenth-circle-raid-guide"],
    "a9s": ["the-ninth-circle-raid-guide"],
    "a8s": ["the-eighth-circle-raid-guide"],
    "a7s": ["the-seventh-circle-raid-guide"],
    "a6s": ["the-sixth-circle-raid-guide"],
    "a5s": ["the-fifth-circle-raid-guide"],
    "a4s": ["the-fourth-circle-raid-guide"],
    "a3s": ["the-third-circle-raid-guide"],
    "a2s": ["the-second-circle-raid-guide"],
    "a1s": ["the-first-circle-raid-guide"],
    
    # Heavensward Trials
    "thordan": ["thordan-raid-guide"],
    "sophia": ["sophia-raid-guide"],
    "sephirot": ["sephirot-raid-guide"],
    "zurvan": ["zurvan-raid-guide"],
    
    # ============ A Realm Reborn (02-arr) ============
    # Raids: t1, t2, t4-t13
    "t13": ["the-final-coil-of-bahamut-turn-4-raid-guide"],
    "t12": ["the-final-coil-of-bahamut-turn-3-raid-guide"],
    "t11": ["the-final-coil-of-bahamut-turn-2-raid-guide"],
    "t10": ["the-final-coil-of-bahamut-turn-1-raid-guide"],
    "t9": ["the-coil-of-bahamut-turn-9-raid-guide"],
    "t8": ["the-coil-of-bahamut-turn-8-raid-guide"],
    "t7": ["the-coil-of-bahamut-turn-7-raid-guide"],
    "t6": ["the-coil-of-bahamut-turn-6-raid-guide"],
    "t5": ["the-coil-of-bahamut-turn-5-raid-guide"],
    "t4": ["the-coil-of-bahamut-turn-4-raid-guide"],
    "t2": ["the-coil-of-bahamut-turn-2-raid-guide"],
    "t1": ["the-coil-of-bahamut-turn-1-raid-guide"],
    
    # ARR Trials
    "ultima-un": ["the-ultimate-weapon-raid-guide"],
    "levi-un": ["leviathan-raid-guide"],
    "titan-un": ["titan-raid-guide"],
    "ifrit-un": ["ifrit-raid-guide"],
    "garuda-un": ["garuda-raid-guide"],
}

import re
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup


# Boss name to Icy Veins URL pattern mapping
BOSS_URL_PATTERNS = {
    # Endwalker - Anabaseios (P9S-P12S)
    "p12s": [
        "the-twelfth-circle-savage-part-one-raid-guide",
        "the-twelfth-circle-savage-part-two-raid-guide",
    ],
    "p11s": [
        "the-eleventh-circle-savage-raid-guide",
    ],
    "p10s": [
        "the-tenth-circle-savage-raid-guide",
    ],
    "p9s": [
        "the-ninth-circle-savage-raid-guide",
    ],
    # Endwalker - Abyssos (P5S-P8S)
    "p8s": [
        "the-eighth-circle-savage-raid-guide",
    ],
    "p7s": [
        "the-seventh-circle-savage-raid-guide",
    ],
    "p6s": [
        "the-sixth-circle-savage-raid-guide",
    ],
    "p5s": [
        "the-fifth-circle-savage-raid-guide",
    ],
    # Endwalker - Asphodelos (P1S-P4S)
    "p4s": [
        "the-fourth-circle-savage-raid-guide",
    ],
    "p3s": [
        "the-third-circle-savage-raid-guide",
    ],
    "p2s": [
        "the-second-circle-savage-raid-guide",
    ],
    "p1s": [
        "the-first-circle-savage-raid-guide",
    ],
    # Shadowbringers - Eden (E1S-E12S)
    "e12s": [
        "the-twelfth-circle-raid-guide",
    ],
    "e11s": [
        "the-eleventh-circle-raid-guide",
    ],
    "e10s": [
        "the-tenth-circle-raid-guide",
    ],
    "e9s": [
        "the-ninth-circle-raid-guide",
    ],
    "e8s": [
        "the-eighth-circle-raid-guide",
    ],
    "e7s": [
        "the-seventh-circle-raid-guide",
    ],
    "e6s": [
        "the-sixth-circle-raid-guide",
    ],
    "e5s": [
        "the-fifth-circle-raid-guide",
    ],
    "e4s": [
        "the-fourth-circle-raid-guide",
    ],
    "e3s": [
        "the-third-circle-raid-guide",
    ],
    "e2s": [
        "the-second-circle-raid-guide",
    ],
    "e1s": [
        "the-first-circle-raid-guide",
    ],
    # Trials
    "zodiark": [
        "zodiark-raid-guide",
    ],
    "endsinger": [
        "endsinger-raid-guide",
    ],
    "barbarricia": [
        "barbarricia-raid-guide",
    ],
    # Ultimates
    "tea": [
        "the-weapons-refrain-ultimate-raid-guide",
    ],
    "top": [
        "the-path-of-ultimatum-raid-guide",
    ],
    "ubc": [
        "the-unending-coil-of-bahamut-ultimate-raid-guide",
    ],
}


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
        name = re.sub(r'[^a-zA-Z0-9\s-]', '', boss_name)
        name = name.lower().strip()
        name = re.sub(r'\s+', '-', name)
        return name

    def _get_icyveins_urls(self, boss_name: str) -> list[str]:
        """Get Icy Veins URL patterns for a boss."""
        normalized = self._normalize_boss_name(boss_name)
        
        if normalized in BOSS_URL_PATTERNS:
            return BOSS_URL_PATTERNS[normalized]
        
        return [f"{normalized}-raid-guide"]

    async def fetch_icyveins_guide(self, boss_name: str) -> dict[str, Any]:
        """Fetch guide content from Icy Veins."""
        url_patterns = self._get_icyveins_urls(boss_name)
        
        for pattern in url_patterns:
            url = f"https://www.icy-veins.com/ffxiv/{pattern}"
            
            try:
                response = await self.http_client.get(url)
                if response.status_code != 200:
                    continue
                    
                soup = BeautifulSoup(response.text, "lxml")
                content = self._extract_icyveins_content(soup, boss_name)
                
                return {
                    "success": True,
                    "source": "icy-veins",
                    "url": url,
                    "title": soup.title.string if soup.title else boss_name,
                    "content": content,
                }
            except Exception:
                continue
        
        return {
            "success": False,
            "error": "No matching guide found",
            "url": f"https://www.icy-veins.com/ffxiv/{boss_name}",
        }

    def _extract_icyveins_content(self, soup: BeautifulSoup, boss_name: str) -> dict[str, Any]:
        """Extract structured content from Icy Veins guide."""
        result = {
            "overview": "",
            "phases": [],
            "mechanics": [],
            "ability_map": {},
            "variations": [],
            "tips": [],
            "table_of_contents": [],
        }

        # Icy Veins content is in the body
        main_content = soup.body
        if not main_content:
            return result

        # Extract overview (first paragraph)
        paragraphs = main_content.find_all("p")
        if paragraphs:
            result["overview"] = paragraphs[0].get_text(strip=True)

        # Extract table of contents
        toc = main_content.find("ul", class_=re.compile(r"toc|contents"))
        if toc:
            for li in toc.find_all("li"):
                link = li.find("a")
                if link:
                    result["table_of_contents"].append({
                        "title": link.get_text(strip=True),
                        "href": link.get("href", ""),
                    })

        # Extract sections - Icy Veins uses div.heading_container for headings
        heading_containers = main_content.find_all("div", class_="heading_container")
        current_section = {"title": "", "content": "", "type": "general", "abilities": []}

        for container in heading_containers:
            # Get the heading (h2 or h3)
            heading = container.find(["h2", "h3"])
            if not heading:
                continue
                
            heading_text = heading.get_text(strip=True)
            heading_lower = heading_text.lower()
            
            # Determine section type
            section_type = "general"
            if "phase" in heading_lower:
                section_type = "phase"
            elif any(kw in heading_lower for kw in ["variation", "skip", "alternative", "strategy"]):
                section_type = "variation"
            elif any(kw in heading_lower for kw in ["mechanic", "ability", "attack"]):
                section_type = "mechanic"
            
            # Save previous section
            if current_section["title"]:
                if section_type == "mechanic" or current_section["type"] == "mechanic":
                    result["mechanics"].append(current_section)
                else:
                    result["phases"].append(current_section)
            
            # Get content after this heading - look for sibling elements
            section_text = ""
            next_elem = container.find_next_sibling()
            
            while next_elem and hasattr(next_elem, 'name') and next_elem.name:
                # Stop at next heading container
                if next_elem.name == 'div' and 'heading_container' in next_elem.get('class', []):
                    break
                # Stop at next heading
                if next_elem.name in ['h2', 'h3', 'h4']:
                    break
                
                if next_elem.name in ['p', 'ul', 'ol']:
                    text = next_elem.get_text(strip=True)
                    if text:
                        section_text += text + "\n"
                
                next_elem = next_elem.find_next_sibling()
            
            # Start new section
            current_section = {
                "title": heading_text,
                "content": section_text,
                "type": section_type,
                "abilities": [],
            }
            
            # Extract ability descriptions
            section_abilities = self._extract_abilities_from_text(section_text)
            current_section["abilities"] = section_abilities
            
            for ability in section_abilities:
                if ability["name"] not in result["ability_map"]:
                    result["ability_map"][ability["name"]] = ability["description"]

        # Add final section
        if current_section["title"]:
            if current_section["type"] == "mechanic":
                result["mechanics"].append(current_section)
            else:
                result["phases"].append(current_section)

        return result
        """Extract structured content from Icy Veins guide."""
        result = {
            "overview": "",
            "phases": [],
            "mechanics": [],
            "ability_map": {},
            "variations": [],
            "tips": [],
            "table_of_contents": [],
        }

        # Icy Veins content is in the body
        main_content = soup.body
        if not main_content:
            return result

        # Extract overview (first paragraph)
        paragraphs = main_content.find_all("p")
        if paragraphs:
            result["overview"] = paragraphs[0].get_text(strip=True)

        # Extract table of contents
        toc = main_content.find("ul", class_=re.compile(r"toc|contents"))
        if toc:
            for li in toc.find_all("li"):
                link = li.find("a")
                if link:
                    result["table_of_contents"].append({
                        "title": link.get_text(strip=True),
                        "href": link.get("href", ""),
                    })

        # Extract sections by iterating through headings
        headings = main_content.find_all(["h2", "h3"])
        current_section = {"title": "", "content": "", "type": "general", "abilities": []}

        for heading in headings:
            heading_text = heading.get_text(strip=True).lower()
            
            # Determine section type
            section_type = "general"
            if "phase" in heading_text:
                section_type = "phase"
            elif any(kw in heading_text for kw in ["variation", "skip", "alternative", "strategy"]):
                section_type = "variation"
            elif any(kw in heading_text for kw in ["mechanic", "ability", "attack"]):
                section_type = "mechanic"
            
            # Save previous section
            if current_section["title"]:
                if section_type == "mechanic" or current_section["type"] == "mechanic":
                    result["mechanics"].append(current_section)
                else:
                    result["phases"].append(current_section)
            
            # Start new section
            current_section = {
                "title": heading.get_text(strip=True),
                "content": "",
                "type": section_type,
                "abilities": [],
            }

            # Get content under this heading by finding siblings in parent
            section_content = []
            parent = heading.parent
            if parent:
                found_heading = False
                for sibling in parent.children:
                    if hasattr(sibling, 'name') and sibling.name:
                        if sibling == heading:
                            found_heading = True
                            continue
                        if found_heading and sibling.name in ["h2", "h3", "h4"]:
                            break
                        if sibling.name in ["p", "ul", "ol"]:
                            text = sibling.get_text(strip=True)
                            if text:
                                section_content.append(text)
            
            current_section["content"] = " ".join(section_content)
            
            # Extract ability descriptions - look for "AbilityName: Description" pattern
            section_abilities = self._extract_abilities_from_text(" ".join(section_content))
            current_section["abilities"] = section_abilities
            
            # Also update ability_map
            for ability in section_abilities:
                if ability["name"] not in result["ability_map"]:
                    result["ability_map"][ability["name"]] = ability["description"]

        # Add final section
        if current_section["title"]:
            if current_section["type"] == "mechanic":
                result["mechanics"].append(current_section)
            else:
                result["phases"].append(current_section)

        return result

    def _extract_abilities_from_text(self, text: str) -> list[dict[str, str]]:
        """Extract ability names and descriptions from text using common patterns."""
        abilities = []
        
        # Pattern: "AbilityName: Description" or "AbilityName - Description"
        # Also handle bullet points like "- AbilityName: Description"
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Remove leading bullet points
            line = re.sub(r'^[\-\*\•]+\s*', '', line)
            
            # Look for colon or dash separators
            match = re.match(r'^([A-Za-z][A-Za-z0-9\s\-\']+?)[\:\-\–\—]\s*(.+)$', line)
            if match:
                ability_name = match.group(1).strip()
                description = match.group(2).strip()
                
                # Filter out non-ability titles (like section headers)
                skip_words = ["phase", "introduction", "unlock", "preparation", "summary", "overview"]
                if (len(ability_name) > 2 and len(ability_name) < 50 and 
                    not any(skip in ability_name.lower() for skip in skip_words)):
                    abilities.append({
                        "name": ability_name,
                        "description": description,
                    })
        
        return abilities

    async def fetch_hardcoregamer_guide(self, boss_name: str) -> dict[str, Any]:
        """Fetch guide content from Hardcore Gamer."""
        normalized_name = self._normalize_boss_name(boss_name)
        url = f"https://hardcoregamer.com/?s={normalized_name}+ffxiv"

        try:
            search_response = await self.http_client.get(url)
            if search_response.status_code != 200:
                return {"success": False, "error": f"HTTP {search_response.status_code}", "url": url}

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
            "ability_map": {},
            "tips": [],
        }

        main_content = soup.find("article") or soup.find("main") or soup.find("div", class_=re.compile(r"content|post"))

        if not main_content:
            return result

        paragraphs = main_content.find_all("p")
        if paragraphs:
            result["overview"] = paragraphs[0].get_text(strip=True)

        return result

    async def fetch_all_guides(self, boss_name: str) -> dict[str, Any]:
        """Fetch guides from all supported sources."""
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

        # Merge ability maps from all sources
        merged_ability_map = {}
        for source, guide in results["guides"].items():
            if guide.get("success"):
                content = guide.get("content", {})
                ability_map = content.get("ability_map", {})
                merged_ability_map.update(ability_map)
        
        results["merged_ability_map"] = merged_ability_map

        return results

    def find_ability_description(self, ability_name: str, guide_data: dict[str, Any]) -> str | None:
        """Find description for a specific ability from guide data."""
        merged_map = guide_data.get("merged_ability_map", {})
        if ability_name in merged_map:
            return merged_map[ability_name]
        
        # Search through all guides
        guides = guide_data.get("guides", {})
        for source, guide in guides.items():
            if not guide.get("success"):
                continue
                
            content = guide.get("content", {})
            ability_map = content.get("ability_map", {})
            
            if ability_name in ability_map:
                return ability_map[ability_name]
        
        return None
