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
from app.shared import merge_cloud_db_with_local_images

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
    {"action": "face_recognition.cloud_db", "params": {}, "desc": "获取云端人脸库信息"},
    {"action": "face_recognition.start", "params": {}, "desc": "启动人脸识别程序"},
    {"action": "face_recognition.stop", "params": {}, "desc": "停止人脸识别程序"},
    {"action": "face_recognition.status", "params": {}, "desc": "获取人脸识别进程状态"},
    {"action": "asr.start", "params": {}, "desc": "启动 ASR 程序"},
    {"action": "asr.stop", "params": {}, "desc": "停止 ASR 程序"},
    {"action": "asr.status", "params": {}, "desc": "获取 ASR 进程状态"},
    {"action": "map.list", "params": {}, "desc": "获取地图列表（含当前工作地图）"},
    {"action": "map.detail", "params": {"map_id": "string"}, "desc": "获取地图详情（2D+拓扑点位）"},
    {"action": "nav.planning_to_goal", "params": {"task_id": "可选", "point_id": "int, 必填"}, "desc": "下发到点规划导航任务（使用当前工作地图）"},
    {"action": "nav.task_control", "params": {"action": "cancel|pause|resume", "task_id": "string"}, "desc": "取消/暂停/恢复导航任务"},
    {"action": "nav.status", "params": {"task_id": "可选，0 表示最近一次"}, "desc": "获取导航任务状态"},
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


async def _face_recognition_cloud_db(params: dict) -> dict:
    result = await rac.get_cloud_face_db_info()
    if not isinstance(result, dict) or "code" not in result:
        return _ok(result)
    return merge_cloud_db_with_local_images(result)


async def _face_recognition_start(params: dict) -> dict:
    current_agent_mode = (await rac.get_agent_properties()).get("contents", {}).get("properties", {}).get("2")
    if current_agent_mode not in ("voice_face", "normal"):
        return _err(400, "当前交互模式不是 voice_face 或 normal")
    result = await rac.start_face_recognition()
    return result if isinstance(result, dict) and "code" in result else _ok(result)


async def _face_recognition_stop(params: dict) -> dict:
    result = await rac.stop_face_recognition()
    return result if isinstance(result, dict) and "code" in result else _ok()


async def _face_recognition_status(params: dict) -> dict:
    result = await rac.get_face_recognition_status()
    return result if isinstance(result, dict) and "code" in result else _ok(result)


async def _asr_start(params: dict) -> dict:
    current_agent_mode = (await rac.get_agent_properties()).get("contents", {}).get("properties", {}).get("2")
    if current_agent_mode not in ("only_voice", "voice_face"):
        return _err(400, "当前交互模式不是 only_voice 或 voice_face")
    result = await rac.start_asr()
    return result if isinstance(result, dict) and "code" in result else _ok(result)


async def _asr_stop(params: dict) -> dict:
    result = await rac.stop_asr()
    return result if isinstance(result, dict) and "code" in result else _ok()


async def _asr_status(params: dict) -> dict:
    result = await rac.get_asr_status()
    return result if isinstance(result, dict) and "code" in result else _ok(result)


async def _map_list(params: dict) -> dict:
    stored = await rac.get_stored_map_names()
    map_lists = stored.get("data", {}).get("map_lists", [])
    current_result = await rac.get_current_working_map()
    current_working_map_id = current_result.get("data", {}).get("map_id", "")
    current_working_map_name = ""
    for m in map_lists:
        if m.get("map_id") == current_working_map_id:
            current_working_map_name = m.get("map_name", "")
            break
    return _ok({
        "current_working_map_id": current_working_map_id,
        "current_working_map_name": current_working_map_name,
        "map_lists": map_lists,
    })


async def _map_detail(params: dict) -> dict:
    map_id = params.get("map_id")
    if not map_id:
        return _err(400, "缺少参数 map_id")
    stored = await rac.get_stored_map_names()
    map_ids = [m.get("map_id") for m in stored.get("data", {}).get("map_lists", [])]
    if map_id not in map_ids:
        return _err(400, "地图ID不存在")
    whole_map_result = await rac.get_2d_whole_map(map_id)
    topo_result = await rac.get_topo_msgs(map_id)
    whole_data = whole_map_result.get("data", whole_map_result)
    topo_data = topo_result.get("data", topo_result) or {}
    points = [{"point_id": p.get("point_id"), "point_name": p.get("name")} for p in topo_data.get("points", [])]
    return _ok({"map_id": whole_data.get("map_id"), "map_name": whole_data.get("map_name"), "points": points})


async def _nav_planning_to_goal(params: dict) -> dict:
    point_id = params.get("point_id")
    if point_id is None:
        return _err(400, "缺少参数 point_id")
    try:
        point_id = int(point_id)
    except (TypeError, ValueError):
        return _err(400, "point_id 须为整数")
    current_result = await rac.get_current_working_map()
    current_working_map_id = current_result.get("data", {}).get("map_id")
    task_id = params.get("task_id", 0)
    result = await rac.planning_navi_to_goal(task_id=task_id or 0, map_id=current_working_map_id, target_id=point_id)
    if result.get("state") != "CommonState_SUCCESS":
        return _err(400, "地图ID或目标点ID不正确")
    return _ok({"task_id": result.get("task_id")})


async def _nav_task_control(params: dict) -> dict:
    action = params.get("action")
    task_id = params.get("task_id")
    if action not in ("cancel", "pause", "resume"):
        return _err(400, "action 须为 cancel | pause | resume")
    if not task_id:
        return _err(400, "缺少参数 task_id")
    fns = {"cancel": rac.cancel_navi_task, "pause": rac.pause_navi_task, "resume": rac.resume_navi_task}
    try:
        result = await fns[action](task_id)
        if result.get("state") == "CommonState_SUCCESS":
            return _ok()
        return _err(400, "任务不存在、已结束或 task_id 不匹配")
    except Exception:
        return _err(400, "任务不存在、已结束或 task_id 不匹配")


async def _nav_status(params: dict) -> dict:
    task_id = params.get("task_id", 0)
    try:
        result = await rac.get_navi_task_status(task_id)
        return _ok({"task_id": result.get("task_id"), "state": result.get("state")})
    except Exception:
        return _err(400, "任务不存在或已结束")


# action -> 异步处理器
ACTION_HANDLERS: dict[str, Callable[[dict], Awaitable[dict]]] = {
    "tts.play": _tts_play,
    "tts.stop": _tts_stop,
    "tts.status": _tts_status,
    "tts.volume.get": _tts_volume_get,
    "tts.volume.set": _tts_volume_set,
    "face_recognition.cloud_db": _face_recognition_cloud_db,
    "face_recognition.start": _face_recognition_start,
    "face_recognition.stop": _face_recognition_stop,
    "face_recognition.status": _face_recognition_status,
    "asr.start": _asr_start,
    "asr.stop": _asr_stop,
    "asr.status": _asr_status,
    "map.list": _map_list,
    "map.detail": _map_detail,
    "nav.planning_to_goal": _nav_planning_to_goal,
    "nav.task_control": _nav_task_control,
    "nav.status": _nav_status,
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
