"""
Variant Analyzer Agent

Extracts timeline variations from YouTube guide transcripts.
Identifies:
- Alternative strategies/paths
- Phase transitions and their triggers
- Conditional mechanics (enrage timing, phase-based)
- Position swaps and role-specific mechanics
"""
import re
from typing import List, Dict, Any, Optional, Set
from pydantic import Field

from atomic_agents import AtomicAgent, AgentConfig, BaseIOSchema
from atomic_agents.context import SystemPromptGenerator

from schemas.youtube_schemas import (
    YouTubeTranscript,
    GuideVariant,
)


SYSTEM_PROMPT = SystemPromptGenerator(
    background=[
        "You analyze FFXIV raid guides to extract timeline variations.",
        "You understand how different strategies create different timeline paths.",
        "You identify conditional mechanics and phase-based variations.",
    ],
    steps=[
        "1. Scan transcript for mentions of variations, alternatives, or conditions",
        "2. Identify phase transitions and their triggers",
        "3. Extract position swaps, role assignments, and strategy differences",
        "4. Note timing variations (enrage speed, phase timing)",
        "5. Document each variant with its trigger condition",
    ],
    output_instructions=[
        "Return variants as a structured list",
        "Include trigger conditions when mentioned",
        "Group variants by their timing in the fight",
    ],
)


class VariantExtractionInput(BaseIOSchema):
    """Input for variant extraction"""
    boss_id: str
    boss_name: str
    timeline_abilities: List[str] = Field(
        default_factory=list,
        description="List of abilities in the timeline",
    )
    transcripts: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Transcript data with video metadata",
    )


class ExtractedVariant(BaseIOSchema):
    """A single extracted variant"""
    variant_id: str
    branch_point: str = Field(description="Approximate timing (e.g., '90s', 'phase 2')")
    trigger_condition: Optional[str] = Field(None, description="What triggers this variant")
    description: str
    alternate_abilities: List[str] = Field(default_factory=list)
    strategy_notes: str = ""


class VariantExtractionOutput(BaseIOSchema):
    """Output from variant extraction"""
    boss_id: str
    variants: List[ExtractedVariant]
    phase_transitions: List[Dict[str, str]] = Field(default_factory=list)
    key_decision_points: List[str] = Field(default_factory=list)


# Keywords that indicate variants in transcripts
VARIANT_INDICATORS = {
    # Strategy variations
    "alternative", "instead", "or you can", "another way", "different strategy",
    "you could also", "option", "choice", "path", "route",
    
    # Phase/conditional
    "if you", "when you", "depending on", "based on", "after",
    "once", "until", "phase", "enrage",
    
    # Timing
    "faster", "slower", "earlier", "later", "delay", "push",
    
    # Role-specific
    "tank", "healer", "dps", "mt", "ot", "st", "party",
    
    # Position swaps
    "swap", "switch", "change position", "move to", "go to",
    "north", "south", "east", "west", "left", "right",
    
    # Conditional mechanics
    "if group", "if party", "unless", "except", "only when",
    "during", "outside", "inside",
}


