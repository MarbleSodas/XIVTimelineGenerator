"""
Description Generator Atomic Agent

Uses LLM to generate detailed descriptions for boss actions based on:
- Cactbot timeline entries
- YouTube guide transcripts
- FFLogs damage data (optional)

This creates much more accurate and useful descriptions than the
rule-based approach in the original TimelineBuilderAgent.
"""
from typing import List, Optional, Dict, Any
from pydantic import Field

from atomic_agents import AtomicAgent, AgentConfig, BaseIOSchema
from atomic_agents.context import SystemPromptGenerator

from schemas.youtube_schemas import (
    YouTubeTranscript,
    GuideActionDescription,
    GuideAnalysisInput,
    GuideAnalysisOutput,
    ActionDescriptionRequest,
    ActionDescriptionResponse,
)
from schemas.cactbot_schemas import CactbotTimelineEntry


SYSTEM_PROMPT = SystemPromptGenerator(
    background=[
        "You are an expert FFXIV raid guide analyst.",
        "You analyze boss mechanics from raid guides and timeline data.",
        "You understand all mechanics: tank busters, AoEs, positionals, markers, etc.",
    ],
    steps=[
        "1. Analyze the transcript for mentions of each boss ability",
        "2. Extract positioning, timing, and mitigation requirements",
        "3. Identify which role (tank/healer/DPS) needs to prioritize each ability",
        "4. Note common mistakes and how to avoid them",
        "5. Generate clear, concise descriptions",
    ],
    output_instructions=[
        "Return detailed descriptions for each ability",
        "Focus on actionable information players can use",
        "Use plain language accessible to intermediate players",
        "Include specific positioning instructions when mentioned",
    ],
)


class TimelineEntryForAnalysis(BaseIOSchema):
    """Timeline entry with additional context"""
    time: float
    name: str
    original_name: Optional[str] = None
    hit_count: Optional[int] = None


class TranscriptContext(BaseIOSchema):
    """Relevant transcript snippets for analysis"""
    video_title: str
    channel: str
    relevant_snippets: List[str] = Field(
        default_factory=list,
        description="Transcript sections mentioning this ability",
    )


class SingleActionAnalysisInput(BaseIOSchema):
    """Input for analyzing a single action"""
    ability_name: str
    timeline_entry: Optional[TimelineEntryForAnalysis] = None
    transcript_contexts: List[TranscriptContext] = Field(
        default_factory=list,
    )
    damage_info: Optional[Dict[str, Any]] = None


class SingleActionAnalysisOutput(BaseIOSchema):
    """Output for a single action analysis"""
    ability_name: str
    description: str
    mechanics: List[str] = Field(default_factory=list)
    mitigation_tips: List[str] = Field(default_factory=list)
    positioning: Optional[str] = None
    timing_notes: Optional[str] = None
    common_failures: List[str] = Field(default_factory=list)
    is_tank_ability: bool = False
    is_healer_ability: bool = False
    is_dps_ability: bool = False
    priority_role: Optional[str] = None
    is_mechanic_ability: bool = True


class FullAnalysisInput(BaseIOSchema):
    """Input for full timeline analysis"""
    boss_id: str
    boss_name: str
    timeline_entries: List[TimelineEntryForAnalysis]
    transcripts: List[Dict[str, Any]]  # Simplified transcript format
    damage_info: Optional[Dict[str, Any]] = None


class FullAnalysisOutput(BaseIOSchema):
    """Output from full analysis"""
    boss_id: str
    action_descriptions: List[SingleActionAnalysisOutput]
    key_mechanics: List[str]
    phase_summary: Dict[str, str]
    variants: List[Dict[str, Any]] = Field(default_factory=list)


