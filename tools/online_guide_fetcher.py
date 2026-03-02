"""
Online Guide Fetcher Tool

Fetches and parses raid guide articles from websites.
"""
import re
from typing import List, Optional, Dict, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential


class OnlineGuideError(Exception):
    """Custom exception for online guide errors"""
    pass


class OnlineGuideFetcher:
    """
    Fetches raid guide articles from websites.
    
    Supports:
    - Direct URL fetching
    - HTML parsing
    - Multiple guide sources
    - Caching
    """
    
    TRUSTED_SOURCES = {
        "hardcoregamer.com": 1.0,
        "gamerescape.com": 1.0,
        "fflogs.com": 0.9,
        "thebalanceffxiv.com": 1.0,
        "mizteq.com": 0.9,
        "xenorus.com": 0.8,
        "icy-veins.com": 1.0,
        "icyveins.com": 1.0,
    }
    
    FALLBACK_SOURCES = [
        "icy-veins.com",
        "icyveins.com",
    ]
    
    def __init__(self, http_client: Optional[httpx.Client] = None):
        self._http_client = http_client
        self._cache: Dict[str, str] = {}
    
    @property
    def http_client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=30.0, follow_redirects=True)
        return self._http_client
    
    def is_trusted_source(self, url: str) -> bool:
        """Check if URL is from a trusted source"""
        for domain in self.TRUSTED_SOURCES:
            if domain in url.lower():
                return True
        return False
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def fetch_guide(
        self,
        url: str,
        force_fetch: bool = False,
    ) -> str:
        """
        Fetch guide article HTML.
        
        Args:
            url: Guide article URL
            force_fetch: Skip cache
            
        Returns:
            Raw HTML content
            
        Raises:
            OnlineGuideError: If guide cannot be fetched
        """
        cache_key = url
        if not force_fetch and cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            response = self.http_client.get(url)
            response.raise_for_status()
            
            html = response.text
            
            self._cache[cache_key] = html
            return html
            
        except httpx.HTTPStatusError as e:
            raise OnlineGuideError(f"HTTP error: {e.response.status_code}")
        except httpx.RequestError as e:
            raise OnlineGuideError(f"Request error: {e}")
        except Exception as e:
            raise OnlineGuideError(f"Failed to fetch guide: {e}")
    
    def fetch_guide_text(
        self,
        url: str,
    ) -> str:
        """
        Fetch guide and extract main text content.
        
        Uses basic HTML parsing to extract readable text.
        """
        html = self.fetch_guide(url)
        return self._extract_text_from_html(html)
    
    def _extract_text_from_html(self, html: str) -> str:
        """Extract readable text from HTML"""
        import html as html_module
        
        text = html
        
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<nav[^>]*>.*?</nav>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<footer[^>]*>.*?</footer>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<header[^>]*>.*?</header>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</h[1-6]>', '\n\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<li[^>]*>', '\n- ', text, flags=re.IGNORECASE)
        
        text = re.sub(r'<[^>]+>', '', text)
        
        text = html_module.unescape(text)
        
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()
        
        return text
    
    def close(self):
        """Close HTTP client"""
        if self._http_client:
            self._http_client.close()


def fetch_online_guide(url: str) -> str:
    """
    Convenience function to fetch online guide.
    
    Example:
        >>> text = fetch_online_guide("https://hardcoregamer.com/ffxiv-dawntrail-aac-heavyweight-m3-savage-guide/")
        >>> print(text[:500])
    """
    fetcher = OnlineGuideFetcher()
    try:
        return fetcher.fetch_guide_text(url)
    finally:
        fetcher.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = "https://hardcoregamer.com/ffxiv-dawntrail-aac-heavyweight-m3-savage-guide/"
    
    print(f"Fetching guide from: {url}")
    
    fetcher = OnlineGuideFetcher()
    
    try:
        text = fetcher.fetch_guide_text(url)
        print(f"Got {len(text)} characters")
        print("\nFirst 1000 characters:")
        print(text[:1000])
        
    except OnlineGuideError as e:
        print(f"Error: {e}")
    finally:
        fetcher.close()
