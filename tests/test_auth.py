import os
from unittest.mock import patch, MagicMock

def test_client_credentials_flow(monkeypatch):
    os.environ["FFLOGS_CLIENT_ID"] = "test_id"
    os.environ["FFLOGS_CLIENT_SECRET"] = "test_secret"

    from fflogs.auth import AuthManager
    am = AuthManager(client_id="test_id", client_secret="test_secret")
    am.cache.load_token = MagicMock(return_value=None)
    am.cache.save_token = MagicMock()

    mock_response = MagicMock()
    mock_response.json.return_value = {"access_token": "abc", "expires_in": 3600}
    mock_response.raise_for_status = MagicMock()

    with patch("fflogs.auth.requests.post", return_value=mock_response):
        token = am.get_token()
        assert token == "abc"
