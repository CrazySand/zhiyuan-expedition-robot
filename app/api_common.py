"""
通用接口：将现有所有可编排的 API 收敛为单一入口 POST /api/common
请求体: { "action": "动作名", "params": { ... } }
Webhooks（人脸回调、ASR 音频上传）仍保留独立路径，不在此通用入口内
"""
from typing import Any, Awaitable, Callable

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# 复用 api 中的机器人客户端，避免重复初始化
from app.api import rac

router = APIRouter(prefix="/api")


class CommonRequestBody(BaseModel):
    """通用接口请求体"""
    action: str = Field(..., description="动作标识，如 tts.play、asr.start")
    params: dict[str, Any] = Field(default_factory=dict, description="该动作所需参数")


# ---------------------------------------------------------------------------
# 支持的 action 列表（用于文档与 GET /api/common/actions）
# ---------------------------------------------------------------------------
COMMON_ACTIONS = [
    {"action": "tts.play", "params": {"text": "string, 必填, 1~200 字"}, "desc": "发起 TTS 播报"},
    {"action": "tts.stop", "params": {}, "desc": "打断当前 TTS 播报"},
    {"action": "tts.status", "params": {"trace_id": "string, 必填"}, "desc": "查询 TTS 播报状态"},
    {"action": "tts.volume.get", "params": {}, "desc": "获取当前音量"},
    {"action": "tts.volume.set", "params": {"audio_volume": "int, 0~70"}, "desc": "设置音量"},
    {"action": "agent.properties.set", "params": {"mode": "only_voice|voice_face|normal"}, "desc": "设置交互模式并重启 agent"},
    {"action": "agent.properties.get", "params": {}, "desc": "查询交互模式"},
    {"action": "face_recognition.cloud_db", "params": {}, "desc": "获取云端人脸库信息"},
    {"action": "face_recognition.start", "params": {}, "desc": "启动人脸识别程序"},
    {"action": "face_recognition.stop", "params": {}, "desc": "停止人脸识别程序"},
    {"action": "face_recognition.status", "params": {}, "desc": "获取人脸识别进程状态"},
    {"action": "asr.start", "params": {}, "desc": "启动 ASR 程序"},
    {"action": "asr.stop", "params": {}, "desc": "停止 ASR 程序"},
    {"action": "asr.status", "params": {}, "desc": "获取 ASR 进程状态"},
]


def _ok(data: Any = None) -> dict:
    return {"code": 0, "msg": "操作成功", "data": data}


def _err(code: int, msg: str) -> dict:
    return {"code": code, "msg": msg, "data": None}


# ---------------------------------------------------------------------------
# 各 action 的处理器（与 api.py 中逻辑一一对应）
# ---------------------------------------------------------------------------

async def _tts_play(params: dict) -> dict:
    text = params.get("text")
    if not text or not isinstance(text, str):
        return _err(400, "缺少参数或 text 无效")
    if len(text) < 1 or len(text) > 200:
        return _err(400, "text 长度需在 1~200 之间")
    result = await rac.play_tts(text)
    return _ok({"trace_id": result["trace_id"]})


async def _tts_stop(params: dict) -> dict:
    await rac.stop_tts()
    return _ok()


async def _tts_status(params: dict) -> dict:
    trace_id = params.get("trace_id")
    if not trace_id or not isinstance(trace_id, str):
        return _err(400, "缺少参数 trace_id")
    if len(trace_id) < 1 or len(trace_id) > 100:
        return _err(400, "trace_id 长度需在 1~100 之间")
    result = await rac.get_audio_status(trace_id)
    return _ok({"tts_status": result["tts_status"]["tts_status"]})


async def _tts_volume_get(params: dict) -> dict:
    result = await rac.get_audio_volume()
    return _ok({"audio_volume": result["audio_volume"]})


async def _tts_volume_set(params: dict) -> dict:
    v = params.get("audio_volume")
    if v is None:
        return _err(400, "缺少参数 audio_volume")
    try:
        vol = int(v)
    except (TypeError, ValueError):
        return _err(400, "audio_volume 须为整数")
    if vol < 0 or vol > 70:
        return _err(400, "audio_volume 须在 0~70 之间")
    await rac.set_audio_volume(vol)
    return _ok()


async def _agent_properties_set(params: dict) -> dict:
    mode = params.get("mode")
    if mode not in ("only_voice", "voice_face", "normal"):
        return _err(400, "mode 须为 only_voice | voice_face | normal")
    await rac.set_agent_properties(mode)
    await rac.agent_mode_reboot()
    return _ok()


async def _agent_properties_get(params: dict) -> dict:
    result = await rac.get_agent_properties()
    mode = result["contents"]["properties"]["2"]
    return _ok({"mode": mode})


async def _face_recognition_cloud_db(params: dict) -> dict:
    result = await rac.get_cloud_face_db_info()
    return result if isinstance(result, dict) and "code" in result else _ok(result)


async def _face_recognition_start(params: dict) -> dict:
    result = await rac.start_face_recognition()
    return result if isinstance(result, dict) and "code" in result else _ok(result)


async def _face_recognition_stop(params: dict) -> dict:
    result = await rac.stop_face_recognition()
    return result if isinstance(result, dict) and "code" in result else _ok()


async def _face_recognition_status(params: dict) -> dict:
    result = await rac.get_face_recognition_status()
    return result if isinstance(result, dict) and "code" in result else _ok(result)


async def _asr_start(params: dict) -> dict:
    result = await rac.start_asr()
    return result if isinstance(result, dict) and "code" in result else _ok(result)


async def _asr_stop(params: dict) -> dict:
    result = await rac.stop_asr()
    return result if isinstance(result, dict) and "code" in result else _ok()


async def _asr_status(params: dict) -> dict:
    result = await rac.get_asr_status()
    return result if isinstance(result, dict) and "code" in result else _ok(result)


# action -> 异步处理器
ACTION_HANDLERS: dict[str, Callable[[dict], Awaitable[dict]]] = {
    "tts.play": _tts_play,
    "tts.stop": _tts_stop,
    "tts.status": _tts_status,
    "tts.volume.get": _tts_volume_get,
    "tts.volume.set": _tts_volume_set,
    "agent.properties.set": _agent_properties_set,
    "agent.properties.get": _agent_properties_get,
    "face_recognition.cloud_db": _face_recognition_cloud_db,
    "face_recognition.start": _face_recognition_start,
    "face_recognition.stop": _face_recognition_stop,
    "face_recognition.status": _face_recognition_status,
    "asr.start": _asr_start,
    "asr.stop": _asr_stop,
    "asr.status": _asr_status,
}


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------

@router.get("/common/actions")
async def list_common_actions():
    """列出通用接口支持的所有 action 及参数说明"""
    return _ok(COMMON_ACTIONS)


@router.post("/common")
async def common_invoke(body: CommonRequestBody):
    """
    通用接口：根据 action 执行对应逻辑，统一返回 { code, msg, data }
    """
    action = (body.action or "").strip()
    if not action:
        return _err(400, "action 不能为空")
    handler = ACTION_HANDLERS.get(action)
    if handler is None:
        return _err(400, f"不支持的 action: {action}，可调用 GET /api/common/actions 查看列表")
    try:
        return await handler(body.params or {})
    except HTTPException:
        raise
    except Exception as e:
        return _err(500, str(e))
