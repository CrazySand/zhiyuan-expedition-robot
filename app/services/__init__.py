import httpx

from app.services.tts_service import TTSService
from app.services.agent_control_service import AgentControlService
from app.services.app_robot_service import AppRobotService

__all__ = [
    "tts_service",
    "agent_control_service",
    "app_robot_service"
]

http_client = httpx.AsyncClient(timeout=60)
tts_service = TTSService(http_client)
agent_control_service = AgentControlService(http_client)
app_robot_service = AppRobotService(http_client)

