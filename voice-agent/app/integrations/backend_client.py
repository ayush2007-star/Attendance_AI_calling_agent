import requests
from app.config.settings import settings


class BackendClient:
    def __init__(self):
        self.base_url = settings.backend_base_url.rstrip("/")
        self.access_token = None

    def login(self, username: str, password: str) -> str:
        response = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            json={
                "username": username,
                "password": password,
            },
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()
        self.access_token = data["access_token"]

        return self.access_token

    def _headers(self) -> dict:
        if not self.access_token:
            return {}

        return {
            "Authorization": f"Bearer {self.access_token}"
        }

    def get(self, path: str):
        response = requests.get(
            f"{self.base_url}{path}",
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def health_check(self) -> bool:
        response = requests.get(
            f"{self.base_url}/health",
            timeout=5,
        )
        response.raise_for_status()
        return True