class DescriptionGeneratorAgent:
    """
    Atomic agent for generating detailed action descriptions from transcripts.
    
    Can work in two modes:
    1. Single action mode - analyze one ability at a time
    2. Full analysis mode - analyze entire timeline at once
    
    Uses LLM for natural language understanding and generation.
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
    
    def run_single_action(
        self,
        input_data: SingleActionAnalysisInput,
    ) -> SingleActionAnalysisOutput:
        """Analyze a single action with LLM"""
        if not self._agent:
            # Fallback to rule-based if no LLM
            return self._rule_based_description(input_data)
        
        try:
            result = self._agent.run(input_data)
            return result
        except Exception as e:
            # Fallback on error
            return self._rule_based_description(input_data)
    
    def run_full_analysis(
        self,
        input_data: FullAnalysisInput,
    ) -> FullAnalysisOutput:
        """Analyze entire timeline at once"""
        if not self._agent:
            # Return empty analysis
            return FullAnalysisOutput(
                boss_id=input_data.boss_id,
                action_descriptions=[],
                key_mechanics=[],
                phase_summary={},
            )
        
        try:
            result = self._agent.run(input_data)
            return result
        except Exception as e:
            # Return empty on error
            return FullAnalysisOutput(
                boss_id=input_data.boss_id,
                action_descriptions=[],
                key_mechanics=[],
                phase_summary={},
            )
    
    def _rule_based_description(
        self,
        input_data: SingleActionAnalysisInput,
    ) -> SingleActionAnalysisOutput:
        """
        Fallback rule-based description when LLM is unavailable.
        
        This uses simple keyword matching to generate basic descriptions.
        """
        name = input_data.ability_name.lower()
        description_parts = []
        mechanics = []
        mitigation_tips = []
        is_tank = False
        is_healer = False
        is_dps = False
        priority_role = None
        
        # Tank buster detection
        if any(kw in name for kw in ["tank", "bus", "tether", "tackle", "chomp"]):
            is_tank = True
            priority_role = "tank"
            description_parts.append("Tank buster")
            mechanics.append("Tank swap may be required")
            mitigation_tips.append("Use cooldowns")
            mitigation_tips.append("Position boss away from party")
        
        # Raidwide detection
        elif any(kw in name for kw in ["raid", "party", "wide", "everyone", "all"]):
            description_parts.append("Raidwide damage")
            is_healer = True
            priority_role = "healer"
            mitigation_tips.append("Healers should prepare AoE heals")
        
        # AoE detection
        elif any(kw in name for kw in ["aoe", "cone", "frontal", "circle", "donut", "raidwide"]):
            description_parts.append("AoE damage")
            mechanics.append("Find safe spot")
            if "frontal" in name:
                positioning = "Stand behind or to the sides"
            elif "circle" in name:
                positioning = "Move out of circle"
            elif "donut" in name:
                positioning = "Stand in the donut (outside the circle)"
        
        # Stack/spread markers
        if "stack" in name:
            description_parts.append("Stack marker")
            mechanics.append("Party members stack together")
            is_dps = True
            is_healer = True
        elif "spread" in name:
            description_parts.append("Spread marker")
            mechanics.append("Spread out from other players")
            is_dps = True
        
        # Positionals
        if "rear" in name or "flank" in name or "front" in name:
            mechanics.append("Positional")
            if "rear" in name:
                positioning = "Stand behind the boss"
            elif "flank" in name:
                positioning = "Stand at boss's flank (side)"
        
        # Default
        if not description_parts:
            description_parts.append("Damage mechanic")
        
        description = ". ".join(description_parts)
        if mitigation_tips:
            description += ". " + " ".join(mitigation_tips)
        
        return SingleActionAnalysisOutput(
            ability_name=input_data.ability_name,
            description=description,
            mechanics=mechanics,
            mitigation_tips=mitigation_tips,
            positioning=positioning,
            is_tank_ability=is_tank,
            is_healer_ability=is_healer,
            is_dps_ability=is_dps,
            priority_role=priority_role,
            is_mechanic_ability=True,
        )
    
    def generate_descriptions_batch(
        self,
        timeline_entries: List[CactbotTimelineEntry],
        transcripts: List[YouTubeTranscript],
        damage_info: Optional[Dict[str, Any]] = None,
    ) -> List[SingleActionAnalysisOutput]:
        """
        Generate descriptions for multiple actions.
        
        Groups actions and processes them efficiently.
        """
        # Build transcript context map
        transcript_context_map: Dict[str, List[TranscriptContext]] = {}
        
        for transcript in transcripts:
            # Find mentions of each ability in transcript
            for entry in timeline_entries:
                ability_name = entry.name.lower()
                
                # Search transcript for this ability
                snippets = self._find_relevant_snippets(
                    transcript.full_text,
                    ability_name,
                )
                
                if snippets:
                    if ability_name not in transcript_context_map:
                        transcript_context_map[ability_name] = []
                    
                    transcript_context_map[ability_name].append(
                        TranscriptContext(
                            video_title=transcript.video_metadata.title,
                            channel=transcript.video_metadata.channel,
                            relevant_snippets=snippets,
                        )
                    )
        
        # Generate descriptions
        results = []
        for entry in timeline_entries:
            context = transcript_context_map.get(entry.name.lower(), [])
            
            input_data = SingleActionAnalysisInput(
                ability_name=entry.name,
                timeline_entry=TimelineEntryForAnalysis(
                    time=entry.time,
                    name=entry.name,
                    original_name=entry.original_name,
                    hit_count=entry.hit_count,
                ) if entry else None,
                transcript_contexts=context,
                damage_info=damage_info,
            )
            
            result = self.run_single_action(input_data)
            results.append(result)
        
        return results
    
    def _find_relevant_snippets(
        self,
        transcript_text: str,
        ability_name: str,
        max_snippets: int = 3,
    ) -> List[str]:
        """Find relevant transcript snippets for an ability"""
        import re
        
        snippets = []
        ability_lower = ability_name.lower()
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', transcript_text)
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            # Check if sentence mentions this ability
            if ability_lower in sentence_lower:
                cleaned = sentence.strip()
                if cleaned:
                    snippets.append(cleaned)
        
        return snippets[:max_snippets]


class TranscriptDescriptionGenerator:
    """
    Simplified description generator using transcripts directly.
    
    This version doesn't require atomic agents framework,
    just uses LLM directly for generation.
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    def generate_description(
        self,
        ability_name: str,
        transcript_snippets: List[str],
    ) -> str:
        """
        Generate a description for an ability based on transcript snippets.
        
        Uses LLM to create a concise, accurate description.
        """
        if not self.llm_client:
            return self._simple_description(ability_name)
        
        if not transcript_snippets:
            return self._simple_description(ability_name)
        
        # Build prompt
        prompt = self._build_description_prompt(ability_name, transcript_snippets)
        
        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an FFXIV raid guide expert."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=200,
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception:
            return self._simple_description(ability_name)
    
    def _build_description_prompt(
        self,
        ability_name: str,
        snippets: List[str],
    ) -> str:
        """Build prompt for description generation"""
        snippets_text = "\n".join(f"- {s}" for s in snippets[:5])
        
        return f"""Based on the following transcript excerpts about "{ability_name}" from an FFXIV raid guide, provide a clear, concise description of this mechanic:

{snippets_text}

Provide a 1-2 sentence description that explains:
1. What the mechanic does
2. How players should respond (positioning, mitigation, etc.)

Format: Just the description, no bullet points."""
    
    def _simple_description(self, ability_name: str) -> str:
        """Generate simple description without LLM"""
        name_lower = ability_name.lower()
        
        if "tank" in name_lower or "buster" in name_lower:
            return "Tank buster - requires cooldowns and positioning"
        elif "raidwide" in name_lower or "party" in name_lower:
            return "Raidwide damage - healers prepare AoE heals"
        elif "stack" in name_lower:
            return "Stack marker - party stacks together"
        elif "spread" in name_lower:
            return "Spread marker - spread out from others"
        elif "frontal" in name_lower:
            return "Frontal attack - avoid front of boss"
        else:
            return "Damage mechanic - respond appropriately"
