from typing import Optional
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class FFLogsConfig(BaseModel):
    client_id: str = ""
    client_secret: str = ""
    api_url: str = "https://www.fflogs.com/api/v2"
    auth_url: str = "https://www.fflogs.com/oauth/token"
    redirect_uri: str = "http://localhost:8080/callback"


class LLMConfig(BaseModel):
    provider: str = "minimax"
    api_key: str = ""
    base_url: str = "https://api.minimax.io/v1"
    model: str = "MiniMax-M2.5"
    temperature: float = 0.0
    max_tokens: int = 4096


class CactbotConfig(BaseModel):
    base_url: str = "https://raw.githubusercontent.com/OverlayPlugin/cactbot/main"
    
    boss_mapping: dict[str, dict] = {
        # Dawntrail Savage (7.x) - The Arcadion
        # Zone 62: AAC Light-Heavyweight
        "r1s": {
            "name": "Arcadion - AAC Light-heavyweight M1 (Savage)",
            "short_name": "Black Cat",
            "timeline_path": "ui/raidboss/data/07-dt/raid/r1s.txt",
            "zone_id": 62,
            "encounter_id": 93,
            "mitplan_id": "black-cat",
            "guide_urls": [
                "https://www.icy-veins.com/ffxiv/aac-light-heavyweight-m1-savage-raid-guide",
            ],
        },
        "r2s": {
            "name": "Arcadion - AAC Light-heavyweight M2 (Savage)",
            "short_name": "Honey B. Lovely",
            "timeline_path": "ui/raidboss/data/07-dt/raid/r2s.txt",
            "zone_id": 62,
            "encounter_id": 94,
            "mitplan_id": "honey-b-lovely",
            "guide_urls": [
                "https://www.icy-veins.com/ffxiv/aac-light-heavyweight-m2-savage-raid-guide",
            ],
        },
        "r3s": {
            "name": "Arcadion - AAC Light-heavyweight M3 (Savage)",
            "short_name": "Brute Bomber",
            "timeline_path": "ui/raidboss/data/07-dt/raid/r3s.txt",
            "zone_id": 62,
            "encounter_id": 95,
            "mitplan_id": "brute-bomber",
            "guide_urls": [
                "https://www.icy-veins.com/ffxiv/aac-light-heavyweight-m3-savage-raid-guide",
            ],
        },
        "r4s": {
            "name": "Arcadion - AAC Light-heavyweight M4 (Savage)",
            "short_name": "Wicked Thunder",
            "timeline_path": "ui/raidboss/data/07-dt/raid/r4s.txt",
            "zone_id": 62,
            "encounter_id": 96,
            "mitplan_id": "wicked-thunder",
            "guide_urls": [
                "https://www.icy-veins.com/ffxiv/aac-light-heavyweight-m4-savage-raid-guide",
            ],
        },
        "r5s": {
            "name": "AAC Cruiserweight M1 (Savage)",
            "short_name": "Dancing Green",
            "timeline_path": "ui/raidboss/data/07-dt/raid/r5s.txt",
            "zone_id": 68,
            "encounter_id": 97,
            "mitplan_id": "dancing-green",
            "guide_urls": [
                "https://www.icy-veins.com/ffxiv/aac-cruiserweight-m1-savage-raid-guide",
            ],
        },
        "r6s": {
            "name": "AAC Cruiserweight M2 (Savage)",
            "short_name": "Sugar Riot",
            "timeline_path": "ui/raidboss/data/07-dt/raid/r6s.txt",
            "zone_id": 68,
            "encounter_id": 98,
            "mitplan_id": "sugar-riot",
            "guide_urls": [
                "https://www.icy-veins.com/ffxiv/aac-cruiserweight-m2-savage-raid-guide",
            ],
        },
        "r7s": {
            "name": "AAC Cruiserweight M3 (Savage)",
            "short_name": "Brute Abombinator",
            "timeline_path": "ui/raidboss/data/07-dt/raid/r7s.txt",
            "zone_id": 68,
            "encounter_id": 99,
            "mitplan_id": "brute-abombinator",
            "guide_urls": [
                "https://www.icy-veins.com/ffxiv/aac-cruiserweight-m3-savage-raid-guide",
            ],
        },
        "r8s": {
            "name": "AAC Cruiserweight M4 (Savage)",
            "short_name": "Howling Blade",
            "timeline_path": "ui/raidboss/data/07-dt/raid/r8s.txt",
            "zone_id": 68,
            "encounter_id": 100,
            "mitplan_id": "howling-blade",
            "guide_urls": [
                "https://www.icy-veins.com/ffxiv/aac-cruiserweight-m4-savage-raid-guide",
            ],
        },
        "r9s": {
            "name": "AAC Heavyweight M1 (Savage)",
            "short_name": "Vamp Fatale",
            "timeline_path": "ui/raidboss/data/07-dt/raid/r9s.txt",
            "zone_id": 73,
            "encounter_id": 101,
            "mitplan_id": "vamp-fatale",
            "guide_urls": [
                "https://www.icy-veins.com/ffxiv/aac-heavyweight-m1-savage-raid-guide",
            ],
        },
        "r10s": {
            "name": "AAC Heavyweight M2 (Savage)",
            "short_name": "Red Hot",
            "timeline_path": "ui/raidboss/data/07-dt/raid/r10s.txt",
            "zone_id": 73,
            "encounter_id": 102,
            "mitplan_id": "red-hot",
            "guide_urls": [
                "https://www.icy-veins.com/ffxiv/aac-heavyweight-m2-savage-raid-guide",
            ],
        },
        "r11s": {
            "name": "AAC Heavyweight M3 (Savage)",
            "short_name": "The Tyrant",
            "timeline_path": "ui/raidboss/data/07-dt/raid/r11s.txt",
            "zone_id": 73,
            "encounter_id": 103,
            "mitplan_id": "the-tyrant",
            "guide_urls": [
                "https://hardcoregamer.com/ffxiv-dawntrail-aac-heavyweight-m3-savage-guide/",
                "https://www.icy-veins.com/ffxiv/aac-heavyweight-m3-savage-raid-guide",
            ],
        },
    }


