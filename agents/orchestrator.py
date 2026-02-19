from typing import Optional, List, Dict, Any, Set
import time as time_module
import os

from schemas.cactbot_schemas import CactbotTimelineInput, CactbotTimelineEntry
from schemas.fflogs_schemas import FFLogsReportInput
from schemas.timeline_schemas import (
    TimelineGenerationRequest,
    TimelineGenerationResult,
    TimelineOutput,
    TimelineSummary,
)
from schemas.damage_schemas import DamageEvent
from schemas.youtube_schemas import YouTubeTranscript

from agents.cactbot_agent import CactbotTimelineAgent
from agents.fflogs_agent import FFLogsReportAgent
from agents.variant_detector_agent import TimelineVariantDetectorAgent
from agents.aggregator_agent import TimelineAggregatorAgent
from agents.timeline_builder_agent import TimelineBuilderAgent
from agents.transcript_enrichment_orchestrator import TranscriptEnrichmentOrchestrator

from config import config
from tools.statistics import normalize_action_name


class TimelineGenerationOrchestrator:
    """
    Orchestrator agent that coordinates all atomic agents into a pipeline.
    
    Pipeline:
    1. CactbotTimelineAgent - Fetch timeline from Cactbot (simple HTTP + regex, no LLM needed)
    2. FFLogsReportAgent - Discover and fetch reports from FFLogs (API client, no LLM needed)
    3. TimelineVariantDetectorAgent - Detect timeline variants (atomic agent with LLM)
    4. TimelineAggregatorAgent - Aggregate damage values (atomic agent with LLM)
    5. TranscriptEnrichmentOrchestrator - Enrich with YouTube descriptions (atomic agent with LLM)
    6. TimelineBuilderAgent - Build final output (atomic agent with LLM)
    """
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        llm_client=None,
        youtube_api_key: Optional[str] = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.llm_client = llm_client
        self.youtube_api_key = youtube_api_key or os.environ.get("YOUTUBE_API_KEY", "")
        
        if not llm_client:
            raise ValueError("LLM client is required for atomic agents")
        
        self.cactbot_agent = CactbotTimelineAgent()
        self.fflogs_agent = FFLogsReportAgent(client_id, client_secret)
        self.variant_detector = TimelineVariantDetectorAgent()
        self.aggregator = TimelineAggregatorAgent()
        self.builder = TimelineBuilderAgent()
        
        # Transcript enrichment (optional - can work without LLM for basic descriptions)
        self.transcript_orchestrator = None
        if self.youtube_api_key or True:  # Always init, works without API key
            try:
                raw_llm_client = config.get_raw_client()
                self.transcript_orchestrator = TranscriptEnrichmentOrchestrator(
                    llm_client=llm_client,
                    raw_llm_client=raw_llm_client,
                    model=config.llm_model,
                    youtube_api_key=self.youtube_api_key,
                )
            except Exception:
                pass
    
    def run(
        self,
        request: TimelineGenerationRequest,
    ) -> TimelineGenerationResult:
        """
        Execute the full timeline generation pipeline.
        """
        errors: List[str] = []
        warnings: List[str] = []
        
        boss_config = config.get_boss_config(request.boss_id)
        if not boss_config:
            return TimelineGenerationResult(
                success=False,
                timeline=None,
                summary=None,
                errors=[f"Unknown boss ID: {request.boss_id}"],
                warnings=[],
            )
        
        boss_name = request.boss_name or boss_config.get("name", request.boss_id)
        timeline_path = boss_config.get("timeline_path")
        encounter_id = boss_config.get("encounter_id")
        
        if not timeline_path:
            errors.append(f"No timeline path configured for {request.boss_id}")
        
        if not encounter_id:
            warnings.append("No encounter_id configured - will use provided report codes only")
        
        timeline_output = None
        
        try:
            cactbot_input = CactbotTimelineInput(
                boss_id=request.boss_id,
                timeline_path=timeline_path or "",
            )
            cactbot_result = self.cactbot_agent.run(cactbot_input)
            
            if not cactbot_result.fetch_success:
                warnings.append(
                    cactbot_result.error_message or "Cactbot timeline fetch failed"
                )
            
            timeline_entries = cactbot_result.timeline_entries
            
            # Build set of normalized ability names from cactbot timeline for early filtering
            cactbot_abilities: Set[str] = set()
            if timeline_entries:
                for entry in timeline_entries:
                    # Use name or base_name for matching
                    name_to_use = entry.base_name or entry.name
                    if name_to_use:
                        cactbot_abilities.add(normalize_action_name(name_to_use))
            
            fflogs_input = FFLogsReportInput(
                boss_id=request.boss_id,
                encounter_id=encounter_id,
                report_count=request.report_count,
                require_kill=True,
                min_fight_duration=120,
            )
            fflogs_result = self.fflogs_agent.run(fflogs_input)
            
            if not fflogs_result.fetch_success:
                warnings.append(
                    fflogs_result.error_message or "FFLogs report discovery failed"
                )
            
            report_codes = [r.code for r in fflogs_result.reports]
            
            all_events: List[DamageEvent] = []
            
            for report in fflogs_result.reports:
                for fight in report.fights:
                    # Must filter by encounter_id - report contains fights for all bosses
                    if not fight.kill:
                        continue
                    if encounter_id and fight.encounter_id != encounter_id:
                        continue
                    
                    try:
                        events = self._extract_events_from_fight(
                            report,
                            fight,
                            cactbot_abilities,
                        )
                        all_events.extend(events)
                    except Exception as e:
                        warnings.append(f"Failed to extract events from {report.code}: {e}")
            
            if not all_events and cactbot_result.fetch_success:
                warnings.append("No damage events extracted - using Cactbot timeline only")
            
            damage_events_by_report: Dict[str, List[DamageEvent]] = {}
            for event in all_events:
                if event.report_code not in damage_events_by_report:
                    damage_events_by_report[event.report_code] = []
                damage_events_by_report[event.report_code].append(event)
            
            variant_result = self.variant_detector.run(
                damage_events_by_report,
                timeline_entries,
            )
            
            aggregation_result = self.aggregator.run(
                all_events,
                timeline_entries,
            )
            
            # Step 6: Optional - Enrich with YouTube transcript descriptions
            youtube_descriptions: Dict[str, str] = {}
            
            if request.enable_transcript_enrichment and self.transcript_orchestrator:
                try:
                    # Convert variant_points to dict format for compatibility
                    statistical_variants = []
                    if hasattr(variant_result, 'variant_points'):
                        for vp in variant_result.variant_points:
                            statistical_variants.append({
                                "branch_point_time": vp.branch_point_time,
                                "branch_point_name": vp.branch_point_name,
                                "branches": [
                                    {
                                        "action_sequence": b.action_sequence,
                                        "is_default": b.is_default,
                                    }
                                    for b in vp.branches
                                ],
                            })
                    
                    from schemas.youtube_schemas import TimelineEnrichmentInput
                    
                    enrichment_input = TimelineEnrichmentInput(
                        boss_id=request.boss_id,
                        boss_name=boss_name,
                        base_timeline=[],
                        youtube_video_ids=request.youtube_video_ids,
                        include_variants=True,
                    )
                    
                    # Run enrichment
                    enrichment_output = self.transcript_orchestrator.run(
                        enrichment_input,
                        timeline_entries,
                        aggregation_result.aggregated_actions,
                        statistical_variants,
                    )
                    
                    for action in enrichment_output.enriched_actions:
                        if action.transcript_description:
                            name_lower = action.name.lower()
                            youtube_descriptions[name_lower] = action.transcript_description
                            youtube_descriptions[name_lower.replace(" ", "_")] = action.transcript_description
                            youtube_descriptions["".join(c for c in name_lower if c.isalnum())] = action.transcript_description
                    
                    if enrichment_output.transcripts_used > 0:
                        warnings.append(f"Enriched {len(youtube_descriptions)} actions with YouTube descriptions")
                        
                except Exception as e:
                    warnings.append(f"Transcript enrichment failed: {e}")
            
            timeline_output = self.builder.run(
                aggregation_result.aggregated_actions,
                variant_result,
                request.boss_id,
                boss_name,
                fflogs_report_codes=report_codes,
                youtube_descriptions=youtube_descriptions,
            )
            
            if request.output_path:
                self.builder.write_output(timeline_output, request.output_path)
            
            return TimelineGenerationResult(
                success=True,
                timeline=timeline_output,
                summary=timeline_output.summary,
                errors=errors,
                warnings=warnings,
                output_path=request.output_path,
            )
            
        except Exception as e:
            return TimelineGenerationResult(
                success=False,
                timeline=timeline_output,
                summary=None,
                errors=errors + [str(e)],
                warnings=warnings,
            )
        
        finally:
            self.close()
    
    def _extract_events_from_fight(
        self,
        report,
        fight,
        cactbot_abilities: Optional[Set[str]] = None,
    ) -> List[DamageEvent]:
        events: List[DamageEvent] = []
        
        try:
            raw_events = self.fflogs_agent.get_fight_events(
                report.code,
                fight.fight_id,
                fight.start_time,
                fight.end_time,
                "DamageTaken",
            )
            
            ability_lookup = self.fflogs_agent.create_ability_lookup(report)
            
            # Get player actor IDs from master data (filter by target being player, not source being boss)
            player_ids = []
            if report.master_data:
                for actor in report.master_data.actors:
                    if actor.actor_type == "Friendly":
                        player_ids.append(actor.id)
            
            for raw_event in raw_events:
                if raw_event.get("type") != "damage":
                    continue
                
                # Only include events where target is a player (not boss)
                if player_ids and raw_event.get("targetID") not in player_ids:
                    continue
                
                unmitigated = raw_event.get("unmitigatedAmount", 0) or 0
                if unmitigated < 5000:
                    continue
                
                ability_id = raw_event.get("abilityGameID") or raw_event.get("ability", {}).get("guid", 0)
                ability_name = (
                    ability_lookup.get(ability_id) or
                    raw_event.get("ability", {}).get("name") or
                    f"Unknown_{ability_id}"
                )
                
                if self._is_auto_attack(ability_name):
                    continue
                
                # Filter using cactbot timeline as guide if available
                if cactbot_abilities:
                    normalized_name = normalize_action_name(ability_name)
                    if normalized_name not in cactbot_abilities:
                        continue
                
                relative_time = (raw_event["timestamp"] - fight.start_time) / 1000
                if relative_time <= 0:
                    continue
                
                hit_type = raw_event.get("hitType", 0)
                damage_type = self._determine_damage_type(hit_type)
                
                events.append(
                    DamageEvent(
                        timestamp=relative_time,
                        ability_name=ability_name,
                        ability_id=ability_id,
                        unmitigated_damage=unmitigated,
                        damage_type=damage_type,
                        target_id=raw_event.get("targetID", 0),
                        source_id=raw_event.get("sourceID", 0),
                        report_code=report.code,
                    )
                )
        except Exception:
            pass
        
        return events
    
    def _is_auto_attack(self, name: str) -> bool:
        return name.lower() in ("attack", "auto-attack", "auto attack", "shot")
    
    def _determine_damage_type(self, hit_type: int) -> str:
        if hit_type in (1, 2):
            return "physical"
        elif hit_type in (4, 8, 9, 10):
            return "magical"
        return "magical"
    
    def close(self):
        self.cactbot_agent.close()
        self.fflogs_agent.close()
        if self.transcript_orchestrator:
            self.transcript_orchestrator.close()
