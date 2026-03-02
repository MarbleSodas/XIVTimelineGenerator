"""
Online Guide Parser Agent

Parses guide articles and extracts ability descriptions using LLM.
"""
import json
import re
from typing import List, Optional, Dict, Any

from tools.online_guide_fetcher import OnlineGuideFetcher, OnlineGuideError
from schemas.youtube_schemas import GuideActionDescription, GuideVariant


class OnlineGuideParserAgent:
    """
    Agent for parsing online guide articles.
    
    Extracts:
    - Ability descriptions with fuzzy matching to timeline
    - Mechanic explanations
    - Positioning advice
    - Variant/strategy information
    """
    
    def __init__(
        self,
        client=None,
        model: str = "MiniMax-M2.5",
    ):
        self.client = client
        self.model = model
        self.fetcher = OnlineGuideFetcher()
    
    def run(
        self,
        guide_url: str,
        timeline_abilities: List[str],
        boss_name: str,
    ) -> Dict[str, Any]:
        """
        Parse online guide and extract ability descriptions.
        
        Args:
            guide_url: URL of the guide article
            timeline_abilities: List of ability names from timeline
            boss_name: Name of the boss
            
        Returns:
            Dict with 'descriptions', 'variants', 'success', 'error'
        """
        try:
            guide_text = self.fetcher.fetch_guide_text(guide_url)
            
            if not guide_text or len(guide_text) < 100:
                return {
                    "descriptions": {},
                    "variants": [],
                    "success": False,
                    "error": "Guide text too short or empty",
                }
            
            if not self.client:
                return self._rule_based_parse(guide_text, timeline_abilities)
            
            return self._llm_parse(guide_text, timeline_abilities, boss_name)
            
        except OnlineGuideError as e:
            return {
                "descriptions": {},
                "variants": [],
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            return {
                "descriptions": {},
                "variants": [],
                "success": False,
                "error": f"Parse error: {e}",
            }
    
    def _llm_parse(
        self,
        guide_text: str,
        timeline_abilities: List[str],
        boss_name: str,
    ) -> Dict[str, Any]:
        """Use LLM to parse guide text with better ability matching"""
        
        abilities_list = "\n".join([f"- {a}" for a in timeline_abilities[:40]])
        
        prompt = f"""You are an FFXIV raid guide expert. Extract ability descriptions from the guide article below.

## Boss: {boss_name}

## Timeline Abilities (use EXACT names from this list):
{abilities_list}

## Guide Article:
{guide_text[:12000]}

## Your Task:
For each ability in the timeline list above, find if it's mentioned in the guide and extract a description. 

## IMPORTANT - Fuzzy Matching:
The guide may use slightly different names for abilities. Try to match:
- Exact matches
- Abbreviated names (e.g., "Uptime" for "Uptime Boss")
- Common synonyms
- Abilities with numbers (e.g., "1" vs "One")
- Plural vs singular forms

For each matched ability, provide:
1. "description": 1-2 sentence description of what the mechanic does
2. "positioning": Where to stand (if mentioned)
3. "mechanics": Array of key mechanics
4. "mitigation": How to mitigate (if mentioned)

## Output Format:
Return a JSON object:
{{
  "Ability Name from Timeline": {{
    "description": "description of mechanic",
    "positioning": "where to stand or null",
    "mechanics": ["mechanic 1", "mechanic 2"],
    "mitigation": ["mitigation tip 1"]
  }}
}}

Only include abilities that are actually discussed in the guide. Use EXACT timeline names as keys."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an FFXIV raid guide expert. Extract accurate mechanic descriptions using fuzzy name matching."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=3000,
            )
            
            result_text = response.choices[0].message.content.strip()
            
            json_match = re.search(r'\{[\s\S]*\}', result_text)
            if json_match:
                parsed = json.loads(json_match.group())
                
                return {
                    "descriptions": parsed,
                    "success": True,
                }
            
            return {
                "descriptions": {},
                "success": False,
                "error": "Failed to parse LLM response",
            }
            
        except Exception as e:
            return {
                "descriptions": {},
                "success": False,
                "error": f"LLM error: {e}",
            }
    
    def _rule_based_parse(
        self,
        guide_text: str,
        timeline_abilities: List[str],
    ) -> Dict[str, Any]:
        """Fallback rule-based parsing without LLM"""
        
        descriptions = {}
        guide_lower = guide_text.lower()
        
        for ability in timeline_abilities:
            ability_lower = ability.lower()
            
            if ability_lower in guide_lower:
                snippet_start = guide_lower.find(ability_lower)
                snippet = guide_text[max(0, snippet_start-50):snippet_start+200]
                
                descriptions[ability] = {
                    "description": snippet.strip(),
                    "positioning": None,
                    "mechanics": [],
                    "mitigation": [],
                }
        
        return {
            "descriptions": descriptions,
            "success": len(descriptions) > 0,
        }
    
    def extract_variants(
        self,
        guide_text: str,
        timeline_abilities: List[str],
        boss_name: str = "",
    ) -> List[Dict[str, Any]]:
        """Extract variant/strategy information from guide using LLM"""
        
        if not self.client:
            return []
        
        abilities_list = "\n".join([f"- {a}" for a in timeline_abilities[:30]])
        
        prompt = f"""You are an FFXIV strategy analyst. Extract timeline variants and strategies from this guide.

## Boss: {boss_name}

## Timeline Abilities:
{abilities_list}

## Guide Article:
{guide_text[:8000]}

## Your Task:
Find where the guide discusses alternative strategies, variants, or conditional mechanics. Look for:
- "or" statements (do X or do Y)
- "if" conditions (if this happens, do that)  
- "sometimes", "may", "can", "depending"
- Different roles handling abilities differently
- Phase-specific strategies
- Prio (priority) mentions
- Swap/tether mechanics with alternatives

## Output:
Return a JSON array of variants:
[
  {{
    "ability": "Exact ability name from timeline",
    "description": "What triggers this variant or when it applies",
    "alternatives": ["option 1", "option 2"],
    "condition": "when this variant occurs"
  }}
]

Only include actual variants/alternatives, not general advice. If no variants found, return empty array []."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an FFXIV strategy analyst. Extract precise variant information."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=1500,
            )
            
            result_text = response.choices[0].message.content.strip()
            
            json_match = re.search(r'\[[\s\S]*\]', result_text)
            if json_match:
                variants = json.loads(json_match.group())
                return variants
            
        except Exception:
            pass
        
        return []
    
    def close(self):
        """Clean up resources"""
        self.fetcher.close()


