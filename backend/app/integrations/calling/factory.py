from app.core.config import settings
from app.integrations.calling.base import CallingProvider
from app.integrations.calling.mock_provider import MockCallingProvider
from app.integrations.calling.voice_agent_provider import VoiceAgentCallingProvider


def get_calling_provider(force_mock: bool = False) -> CallingProvider:
    """
    Return the active calling provider.
    Fails closed to MockCallingProvider unless REAL_CALLS_ENABLED is explicitly True.
    """
    if not force_mock and settings.real_calls_enabled and settings.calling_provider == "voice_agent":
        return VoiceAgentCallingProvider()
    return MockCallingProvider()
