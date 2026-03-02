"""
YouTube Transcript Fetcher Tool

Fetches transcripts from YouTube videos for raid guides.
"""
import re
from typing import List, Optional, Dict, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

# Try to import youtube-transcript-api, install if needed
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        TranscriptsDisabled,
        NoTranscriptFound,
        VideoUnavailable,
        InvalidVideoId,
        CouldNotRetrieveTranscript,
    )
    YOUTUBE_TRANSCRIPT_AVAILABLE = True
except ImportError:
    YOUTUBE_TRANSCRIPT_AVAILABLE = False


class YouTubeTranscriptError(Exception):
    """Custom exception for YouTube transcript errors"""
    pass


class YouTubeTranscriptFetcher:
    """
    Fetches transcripts from YouTube videos.
    
    Supports:
    - Direct video ID input
    - YouTube URL parsing (various formats)
    - Multiple language fallbacks
    - Caching to avoid re-fetching
    """
    
    # YouTube URL patterns
    URL_PATTERNS = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
        r"youtube\.com/v/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
    ]
    
    # Known FFXIV raid guide channels
    FFXIV_GUIDE_CHANNELS = [
        "Mister Never",
        "Tanuki Tanque",
        "Mizzteq",
        "Hydaelyn",
        "Aetherflow",
        " Wesk Alber",
        "Okami",
        "The Deep Dive",
        "Hector's FFXIV",
        "Carrot",
        "Natsucord",
    ]
    
    def __init__(self, http_client: Optional[httpx.Client] = None):
        self._http_client = http_client
        self._cache: Dict[str, List[Dict[str, Any]]] = {}
    
    @property
    def http_client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=30.0, follow_redirects=True)
        return self._http_client
    
    def extract_video_id(self, url_or_id: str) -> Optional[str]:
        """Extract video ID from URL or return if already an ID"""
        # Already just an ID
        if re.match(r"^[a-zA-Z0-9_-]{11}$", url_or_id):
            return url_or_id
        
        # Try each pattern
        for pattern in self.URL_PATTERNS:
            match = re.search(pattern, url_or_id)
            if match:
                return match.group(1)
        
        return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def fetch_transcript(
        self,
        video_id_or_url: str,
        languages: Optional[List[str]] = None,
        force_fetch: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Fetch transcript from a YouTube video.
        
        Args:
            video_id_or_url: YouTube video ID or URL
            languages: List of language codes to try (e.g., ['en', 'en-US'])
            force_fetch: Skip cache and force fetch
            
        Returns:
            List of transcript segments with 'text', 'start', 'duration'
            
        Raises:
            YouTubeTranscriptError: If transcript cannot be fetched
        """
        if not YOUTUBE_TRANSCRIPT_AVAILABLE:
            raise YouTubeTranscriptError(
                "youtube-transcript-api not installed. "
                "Install with: pip install youtube-transcript-api"
            )
        
        video_id = self.extract_video_id(video_id_or_url)
        if not video_id:
            raise YouTubeTranscriptError(f"Invalid YouTube URL or video ID: {video_id_or_url}")
        
        # Check cache
        cache_key = video_id
        if not force_fetch and cache_key in self._cache:
            return self._cache[cache_key]
        
        # Default languages
        if languages is None:
            languages = ["en", "en-US", "en-GB"]
        
        api = YouTubeTranscriptApi()
        
        # Try each language
        last_error = None
        for lang in languages:
            try:
                transcript = api.fetch(video_id, languages=[lang])
                segments = [
                    {
                        "text": segment.text,
                        "start": segment.start,
                        "duration": segment.duration,
                    }
                    for segment in transcript
                ]
                
                # Cache the result
                self._cache[cache_key] = segments
                return segments
                
            except NoTranscriptFound:
                last_error = f"No transcript found for language: {lang}"
                continue
            except TranscriptsDisabled:
                raise YouTubeTranscriptError(f"Transcripts disabled for video: {video_id}")
            except (VideoUnavailable, InvalidVideoId):
                raise YouTubeTranscriptError(f"Video not found: {video_id}")
            except CouldNotRetrieveTranscript as e:
                last_error = str(e)
                continue
            except Exception as e:
                last_error = str(e)
                continue
        
        # Try to get any available transcript
        try:
            transcript = api.list_transcripts(video_id)
            # Get all available transcripts
            available = []
            for t in transcript:
                available.append(t.language_code)
            
            # Try with any available language
            if available:
                transcript = api.fetch(video_id, languages=[available[0]])
                segments = [
                    {
                        "text": segment.text,
                        "start": segment.start,
                        "duration": segment.duration,
                    }
                    for segment in transcript
                ]
                self._cache[cache_key] = segments
                return segments
                
        except Exception:
            pass
        
        raise YouTubeTranscriptError(f"Could not fetch transcript: {last_error}")
    
    def fetch_transcript_text(
        self,
        video_id_or_url: str,
        languages: Optional[List[str]] = None,
    ) -> str:
        """
        Fetch transcript as plain text.
        
        Args:
            video_id_or_url: YouTube video ID or URL
            languages: List of language codes to try
            
        Returns:
            Full transcript as plain text
        """
        segments = self.fetch_transcript(video_id_or_url, languages)
        return " ".join(seg["text"] for seg in segments)
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    def get_video_metadata(self, video_id_or_url: str) -> Dict[str, Any]:
        """
        Get video metadata (title, channel, description).
        
        Uses YouTube oEmbed API for basic metadata.
        """
        video_id = self.extract_video_id(video_id_or_url)
        if not video_id:
            raise YouTubeTranscriptError(f"Invalid YouTube URL or video ID: {video_id_or_url}")
        
        try:
            # Use oEmbed API for basic info
            url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            response = self.http_client.get(url)
            response.raise_for_status()
            data = response.json()
            
            return {
                "video_id": video_id,
                "title": data.get("title", ""),
                "channel": data.get("author_name", ""),
                "thumbnail": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            }
        except Exception as e:
            return {
                "video_id": video_id,
                "title": "Unknown",
                "channel": "Unknown",
                "error": str(e),
            }
    
    def search_videos(
        self,
        query: str,
        max_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search for YouTube videos (requires API key or scraping).
        
        Note: This requires YouTube Data API key for proper search.
        Without API key, returns empty list.
        """
        # This would need YouTube Data API for proper implementation
        # For now, return empty and let caller handle discovery separately
        return []
    
    def is_valid_video(self, video_id_or_url: str) -> bool:
        """Check if a video ID/URL is valid and exists"""
        video_id = self.extract_video_id(video_id_or_url)
        if not video_id:
            return False
        
        try:
            metadata = self.get_video_metadata(video_id)
            return "error" not in metadata
        except Exception:
            return False
    
    def close(self):
        """Close HTTP client"""
        if self._http_client:
            self._http_client.close()


# Standalone function for simple usage
def fetch_youtube_transcript(
    video_id_or_url: str,
    languages: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Convenience function to fetch YouTube transcript.
    
    Example:
        >>> transcript = fetch_youtube_transcript("https://www.youtube.com/watch?v=abc123")
        >>> print(transcript[0])
        {'text': 'Hello everyone', 'start': 0.0, 'duration': 2.5}
    """
    fetcher = YouTubeTranscriptFetcher()
    try:
        return fetcher.fetch_transcript(video_id_or_url, languages)
    finally:
        fetcher.close()


if __name__ == "__main__":
    # Test with a sample video
    import sys
    
    if len(sys.argv) > 1:
        video_url = sys.argv[1]
    else:
        # Default test video (M7S guide if available)
        video_url = "dQw4w9WgXcQ"  # Never gonna give you up - always has captions
    
    fetcher = YouTubeTranscriptFetcher()
    
    try:
        print(f"Fetching transcript from: {video_url}")
        transcript = fetcher.fetch_transcript(video_url)
        print(f"Got {len(transcript)} segments")
        
        if transcript:
            print("\nFirst 3 segments:")
            for seg in transcript[:3]:
                print(f"  [{seg['start']:.1f}s] {seg['text']}")
                
    except YouTubeTranscriptError as e:
        print(f"Error: {e}")
    finally:
        fetcher.close()