class TranscriptVariantAnalyzer:
    """
    Analyzes transcripts to extract timeline variations.
    
    Uses both LLM (atomic agent) and rule-based approaches.
    """
    
    def __init__(self, client=None, model: str = "gpt-4o-mini"):
        self.client = client
        self.model = model
        self._agent = None
        
        if client:
            self._agent: AtomicAgent = AtomicAgent(
                config=AgentConfig(
                    client=client,
                    model=model,
                    system_prompt_generator=SYSTEM_PROMPT,
                    model_api_parameters={"temperature": 0.2},
                )
            )
    
    def extract_variants(
        self,
        timeline_abilities: List[str],
        transcripts: List[YouTubeTranscript],
    ) -> List[GuideVariant]:
        """Extract variants from transcripts"""
        variants: List[GuideVariant] = []
        
        if not transcripts:
            return variants
        
        # Try LLM-based extraction first
        if self._agent:
            try:
                variants = self._extract_with_llm(timeline_abilities, transcripts)
                if variants:
                    return variants
            except Exception:
                pass
        
        # Fall back to rule-based
        return self._extract_rule_based(timeline_abilities, transcripts)
    
    def _extract_with_llm(
        self,
        timeline_abilities: List[str],
        transcripts: List[YouTubeTranscript],
    ) -> List[GuideVariant]:
        """Extract variants using LLM"""
        # Prepare transcript data
        transcript_data = []
        for t in transcripts:
            transcript_data.append({
                "title": t.video_metadata.title,
                "channel": t.video_metadata.channel,
                "text": t.full_text[:5000],  # Limit length
            })
        
        input_data = VariantExtractionInput(
            boss_id="",  # Will be filled by caller
            boss_name="",
            timeline_abilities=timeline_abilities,
            transcripts=transcript_data,
        )
        
        result = self._agent.run(input_data)
        
        # Convert to GuideVariant
        guide_variants = []
        for v in result.variants:
            guide_variants.append(GuideVariant(
                variant_id=v.variant_id,
                branch_point=v.branch_point,
                trigger_condition=v.trigger_condition,
                description=v.description,
                alternate_abilities=v.alternate_abilities,
                strategy_notes=v.strategy_notes,
            ))
        
        return guide_variants
    
    def _extract_rule_based(
        self,
        timeline_abilities: List[str],
        transcripts: List[YouTubeTranscript],
    ) -> List[GuideVariant]:
        """Extract variants using rule-based approach"""
        variants: List[GuideVariant] = []
        variant_id_counter = 1
        
        ability_set = set(a.lower() for a in timeline_abilities)
        
        for transcript in transcripts:
            text = transcript.full_text.lower()
            sentences = re.split(r'[.!?]+', text)
            
            # Track which abilities are mentioned with variant indicators
            ability_variants: Dict[str, List[Dict[str, str]]] = {}
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                # Check if sentence mentions variant indicators
                has_variant_indicator = any(
                    indicator in sentence
                    for indicator in VARIANT_INDICATORS
                )
                
                if not has_variant_indicator:
                    continue
                
                # Check which abilities are mentioned
                mentioned_abilities = [
                    a for a in ability_set
                    if a.lower() in sentence
                ]
                
                for ability in mentioned_abilities:
                    if ability not in ability_variants:
                        ability_variants[ability] = []
                    
                    ability_variants[ability].append({
                        "sentence": sentence,
                        "context": self._classify_variant_context(sentence),
                    })
            
            # Convert to variants
            for ability, contexts in ability_variants.items():
                if len(contexts) >= 2:  # Need at least 2 mentions for variant
                    # Determine branch point
                    branch_point = self._estimate_branch_point(
                        ability, contexts, transcript.segments
                    )
                    
                    # Build description from context
                    descriptions = [c["context"] for c in contexts[:3]]
                    description = " | ".join(descriptions)
                    
                    variants.append(GuideVariant(
                        variant_id=f"transcript_variant_{variant_id_counter}",
                        branch_point=branch_point,
                        trigger_condition=self._extract_trigger_condition(contexts),
                        description=description[:200],  # Limit length
                        alternate_abilities=[],
                        strategy_notes="Extracted from guide transcript",
                    ))
                    
                    variant_id_counter += 1
        
        return variants
    
    def _classify_variant_context(self, sentence: str) -> str:
        """Classify what type of variant information is in the sentence"""
        sentence_lower = sentence.lower()
        
        if any(kw in sentence_lower for kw in ["swap", "switch", "change position"]):
            return "Position/swap variant"
        elif any(kw in sentence_lower for kw in ["tank", "mt", "ot", "healer"]):
            return "Role-specific variant"
        elif any(kw in sentence_lower for kw in ["if", "when", "depending"]):
            return "Conditional variant"
        elif any(kw in sentence_lower for kw in ["faster", "slower", "push"]):
            return "Timing variant"
        elif any(kw in sentence_lower for kw in ["phase"]):
            return "Phase transition"
        else:
            return "Strategy variant"
    
    def _estimate_branch_point(
        self,
        ability: str,
        contexts: List[Dict[str, str]],
        segments: List[Any],
    ) -> str:
        """Estimate when in the fight this variant occurs"""
        # This is a simplified version - in production, would use
        # timestamp information from segments
        
        # Default to mid-fight estimate
        return "mid-fight"
    
    def _extract_trigger_condition(self, contexts: List[Dict[str, str]]) -> Optional[str]:
        """Extract the trigger condition from contexts"""
        conditions = []
        
        for ctx in contexts:
            sentence = ctx.get("sentence", "")
            
            # Look for conditional phrases
            if_match = re.search(r"if\s+([^,.]+)", sentence)
            if if_match:
                conditions.append(if_match.group(1).strip())
            
            when_match = re.search(r"when\s+([^,.]+)", sentence)
            if when_match:
                conditions.append(when_match.group(1).strip())
        
        if conditions:
            return conditions[0][:100]  # Limit length
        
        return None
    
    def find_phase_transitions(
        self,
        transcripts: List[YouTubeTranscript],
    ) -> List[Dict[str, str]]:
        """Find phase transition points from transcripts"""
        transitions = []
        
        for transcript in transcripts:
            text = transcript.full_text.lower()
            
            # Look for phase transition language
            phase_patterns = [
                r"(?:phase|stage)\s*(\d+|2nd|second|third|final)",
                r"once you (?:reach|get to|hit)\s*(\d+%)",
                r"at\s*(\d+%)",
                r"(?:push|clear|enrage)\s*(?:at|time)",
            ]
            
            for pattern in phase_patterns:
                matches = re.finditer(pattern, text)
                for match in matches:
                    transitions.append({
                        "trigger": match.group(0),
                        "phase": match.group(1) if match.groups() else "",
                    })
        
        return transitions