class OutputConfig(BaseModel):
    base_path: str = "src/data/bosses"
    format: str = "mitplan"


class ScraperConfig(BaseSettings):
    fflogs_client_id: str = ""
    fflogs_client_secret: str = ""
    youtube_api_key: str = ""
    include_dodgeable: bool = False
    default_report_count: int = 30
    min_fight_duration: int = 120
    
    llm_provider: str = "minimax"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.minimax.io/v1"
    llm_model: str = "MiniMax-M2.5"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4096
    
    fflogs: FFLogsConfig = FFLogsConfig()
    cactbot: CactbotConfig = CactbotConfig()
    output: OutputConfig = OutputConfig()
    llm: LLMConfig = LLMConfig()
    
    class Config:
        env_prefix = "MITPLAN_"
        env_file = ".env"
        extra = "ignore"
    
    def get_boss_config(self, boss_id: str) -> Optional[dict]:
        return self.cactbot.boss_mapping.get(boss_id)
    
    def get_llm_client(self):
        """Get the instructor-wrapped client for atomic agents."""
        import os
        
        provider = self.llm_provider.lower()
        
        api_key = self.llm_api_key or os.environ.get("MINIMAX_API_KEY", "")
        if not api_key:
            raise ValueError("LLM API key not set. Set MITPLAN_LLM_API_KEY or MINIMAX_API_KEY")
        
        base_url = self.llm_base_url or os.environ.get("MINIMAX_BASE_URL", "https://api.minimax.io/v1")
        
        if provider == "minimax" or provider == "openai":
            import instructor
            from openai import OpenAI
            
            openai_client = OpenAI(
                api_key=api_key,
                base_url=base_url,
            )
            
            return instructor.from_openai(openai_client, mode=instructor.Mode.MD_JSON)
        elif provider == "anthropic":
            try:
                from anthropic import Anthropic
                return Anthropic(api_key=api_key)
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
        elif provider == "ollama":
            import instructor
            from openai import OpenAI
            openai_client = OpenAI(
                api_key="ollama",
                base_url="http://localhost:11434/v1",
            )
            return instructor.from_openai(openai_client, mode=instructor.Mode.MD_JSON)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
    
    def get_raw_client(self):
        """Get the raw (unwrapped) OpenAI client for direct API calls."""
        import os
        
        provider = self.llm_provider.lower()
        
        api_key = self.llm_api_key or os.environ.get("MINIMAX_API_KEY", "")
        if not api_key:
            raise ValueError("LLM API key not set. Set MITPLAN_LLM_API_KEY or MINIMAX_API_KEY")
        
        base_url = self.llm_base_url or os.environ.get("MINIMAX_BASE_URL", "https://api.minimax.io/v1")
        
        if provider == "minimax" or provider == "openai" or provider == "ollama":
            from openai import OpenAI
            
            if provider == "ollama":
                base_url = "http://localhost:11434/v1"
                api_key = "ollama"
            
            return OpenAI(
                api_key=api_key,
                base_url=base_url,
            )
        elif provider == "anthropic":
            try:
                from anthropic import Anthropic
                return Anthropic(api_key=api_key)
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")


config = ScraperConfig()
