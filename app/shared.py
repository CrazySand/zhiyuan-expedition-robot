"""
共享资源：客户端实例、ASR 模型、回调工具函数等
"""
import asyncio
import logging
import shutil
import httpx
from funasr import AutoModel
from app.robot_api_client import RobotAPIClient
from app.config import (
    FUN_ASR_MODEL,
    CLOUD_EVENT_CALLBACK_URL,
    ENABLE_CLOUD_EVENT_CALLBACK,
    TTS_SECONDS_PER_CHAR,
)

# ============================= 客户端实例 =====================================

http_client = httpx.AsyncClient(timeout=60)
rac = RobotAPIClient(
    http_client, orin_mapped_ip="127.0.0.1", x86_ip="192.168.1.115")

# ============================= ASR 模型 =====================================

if not shutil.which("ffmpeg"):
    raise Exception("未检测到 ffmpeg")

asr_model = AutoModel(
    model=FUN_ASR_MODEL,
    disable_update=True,
    disable_pbar=True,
)


def recognize_audio(audio_path: str) -> str:
    """语音识别"""
    result = asr_model.generate(input=audio_path)
    return result[0].get("text", "") if result else ""

# ============================= 回调工具函数 =====================================


logger = logging.getLogger(__name__)


def log_callback_request(action: str, params: dict):
    """记录回调请求日志（用于调试）"""
    logger.info(
        f"回调请求 url={CLOUD_EVENT_CALLBACK_URL} action={action} params={params}")


async def send_callback_to_cloud(action: str, params: dict):
    """发送回调到中控（带开关控制）"""
    log_callback_request(action, params)
    if ENABLE_CLOUD_EVENT_CALLBACK:
        try:
            await http_client.post(
                CLOUD_EVENT_CALLBACK_URL,
                json={"action": action, "params": params},
            )
        except Exception as e:
            logging.warning(f"回调中控失败 action={action}: {e}")


async def tts_finished_callback_delayed(trace_id: str, text: str):
    """根据文本长度 sleep 后回调中控：tts 任务完成"""
    duration = max(1.0, len(text) * TTS_SECONDS_PER_CHAR)
    await asyncio.sleep(duration)
    await send_callback_to_cloud("ttsFinished", {"trace_id": trace_id})


# ============================= 导航任务轮询 =====================================

_NAV_POLL_INTERVAL = 5
_NAV_TERMINAL_STATES = ("PncServiceState_SUCCESS", "PncServiceState_FAILED")


async def poll_nav_task_until_done(task_id: str):
    """后台轮询导航任务状态，结束时回调中控并退出"""
    while True:
        await asyncio.sleep(_NAV_POLL_INTERVAL)
        try:
            result = await rac.get_navi_task_status(task_id)
        except Exception as e:
            logging.warning(f"轮询导航任务状态失败 task_id={task_id}: {e}")
            return
        state = result.get("state")
        if state in _NAV_TERMINAL_STATES:
            await send_callback_to_cloud(
                "navTaskFinished",
                {"task_id": task_id, "state": state},
            )
            return
