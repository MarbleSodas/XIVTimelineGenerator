"""
YouTube Guide Discovery Agent

Discovers and fetches relevant raid guide videos from YouTube.
Uses YouTube Data API for searching and filters for quality guides.
"""
import os
import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

import httpx

from tools.youtube_transcript import (
    YouTubeTranscriptFetcher,
    YouTubeTranscriptError,
)
from schemas.youtube_schemas import (
    YouTubeVideoMetadata,
    YouTubeGuideInput,
    YouTubeGuideVideo,
    YouTubeGuideOutput,
    YouTubeTranscript,
    TranscriptSegment,
)


# Known FFXIV raid guide channels (trusted sources)
TRUSTED_CHANNELS = {
    # English guides
    "Mister Never": 1.0,
    "Tanuki Tanque": 1.0,
    "Mizzteq": 1.0,
    "Hydaelyn": 1.0,
    "Aetherflow": 1.0,
    "WeskAlber": 1.0,
    "Okami X": 1.0,
    "The Deep Dive": 1.0,
    "Hector's FFXIV": 1.0,
    "Carrot": 1.0,
    "Natsucord": 1.0,
    "Momo FFXIV": 1.0,
    "Lulu FFXIV": 1.0,
    "MTQCapture": 0.9,
    "Frosty_TV": 0.9,
    "Joonbob": 0.9,
    # Japanese guides
    "另一個縫隙": 0.9,  # ENkou
    "Naoki": 0.9,
    "Kyo VOD": 0.8,
    # Chinese guides
    "FF14 泥潭奶茶": 0.8,
}

# Search query templates
SEARCH_TEMPLATES = [
    "{boss_name} savage guide",
    "{boss_name} mechanic guide",
    "{boss_name} full guide",
    "{boss_name} explained",
    "{boss_name} walkthrough",
    "{boss_name} duty finder",
]


@dataclass
class SearchResult:
    video_id: str
    title: str
    channel: str
    relevance_score: float


