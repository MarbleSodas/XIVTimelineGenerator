"""
Transcript Enrichment Pipeline

Integrates YouTube guide discovery, transcript fetching, description generation,
and variant analysis into the existing timeline generation pipeline.

This enriches timelines with actual guide knowledge instead of just using
statistical damage analysis.
"""
from typing import List, Optional, Dict, Any
import logging

from schemas.youtube_schemas import (
    YouTubeGuideInput,
    YouTubeGuideOutput,
    YouTubeTranscript,
    GuideVariant,
    TranscriptEnrichedAction,
    TimelineEnrichmentInput,
    TimelineEnrichmentOutput,
)
from schemas.cactbot_schemas import CactbotTimelineEntry
from schemas.aggregation_schemas import AggregatedAction
from schemas.timeline_schemas import BossAction

from agents.youtube_guide_agent import YouTubeGuideDiscoveryAgent
from agents.description_generator_agent import (
    DescriptionGeneratorAgent,
    TranscriptDescriptionGenerator,
)
from agents.variant_analyzer_agent import (
    TranscriptVariantAnalyzer,
    VariantMerger,
)
from agents.online_guide_parser import OnlineGuideParserAgent, OnlineGuideDiscoveryAgent

logger = logging.getLogger(__name__)


class TranscriptEnrichmentOrchestrator:
    """
    Orchestrates the transcript enrichment pipeline.
    
    Pipeline:
    1. Discover YouTube guides for the boss
    2. Fetch transcripts from relevant guides
    3. Generate detailed descriptions for each action
    4. Extract variants from guide strategies
    5. Merge with statistical variants from FFLogs
    """
    
    def __init__(
        self,
        llm_client=None,
        youtube_api_key: Optional[str] = None,
        raw_llm_client=None,
        model: str = "MiniMax-M2.5",
    ):
        self.llm_client = llm_client
        self.raw_llm_client = raw_llm_client
        self.youtube_api_key = youtube_api_key
        self.model = model
        
        self.guide_discovery = YouTubeGuideDiscoveryAgent(
            api_key=youtube_api_key,
        )
        
        self.description_generator = DescriptionGeneratorAgent(
            client=llm_client,
        )
        
        self.transcript_generator = TranscriptDescriptionGenerator(
            llm_client=llm_client,
        )
        
        self.variant_analyzer = TranscriptVariantAnalyzer(
            client=llm_client,
        )
        
        self.variant_merger = VariantMerger()
        
        self.online_guide_parser = OnlineGuideParserAgent(
            client=llm_client,
            model=model,
        )
        
        self.online_guide_discovery = OnlineGuideDiscoveryAgent()
    
    def run(
        self,
        enrichment_input: TimelineEnrichmentInput,
        cactbot_entries: List[CactbotTimelineEntry],
        aggregated_actions: List[AggregatedAction],
        statistical_variants: List[Dict[str, Any]],
    ) -> TimelineEnrichmentOutput:
        """
        Run the full enrichment pipeline.
        
        Args:
            enrichment_input: Basic input (boss ID, video IDs, etc.)
            cactbot_entries: Timeline entries from Cactbot
            aggregated_actions: Aggregated actions with damage data
            statistical_variants: Variants from FFLogs analysis
            
        Returns:
            Enriched timeline with descriptions and variants
        """
        boss_id = enrichment_input.boss_id
        boss_name = enrichment_input.boss_name
        
        transcripts = self._fetch_transcripts(
            boss_id,
            boss_name,
            enrichment_input.youtube_video_ids,
        )
        
        online_guide_descriptions = self._fetch_online_guide_descriptions(
            boss_id,
            boss_name,
            [e.name for e in cactbot_entries],
        )
        
        enriched_actions = self._generate_descriptions(
            cactbot_entries,
            aggregated_actions,
            transcripts,
            online_guide_descriptions,
        )
        
        transcript_variants = self.variant_analyzer.extract_variants(
            [e.name for e in cactbot_entries],
            transcripts,
        )
        
        timeline_abilities = [e.name for e in cactbot_entries]
        merged_variants = self.variant_merger.merge_variants(
            statistical_variants,
            transcript_variants,
            timeline_abilities,
        )
        
        final_actions = self._build_enriched_actions(
            enriched_actions,
            merged_variants,
        )
        
        phase_summary = self._generate_phase_summary(
            cactbot_entries,
            transcripts,
        )
        
        return TimelineEnrichmentOutput(
            boss_id=boss_id,
            enriched_actions=final_actions,
            variants=transcript_variants,
            phase_summary=phase_summary,
            transcripts_used=len(transcripts),
            analysis_success=True,
        )
    
    def _fetch_online_guide_descriptions(
        self,
        boss_id: str,
        boss_name: str,
        timeline_abilities: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        """Fetch and parse descriptions from online guide articles with fallback"""
        
        online_descriptions: Dict[str, Dict[str, Any]] = {}
        
        guides = self.online_guide_discovery.discover_with_fallback(boss_id, boss_name)
        
        for guide in guides:
            try:
                result = self.online_guide_parser.run(
                    guide_url=guide["url"],
                    timeline_abilities=timeline_abilities,
                    boss_name=boss_name,
                )
                
                if result.get("descriptions"):
                    for ability, desc_data in result["descriptions"].items():
                        if ability not in online_descriptions:
                            online_descriptions[ability] = desc_data
                            
            except Exception as e:
                logger.warning(f"Failed to parse online guide {guide.get('url')}: {e}")
        
        return online_descriptions
    
    def _fetch_transcripts(
        self,
        boss_id: str,
        boss_name: str,
        video_ids: List[str],
    ) -> List[YouTubeTranscript]:
        """Fetch transcripts from YouTube guides"""
        transcripts = []
        
        # If specific video IDs provided, fetch those
        if video_ids:
            for video_id in video_ids:
                transcript = self.guide_discovery.get_transcript_only(video_id)
                if transcript:
                    transcripts.append(transcript)
        
        # Otherwise, discover relevant guides
        if not transcripts:
            try:
                guide_input = YouTubeGuideInput(
                    boss_id=boss_id,
                    boss_name=boss_name,
                    max_results=3,
                )
                
                guide_output = self.guide_discovery.run(guide_input)
                
                # guide_discovery.run() fetches transcripts internally
                # We need to re-fetch them since they're not in the output
                if guide_output and guide_output.videos:
                    for video in guide_output.videos[:3]:
                        transcript = self.guide_discovery.get_transcript_only(video.video_id)
                        if transcript:
                            transcripts.append(transcript)
                            
            except Exception as e:
                logger.warning(f"Failed to discover guides: {e}")
        
        return transcripts
    
    def _find_transcript_snippets_chronological(
        self,
        timeline_entries: List[CactbotTimelineEntry],
        transcripts: List[YouTubeTranscript],
        max_snippets_per_ability: int = 2,
    ) -> Dict[str, List[str]]:
        """
        Find transcript snippets for abilities in CHRONOLOGICAL order based on timeline.
        
        This method processes abilities in timeline ORDER and finds the FIRST occurrence
        of each ability in the transcript (which represents when the guide mentions it).
        This ensures descriptions are generated based on proper context.
        
        Returns:
            Dict mapping ability name -> list of transcript snippets
        """
        ability_snippets: Dict[str, List[str]] = {}
        used_segments: set = set()  # Track segments already used to avoid duplicates
        
        for entry in timeline_entries:
            ability_name = entry.name
            ability_lower = ability_name.lower()
            ability_words = ability_lower.replace("-", " ").replace("(", " ").replace(")", " ").split()
            ability_aliases = self._get_ability_aliases(ability_name)
            
            snippets: List[str] = []
            
            # Search transcripts in order - find FIRST match for this ability
            for transcript in transcripts:
                for seg_idx, segment in enumerate(transcript.segments):
                    # Skip already used segments
                    segment_key = f"{transcript.video_id}_{seg_idx}"
                    if segment_key in used_segments:
                        continue
                    
                    text_lower = segment.text.lower()
                    
                    # Check for exact match first
                    match_found = False
                    if ability_lower in text_lower:
                        match_found = True
                    elif any(alias in text_lower for alias in ability_aliases if alias):
                        match_found = True
                    elif any(len(word) >= 4 and word in text_lower for word in ability_words):
                        # Only match significant words (4+ chars)
                        significant_words = [w for w in ability_words if len(w) >= 4]
                        if significant_words and any(w in text_lower for w in significant_words):
                            match_found = True
                    
                    if match_found:
                        snippets.append(segment.text)
                        used_segments.add(segment_key)
                        break  # Only take first match per transcript for this ability
                
                if snippets and len(snippets) >= max_snippets_per_ability:
                    break  # Got enough snippets for this ability
            
            if snippets:
                ability_snippets[ability_name] = snippets
        
        return ability_snippets
    
    def _find_transcript_snippets_improved(
        self,
        ability_name: str,
        transcripts: List[YouTubeTranscript],
        timeline_order: List[str],
        max_snippets: int = 3,
    ) -> List[str]:
        """Find relevant transcript snippets with fuzzy matching (legacy method)"""
        snippets = []
        ability_lower = ability_name.lower()
        ability_words = ability_lower.replace("-", " ").replace("(", " ").replace(")", " ").split()
        
        ability_aliases = self._get_ability_aliases(ability_name)
        
        for transcript in transcripts:
            for segment in transcript.segments:
                text_lower = segment.text.lower()
                
                if ability_lower in text_lower:
                    snippets.append(segment.text)
                    if len(snippets) >= max_snippets:
                        return snippets
                
                for alias in ability_aliases:
                    if alias in text_lower:
                        snippets.append(segment.text)
                        if len(snippets) >= max_snippets:
                            return snippets
                
                for word in ability_words:
                    if len(word) >= 4 and word in text_lower:
                        snippets.append(segment.text)
                        if len(snippets) >= max_snippets:
                            return snippets
        
        return snippets
    
    def _get_ability_aliases(self, ability_name: str) -> List[str]:
        """Get common aliases for FFXIV abilities"""
        name_lower = ability_name.lower()
        
        aliases = {
            "dark force": ["orbital", "orbit", "omen"],
            "soul rush": ["sword", "sword rush"],
            "dimension slash": ["dimension", "slash", "line"],
            "triple slash": ["triple", "three", "tri"],
            "akh afah": ["akh", "afah", "meteor", "meteors"],
            "mirage": ["mirror", "clone", "image"],
            "scythe": ["axe", "weapon"],
            "cleave": ["frontal", "cone", "aoe"],
            "raidwide": ["party wide", "everyone", "all"],
            "tank buster": ["tank", "buster", "tether"],
            "stack": ["stack", "together", "group"],
            "spread": ["spread", "apart"],
        }
        
        for key, values in aliases.items():
            if key in name_lower:
                return values
        
        return []
    
    def _generate_descriptions(
        self,
        cactbot_entries: List[CactbotTimelineEntry],
        aggregated_actions: List[AggregatedAction],
        transcripts: List[YouTubeTranscript],
        online_guide_descriptions: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[TranscriptEnrichedAction]:
        """Generate detailed descriptions using chronological transcript matching and online guides"""
        enriched = []
        
        online_guide_descriptions = online_guide_descriptions or {}
        
        timeline_order = [e.name for e in cactbot_entries]
        
        damage_lookup = {
            a.name: {
                "damage": a.unmitigated_damage,
                "type": a.damage_type,
                "is_tank_buster": a.is_tank_buster,
                "hit_count": a.hit_count,
            }
            for a in aggregated_actions
        }
        
        full_transcript_text = ""
        for transcript in transcripts:
            full_transcript_text += " ".join(seg.text for seg in transcript.segments) + "\n"
        
        # Use CHRONOLOGICAL matching - finds FIRST occurrence of each ability in transcript
        ability_snippets = self._find_transcript_snippets_chronological(
            cactbot_entries,
            transcripts,
            max_snippets_per_ability=2,
        )
        
        if self.raw_llm_client and ability_snippets and full_transcript_text:
            try:
                descriptions = self._generate_llm_descriptions(
                    cactbot_entries,
                    ability_snippets,
                    damage_lookup,
                    full_transcript_text,
                    timeline_order,
                )
                
                for entry in cactbot_entries:
                    damage_info = damage_lookup.get(entry.name, {})
                    
                    description = descriptions.get(entry.name)
                    if not description and entry.name in online_guide_descriptions:
                        og_desc = online_guide_descriptions[entry.name]
                        description = og_desc.get("description")
                    
                    if not description:
                        description = self._rule_based_description(
                            entry.name,
                            damage_info,
                        )
                    
                    enriched.append(TranscriptEnrichedAction(
                        time=entry.time,
                        name=entry.name,
                        id=f"{entry.name.lower().replace(' ', '_')}_{entry.time:.0f}",
                        unmitigated_damage=damage_info.get("damage"),
                        damage_type=damage_info.get("type"),
                        importance="medium",
                        is_tank_buster=damage_info.get("is_tank_buster", False),
                        hit_count=damage_info.get("hit_count") or entry.hit_count,
                        transcript_description=description,
                        is_variant_point=entry.name in ability_snippets,
                    ))
            except Exception as e:
                logger.warning(f"LLM description generation failed: {e}")
        
        if not enriched:
            for entry in cactbot_entries:
                damage_info = damage_lookup.get(entry.name, {})
                snippets = ability_snippets.get(entry.name, [])
                
                description = None
                if entry.name in online_guide_descriptions:
                    og_desc = online_guide_descriptions[entry.name]
                    description = og_desc.get("description")
                
                if not description:
                    if snippets and self.llm_client:
                        description = self.transcript_generator.generate_description(
                            entry.name,
                            snippets,
                        )
                    else:
                        description = self._rule_based_description(
                            entry.name,
                            damage_info,
                        )
                
                enriched.append(TranscriptEnrichedAction(
                    time=entry.time,
                    name=entry.name,
                    id=f"{entry.name.lower().replace(' ', '_')}_{entry.time:.0f}",
                    unmitigated_damage=damage_info.get("damage"),
                    damage_type=damage_info.get("type"),
                    importance="medium",
                    is_tank_buster=damage_info.get("is_tank_buster", False),
                    hit_count=damage_info.get("hit_count") or entry.hit_count,
                    transcript_description=description if (snippets or online_guide_descriptions.get(entry.name)) else None,
                    is_variant_point=bool(snippets),
                ))
        
        return enriched
    
    def _generate_llm_descriptions(
        self,
        cactbot_entries: List[CactbotTimelineEntry],
        ability_snippets: Dict[str, List[str]],
        damage_lookup: Dict[str, Any],
        full_transcript_text: str,
        timeline_order: List[str],
    ) -> Dict[str, str]:
        """Use LLM to generate descriptions based on transcript and timeline order"""
        
        # Build context for each ability
        abilities_context = []
        for i, entry in enumerate(cactbot_entries):
            name = entry.name
            snippets = ability_snippets.get(name, [])
            damage_info = damage_lookup.get(name, {})
            
            # Get previous and next abilities for context
            prev_ability = timeline_order[i-1] if i > 0 else None
            next_ability = timeline_order[i+1] if i < len(timeline_order) - 1 else None
            
            abilities_context.append({
                "index": i + 1,
                "name": name,
                "time": entry.time,
                "snippets": snippets[:3],
                "damage_type": damage_info.get("type"),
                "is_tank_buster": damage_info.get("is_tank_buster", False),
                "hit_count": damage_info.get("hit_count"),
                "previous_ability": prev_ability,
                "next_ability": next_ability,
            })
        
        # Build prompt
        abilities_json = "\n".join([
            f'{a["index"]}. {a["name"]} @ {a["time"]}s - {a["damage_type"] or "unknown"} damage'
            + (f' (tank buster)' if a["is_tank_buster"] else '')
            + (f' - {a["hit_count"]} hits' if a["hit_count"] else '')
            for a in abilities_context[:20]  # Limit to first 20 for token limit
        ])
        
        # Get relevant transcript snippets for mentioned abilities
        mentioned_abilities = list(ability_snippets.keys())
        relevant_transcript = self._extract_relevant_transcript(
            full_transcript_text, 
            mentioned_abilities[:10],
            max_chars=8000,
        )
        
        prompt = f"""You are an FFXIV raid guide expert. Generate clear, concise descriptions for each boss ability based on the guide transcript and timeline order.

## Timeline Order (first 20 abilities):
{abilities_json}

## Guide Transcript (relevant sections):
{relevant_transcript}

## Your Task:
For each ability in the timeline above that has transcript snippets, generate a 1-2 sentence description that explains:
1. What the mechanic does
2. How players should respond (positioning, mitigation, markers)

## IMPORTANT - Use Exact Timeline Names:
You MUST use the EXACT ability names from the timeline above as JSON keys. Do NOT rename or create new ability names.
- Use "Frontal Cleave" NOT "Conal Cleave"
- Use "Dark Force" NOT "Crown of Arcadia"  
- Use "Raidwide" NOT "raidwide" or other variants
- Use "Tank Buster" NOT "Raw Steel Trophy"

## Output Format:
Return a JSON object with ability names as keys and descriptions as values.
Example:
{{
  "Frontal Cleave": "Description of the mechanic and how to handle it.",
  "Dark Force": "Description of the mechanic and how to handle it."
}}

Only include abilities from the timeline above that have transcript information. Use the EXACT names from the timeline."""

        # Use raw client if available, otherwise try to use llm_client
        client = self.raw_llm_client or self.llm_client
        if not client:
            return {}
        
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an FFXIV raid guide expert. Generate accurate mechanic descriptions based on the transcript."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=2000,
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON from response - handle MiniMax reasoning format
            import json
            import re
            
            # First, try to extract JSON from code blocks (```json ... ```)
            json_block_match = re.search(r'```json\s*([\s\S]*?)\s*```', result_text)
            if json_block_match:
                try:
                    return json.loads(json_block_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # Try to extract JSON from the response (skip reasoning if present)
            # Remove <think> ... </think> blocks first
            cleaned = re.sub(r'<think>.*?</think>', '', result_text, flags=re.DOTALL).strip()
            
            # Try to find JSON object in the cleaned response
            json_match = re.search(r'\{[\s\S]*\}', cleaned)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            # Try whole cleaned response as JSON
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM response as JSON: {cleaned[:200]}")
                return {}
                
        except Exception as e:
            logger.warning(f"LLM call failed: {e}")
            return {}
    
    def _extract_relevant_transcript(
        self,
        full_transcript: str,
        ability_names: List[str],
        max_chars: int = 8000,
    ) -> str:
        """Extract relevant sections of transcript for given abilities"""
        transcript_lower = full_transcript.lower()
        
        relevant_parts = []
        for ability in ability_names:
            ability_lower = ability.lower()
            
            # Find position of ability name in transcript
            pos = transcript_lower.find(ability_lower)
            if pos == -1:
                # Try parts of the name
                for word in ability_lower.split():
                    if len(word) > 3:
                        pos = transcript_lower.find(word)
                        if pos != -1:
                            break
            
            if pos != -1:
                # Extract context around the mention
                start = max(0, pos - 200)
                end = min(len(full_transcript), pos + 400)
                context = full_transcript[start:end]
                relevant_parts.append(context)
        
        # Combine and truncate
        combined = " ... ".join(relevant_parts)
        if len(combined) > max_chars:
            combined = combined[:max_chars] + "..."
        
        return combined or full_transcript[:max_chars]
    
    def _find_transcript_snippets(
        self,
        ability_name: str,
        transcripts: List[YouTubeTranscript],
        max_snippets: int = 3,
    ) -> List[str]:
        """Find relevant transcript snippets for an ability"""
        snippets = []
        ability_lower = ability_name.lower()
        
        for transcript in transcripts:
            for segment in transcript.segments:
                if ability_lower in segment.text.lower():
                    snippets.append(segment.text)
                    if len(snippets) >= max_snippets:
                        return snippets
        
        return snippets
    
    def _rule_based_description(
        self,
        ability_name: str,
        damage_info: Dict[str, Any],
    ) -> str:
        name_lower = ability_name.lower()
        parts = []
        damage_type = damage_info.get("type")
        
        hit_count = damage_info.get("hit_count")
        if hit_count and hit_count > 1:
            parts.append(f"Tank buster - {hit_count} hits")
        elif damage_info.get("is_tank_buster"):
            parts.append("Tank buster")
        elif "raidwide" in name_lower or "party" in name_lower:
            parts.append("Raidwide damage")
        
        if "stack" in name_lower:
            parts.append("stack marker")
        if "spread" in name_lower:
            parts.append("spread")
        if "frontal" in name_lower or "cleave" in name_lower:
            parts.append("frontal AoE")
        
        if not parts:
            parts.append("damage mechanic")
        
        result = ". ".join(parts)
        
        if damage_type and damage_type not in result.lower():
            result = f"({damage_type}) {result}"
        
        return result.capitalize() + "."
    
    def _is_variant_point(
        self,
        ability_name: str,
        transcripts: List[YouTubeTranscript],
    ) -> bool:
        """Check if an ability has variant information in transcripts"""
        ability_lower = ability_name.lower()
        
        variant_keywords = {
            "alternative", "or", "if", "depending", "choice",
            "swap", "switch", "sometimes", "may", "can",
        }
        
        for transcript in transcripts:
            for segment in transcript.segments:
                text_lower = segment.text.lower()
                if ability_lower in text_lower:
                    if any(kw in text_lower for kw in variant_keywords):
                        return True
        
        return False
    
    def _build_enriched_actions(
        self,
        enriched: List[TranscriptEnrichedAction],
        merged_variants: Dict[str, List[str]],
    ) -> List[TranscriptEnrichedAction]:
        """Build final enriched actions with variant information"""
        for action in enriched:
            # Check if this action is at a variant point
            for time_key, variant_abilities in merged_variants.items():
                if action.name.lower() in [a.lower() for a in variant_abilities]:
                    action.is_variant_point = True
                    action.variants = variant_abilities
        
        return enriched
    
    def _generate_phase_summary(
        self,
        cactbot_entries: List[CactbotTimelineEntry],
        transcripts: List[YouTubeTranscript],
    ) -> Dict[str, str]:
        """Generate summary of fight phases"""
        # Simple phase estimation based on timing
        phases = {}
        
        if not cactbot_entries:
            return phases
        
        total_duration = max(e.time for e in cactbot_entries)
        
        # Divide into rough phases
        if total_duration > 300:  # Long fight
            phases["Phase 1 (0-40%)"] = "Early phase - basic mechanics"
            phases["Phase 2 (40-70%)"] = "Mid phase - increased complexity"
            phases["Phase 3 (70-100%)"] = "Final phase - enrage mechanics"
        else:
            phases["Phase 1"] = "First half of the fight"
            phases["Phase 2"] = "Second half - final mechanics"
        
        # Try to extract more specific phase info from transcripts
        for transcript in transcripts:
            text_lower = transcript.full_text.lower()
            
            phase_keywords = {
                "phase 1": "phase 1",
                "phase 2": "phase 2", 
                "phase 3": "phase 3",
                "phase 4": "phase 4",
                "add phase": "add phase",
                "enrage": "enrage phase",
            }
            
            for keyword, phase_name in phase_keywords.items():
                if keyword in text_lower:
                    # Found phase mention - this would need more sophisticated extraction
                    pass
        
        return phases
    
    def close(self):
        """Clean up resources"""
        self.guide_discovery.close()
        if hasattr(self, 'online_guide_parser'):
            self.online_guide_parser.close()
        if hasattr(self, 'online_guide_discovery'):
            self.online_guide_discovery.close()


class TranscriptEnrichmentRequest:
    """Request to enrich timeline with transcript data"""
    
    def __init__(
        self,
        boss_id: str,
        boss_name: str,
        cactbot_entries: List[CactbotTimelineEntry],
        aggregated_actions: List[AggregatedAction],
        statistical_variants: List[Dict[str, Any]],
        youtube_video_ids: Optional[List[str]] = None,
    ):
        self.boss_id = boss_id
        self.boss_name = boss_name
        self.cactbot_entries = cactbot_entries
        self.aggregated_actions = aggregated_actions
        self.statistical_variants = statistical_variants
        self.youtube_video_ids = youtube_video_ids or []


# Standalone function for simple enrichment
def enrich_timeline_with_transcripts(
    request: TranscriptEnrichmentRequest,
    llm_client=None,
    youtube_api_key: Optional[str] = None,
) -> TimelineEnrichmentOutput:
    """
    Convenience function to enrich a timeline with transcript data.
    
    Example:
        >>> request = TranscriptEnrichmentRequest(
        ...     boss_id="r7s",
        ...     boss_name="Brute Abombinator",
        ...     cactbot_entries=[...],
        ...     aggregated_actions=[...],
        ...     statistical_variants=[...],
        ... )
        >>> result = enrich_timeline_with_transcripts(request, llm_client)
    """
    orchestrator = TranscriptEnrichmentOrchestrator(
        llm_client=llm_client,
        youtube_api_key=youtube_api_key,
    )
    
    try:
        input_data = TimelineEnrichmentInput(
            boss_id=request.boss_id,
            boss_name=request.boss_name,
            base_timeline=[],
            youtube_video_ids=request.youtube_video_ids,
            include_variants=True,
        )
        
        return orchestrator.run(
            input_data,
            request.cactbot_entries,
            request.aggregated_actions,
            request.statistical_variants,
        )
    finally:
        orchestrator.close()


if __name__ == "__main__":
    # Quick test
    print("Transcript Enrichment Pipeline")
    print("=" * 40)
    print("This module provides:")
    print("  - YouTubeGuideDiscoveryAgent")
    print("  - DescriptionGeneratorAgent") 
    print("  - TranscriptVariantAnalyzer")
    print("  - TranscriptEnrichmentOrchestrator")
    print()
    print("Usage:")
    print("  from agents.transcript_enrichment_orchestrator import (")
    print("      TranscriptEnrichmentOrchestrator,")
    print("      TranscriptEnrichmentRequest,")
    print("      enrich_timeline_with_transcripts,")
    print("  )")
