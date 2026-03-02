"""
Schemas for YouTube transcript and guide analysis.

Defines data structures for:
- YouTube video metadata
- Transcript segments
- Guide analysis results
- Action descriptions
- Variant information from guides
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class YouTubeVideoMetadata(BaseModel):
    """YouTube video basic information"""
    video_id: str
    title: str
    channel: str
    thumbnail: Optional[str] = None
    duration: Optional[int] = None  # seconds
    upload_date: Optional[str] = None


class TranscriptSegment(BaseModel):
    """Single segment of a transcript"""
    text: str
    start: float  # seconds
    duration: float  # seconds
    
    @property
    def end(self) -> float:
        return self.start + self.duration


class YouTubeTranscript(BaseModel):
    """Full transcript from a YouTube video"""
    video_id: str
    video_metadata: YouTubeVideoMetadata
    segments: List[TranscriptSegment]
    language: str = "en"
    fetch_success: bool = True
    error_message: Optional[str] = None
    
    @property
    def full_text(self) -> str:
        """Get full transcript as plain text"""
        return " ".join(seg.text for seg in self.segments)
    
    @property
    def segment_count(self) -> int:
        return len(self.segments)


class GuideActionDescription(BaseModel):
    """Detailed description for a boss action from guide analysis"""
    ability_name: str
    description: str = Field(..., description="Human-readable description of the mechanic")
    mechanics: List[str] = Field(default_factory=list, description="Key mechanics involved")
    mitigation_tips: List[str] = Field(default_factory=list, description="How to mitigate this ability")
    positioning: Optional[str] = Field(None, description="Recommended positioning")
    timing_notes: Optional[str] = Field(None, description="Timing notes from the guide")
    common_failures: List[str] = Field(default_factory=list, description="Common mistakes to avoid")
    is_tank_ability: bool = Field(False, description="Whether this is primarily a tank mechanic")
    is_healer_ability: bool = Field(False, description="Whether this is primarily a healer mechanic")
    is_dps_ability: bool = Field(False, description="Whether this is primarily a DPS mechanic")
    priority_role: Optional[str] = Field(None, description="Which role should prioritize this (tank/healer/dps)")


class GuideVariant(BaseModel):
    """A variant/alternative in the timeline from guide analysis"""
    variant_id: str
    branch_point: str = Field(..., description="When this variant branches (e.g., '90s')")
    trigger_condition: Optional[str] = Field(None, description="What triggers this variant")
    description: str = Field(..., description="Description of what happens in this variant")
    alternate_abilities: List[str] = Field(default_factory=list, description="Abilities used in this variant")
    strategy_notes: str = Field("", description="Strategy notes for handling this variant")


class GuideAnalysisInput(BaseModel):
    """Input for guide analysis"""
    boss_id: str
    boss_name: str
    cactbot_timeline: List[Dict[str, Any]] = Field(..., description="Timeline entries from Cactbot")
    transcripts: List[YouTubeTranscript] = Field(default_factory=list, description="Guide transcripts")


class GuideAnalysisOutput(BaseModel):
    """Output from guide analysis"""
    boss_id: str
    boss_name: str
    action_descriptions: List[GuideActionDescription] = Field(default_factory=list)
    variants: List[GuideVariant] = Field(default_factory=list)
    key_mechanics: List[str] = Field(default_factory=list, description="Overall key mechanics of the fight")
    phase_summary: Dict[str, str] = Field(default_factory=dict, description="Summary of each phase")
    analysis_success: bool = True
    transcripts_analyzed: int = 0
    error_message: Optional[str] = None


class ActionDescriptionRequest(BaseModel):
    """Request to generate description for a specific action"""
    ability_name: str
    cactbot_timeline_entry: Optional[Dict[str, Any]] = None
    transcript_context: List[str] = Field(default_factory=list, description="Relevant transcript snippets")
    damage_info: Optional[Dict[str, Any]] = None  # From FFLogs


class ActionDescriptionResponse(BaseModel):
    """Response with generated description"""
    ability_name: str
    description: str
    mechanics: List[str] = []
    mitigation_tips: List[str] = []
    positioning: Optional[str] = None
    is_mechanic_ability: bool = False  # True if it's a real mechanic, not just damage


class YouTubeGuideInput(BaseModel):
    """Input for YouTube guide discovery"""
    boss_id: str
    boss_name: str
    search_query: Optional[str] = None
    max_results: int = Field(5, description="Maximum number of videos to fetch")


class YouTubeGuideVideo(BaseModel):
    """A discovered YouTube video for a guide"""
    video_id: str
    title: str
    channel: str
    thumbnail: str
    url: str
    relevance_score: float = Field(0.0, description="How relevant this guide is (0-1)")


class YouTubeGuideOutput(BaseModel):
    """Output from YouTube guide discovery"""
    boss_id: str
    videos: List[YouTubeGuideVideo] = Field(default_factory=list)
    transcripts_fetched: int = 0
    fetch_success: bool = True
    error_message: Optional[str] = None


# Combined input/output for the full pipeline
class TranscriptEnrichedAction(BaseModel):
    """Action enriched with transcript-based description"""
    # From Cactbot/FFLogs
    time: float
    name: str
    id: str
    unmitigated_damage: Optional[str] = None
    damage_type: Optional[str] = None
    importance: str = "medium"
    is_tank_buster: bool = False
    is_dual_tank_buster: bool = False
    hit_count: Optional[int] = None
    
    # From transcript analysis
    transcript_description: Optional[str] = None
    mechanics: List[str] = []
    mitigation_tips: List[str] = []
    positioning: Optional[str] = None
    common_failures: List[str] = []
    priority_role: Optional[str] = None
    
    # From variant analysis
    variants: List[str] = []
    is_variant_point: bool = False
    variant_branches: List[Dict[str, Any]] = []


class TimelineEnrichmentInput(BaseModel):
    """Input for timeline enrichment pipeline"""
    boss_id: str
    boss_name: str
    base_timeline: List[Dict[str, Any]]  # From existing timeline builder
    youtube_video_ids: List[str] = Field(default_factory=list)
    include_variants: bool = True


class TimelineEnrichmentOutput(BaseModel):
    """Output from timeline enrichment"""
    boss_id: str
    enriched_actions: List[TranscriptEnrichedAction]
    variants: List[GuideVariant]
    phase_summary: Dict[str, str]
    transcripts_used: int
    analysis_success: bool = True
    error_message: Optional[str] = None