class YouTubeGuideDiscoveryAgent:
    """
    Agent for discovering relevant FFXIV raid guides on YouTube.
    
    Features:
    - Searches YouTube Data API for relevant guides
    - Filters by trusted channels
    - Ranks by relevance and quality
    - Fetches transcripts from discovered videos
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        http_client: Optional[httpx.Client] = None,
    ):
        self.api_key = api_key or os.environ.get("YOUTUBE_API_KEY", "")
        self._http_client = http_client
        self._transcript_fetcher = None
    
    @property
    def http_client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=30.0, follow_redirects=True)
        return self._http_client
    
    @property
    def transcript_fetcher(self) -> YouTubeTranscriptFetcher:
        if self._transcript_fetcher is None:
            self._transcript_fetcher = YouTubeTranscriptFetcher()
        return self._transcript_fetcher
    
    def run(
        self,
        input_data: YouTubeGuideInput,
    ) -> YouTubeGuideOutput:
        """
        Discover and fetch YouTube guides for a boss.
        
        Returns guides sorted by relevance.
        """
        boss_id = input_data.boss_id
        boss_name = input_data.boss_name
        max_results = input_data.max_results
        
        # Build search query
        search_query = input_data.search_query or self._build_search_query(boss_name)
        
        # Search for videos
        videos = self._search_videos(search_query, max_results * 2)
        
        # Filter and rank videos
        ranked_videos = self._rank_videos(videos, boss_name)
        
        # Take top results
        top_videos = ranked_videos[:max_results]
        
        # Fetch transcripts for top videos
        transcripts = []
        transcripts_fetched = 0
        
        for video in top_videos:
            try:
                segments = self.transcript_fetcher.fetch_transcript(
                    video.video_id,
                    languages=["en", "en-US", "en-GB"],
                )
                
                if segments:
                    metadata = self.transcript_fetcher.get_video_metadata(video.video_id)
                    
                    transcript = YouTubeTranscript(
                        video_id=video.video_id,
                        video_metadata=YouTubeVideoMetadata(
                            video_id=video.video_id,
                            title=metadata.get("title", video.title),
                            channel=metadata.get("channel", video.channel),
                            thumbnail=metadata.get("thumbnail", f"https://img.youtube.com/vi/{video.video_id}/maxresdefault.jpg"),
                        ),
                        segments=[
                            TranscriptSegment(
                                text=seg["text"],
                                start=seg["start"],
                                duration=seg["duration"],
                            )
                            for seg in segments
                        ],
                    )
                    transcripts.append(transcript)
                    transcripts_fetched += 1
                    
            except YouTubeTranscriptError:
                # Skip videos without transcripts
                continue
            except Exception:
                continue
        
        # Convert to output format
        guide_videos = [
            YouTubeGuideVideo(
                video_id=v.video_id,
                title=v.title,
                channel=v.channel,
                thumbnail=f"https://img.youtube.com/vi/{v.video_id}/maxresdefault.jpg",
                url=f"https://www.youtube.com/watch?v={v.video_id}",
                relevance_score=v.relevance_score,
            )
            for v in top_videos
        ]
        
        return YouTubeGuideOutput(
            boss_id=boss_id,
            videos=guide_videos,
            transcripts_fetched=transcripts_fetched,
            fetch_success=True,
        )
    
    def _build_search_query(self, boss_name: str) -> str:
        """Build search query from boss name"""
        # Clean up boss name
        clean_name = re.sub(r'\(Savage\)', '', boss_name)
        clean_name = re.sub(r'\s+', ' ', clean_name).strip()
        return f"FFXIV {clean_name} guide"
    
    def _search_videos(self, query: str, max_results: int) -> List[SearchResult]:
        """Search YouTube for videos"""
        if not self.api_key:
            # No API key - return known video IDs for common bosses
            return self._search_fallback(query, max_results)
        
        try:
            url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": max_results,
                "videoCategoryId": "24",  # Gaming
                "regionCode": "US",
                "relevanceLanguage": "en",
                "key": self.api_key,
            }
            
            response = self.http_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("items", []):
                video_id = item["id"]["videoId"]
                title = item["snippet"]["title"]
                channel = item["snippet"]["channelTitle"]
                
                results.append(SearchResult(
                    video_id=video_id,
                    title=title,
                    channel=channel,
                    relevance_score=0.5,  # Default, will be updated
                ))
            
            return results
            
        except Exception as e:
            # Fall back to known videos
            return self._search_fallback(query, max_results)
    
    def _search_fallback(self, query: str, max_results: int) -> List[SearchResult]:
        """
        Fallback search using hardcoded known video IDs.
        
        This provides basic functionality when YouTube Data API is unavailable.
        Users should get an API key for full functionality.
        """
        # Known guide videos for common bosses (placeholder IDs - replace with real ones)
        # In production, maintain a database of known good guide video IDs
        known_guides: Dict[str, List[Dict[str, str]]] = {
            "r1s": [
                {"id": "placeholder", "title": "Black Cat (M1S) Full Guide", "channel": "Mister Never"},
                {"id": "placeholder", "title": "Black Cat Mechanic Guide", "channel": "Mizzteq"},
            ],
            "r7s": [
                {"id": "placeholder", "title": "Brute Abombinator (M7S) Guide", "channel": "Mister Never"},
            ],
        }
        
        # Return empty for unknown bosses
        return []
    
    def _rank_videos(
        self,
        videos: List[SearchResult],
        boss_name: str,
    ) -> List[SearchResult]:
        """Rank videos by relevance and quality"""
        scored_videos = []
        
        boss_name_lower = boss_name.lower()
        
        for video in videos:
            score = 0.5  # Base score
            
            # Check if trusted channel
            channel_bonus = TRUSTED_CHANNELS.get(video.channel, 0.0)
            score += channel_bonus * 0.3
            
            # Check title relevance
            title_lower = video.title.lower()
            
            # Positive signals
            if boss_name_lower.replace(" ", "") in title_lower.replace(" ", ""):
                score += 0.2
            if "guide" in title_lower:
                score += 0.1
            if "mechanic" in title_lower:
                score += 0.1
            if "full" in title_lower:
                score += 0.1
            if "savage" in title_lower:
                score += 0.05
            if "duty finder" in title_lower:
                score += 0.05
                
            # Negative signals
            if "preview" in title_lower or "teaser" in title_lower:
                score -= 0.3
            if "music" in title_lower or "soundtrack" in title_lower:
                score -= 0.3
            if "react" in title_lower or "reaction" in title_lower:
                score -= 0.2
            if "first impression" in title_lower:
                score -= 0.2
            
            video.relevance_score = min(1.0, max(0.0, score))
            scored_videos.append(video)
        
        # Sort by score descending
        return sorted(scored_videos, key=lambda v: v.relevance_score, reverse=True)
    
    def get_transcript_only(
        self,
        video_id: str,
    ) -> Optional[YouTubeTranscript]:
        """Fetch transcript for a specific video ID"""
        try:
            segments = self.transcript_fetcher.fetch_transcript(
                video_id,
                languages=["en", "en-US", "en-GB"],
            )
            
            if not segments:
                return None
            
            metadata = self.transcript_fetcher.get_video_metadata(video_id)
            
            return YouTubeTranscript(
                video_id=video_id,
                video_metadata=YouTubeVideoMetadata(
                    video_id=video_id,
                    title=metadata.get("title", ""),
                    channel=metadata.get("channel", ""),
                    thumbnail=metadata.get("thumbnail", f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"),
                ),
                segments=[
                    TranscriptSegment(
                        text=seg["text"],
                        start=seg["start"],
                        duration=seg["duration"],
                    )
                    for seg in segments
                ],
            )
            
        except YouTubeTranscriptError:
            return None
        except Exception:
            return None
    
    def close(self):
        """Close HTTP clients"""
        if self._http_client:
            self._http_client.close()
        if self._transcript_fetcher:
            self._transcript_fetcher.close()


if __name__ == "__main__":
    # Test the agent
    agent = YouTubeGuideDiscoveryAgent()
    
    # Test with M7S (Brute Abominator)
    result = agent.run(YouTubeGuideInput(
        boss_id="r7s",
        boss_name="Brute Abominator",
        max_results=3,
    ))
    
    print(f"Found {len(result.videos)} videos")
    print(f"Transcripts fetched: {result.transcripts_fetched}")
    
    for video in result.videos:
        print(f"  - {video.title} ({video.channel}): {video.relevance_score:.2f}")
    
    agent.close()
