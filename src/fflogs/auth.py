import os
import requests
from typing import Optional
from .cache import CacheManager
from .env import load_project_env

TOKEN_URL = "https://www.fflogs.com/oauth/token"

class AuthManager:
    def __init__(self, client_id: Optional[str] = None,
                 client_secret: Optional[str] = None,
                 cache: Optional[CacheManager] = None):
        load_project_env()
        self.client_id = client_id or os.environ.get("FFLOGS_CLIENT_ID", "")
        self.client_secret = client_secret or os.environ.get("FFLOGS_CLIENT_SECRET", "")
        self.cache = cache or CacheManager()

    def get_token(self) -> str:
        cached = self.cache.load_token()
        if cached:
            return cached

        response = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        data = response.json()
        self.cache.save_token(data["access_token"], data["expires_in"])
        return data["access_token"]