class VariantMerger:
    """
    Merges variants from multiple sources:
    - Statistical variants (from FFLogs)
    - Transcript-based variants (from guides)
    """
    
    def merge_variants(
        self,
        statistical_variants: List[Dict[str, Any]],
        transcript_variants: List[GuideVariant],
        timeline_abilities: List[str],
    ) -> Dict[str, List[str]]:
        """
        Merge variants from different sources into a single map.
        
        Returns a dict mapping time points to list of variant ability names.
        """
        merged: Dict[str, List[str]] = {}
        
        # Add statistical variants
        for stat_var in statistical_variants:
            time_key = stat_var.get("time_key", "unknown")
            abilities = stat_var.get("abilities", [])
            
            if time_key not in merged:
                merged[time_key] = []
            
            for ability in abilities:
                if ability not in merged[time_key]:
                    merged[time_key].append(ability)
        
        # Add transcript variants
        for trans_var in transcript_variants:
            branch_point = trans_var.branch_point
            
            if branch_point not in merged:
                merged[branch_point] = []
            
            # Add alternate abilities
            for ability in trans_var.alternate_abilities:
                if ability not in merged[branch_point]:
                    merged[branch_point].append(ability)
        
        return merged


if __name__ == "__main__":
    # Test the analyzer
    analyzer = TranscriptVariantAnalyzer()
    
    # Test with sample abilities
    abilities = [
        "Frontal Cleave",
        "Tank Buster",
        "Raidwide",
        "Stack Marker",
        "Spread",
    ]
    
    # Would normally have transcripts here
    transcripts = []
    
    variants = analyzer.extract_variants(abilities, transcripts)
    
    print(f"Found {len(variants)} variants")
    for v in variants:
        print(f"  - {v.branch_point}: {v.description[:50]}...")