class OnlineGuideDiscoveryAgent:
    """
    Discovers guide URLs for bosses with fallback sources.
    """
    
    def __init__(self):
        self.fetcher = OnlineGuideFetcher()
    
    def discover_guides(
        self,
        boss_id: str,
        boss_name: str,
    ) -> List[Dict[str, Any]]:
        """
        Discover guide URLs for a boss with fallback sources.
        """
        from config import config
        
        boss_config = config.get_boss_config(boss_id)
        if not boss_config:
            return []
        
        guide_urls = boss_config.get("guide_urls", [])
        
        guides = []
        for url in guide_urls:
            is_fallback = any(fb in url.lower() for fb in self.fetcher.FALLBACK_SOURCES)
            guides.append({
                "url": url,
                "source": url.split("/")[2] if "/" in url else "unknown",
                "relevance": 0.5 if is_fallback else 1.0,
                "is_fallback": is_fallback,
            })
        
        guides.sort(key=lambda x: x["relevance"], reverse=True)
        
        return guides
    
    def discover_with_fallback(
        self,
        boss_id: str,
        boss_name: str,
    ) -> List[Dict[str, Any]]:
        """Discover guides with automatic fallback to icy-veins"""
        
        guides = self.discover_guides(boss_id, boss_name)
        
        primary_guides = [g for g in guides if not g.get("is_fallback")]
        fallback_guides = [g for g in guides if g.get("is_fallback")]
        
        if primary_guides:
            return primary_guides
        elif fallback_guides:
            return fallback_guides
        
        return guides
    
    def close(self):
        self.fetcher.close()
