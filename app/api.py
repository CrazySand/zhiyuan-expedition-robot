from typing import Literal

from fastapi import APIRouter, Body, Query

from app.services import tts_service, agent_control_service, app_robot_service

router = APIRouter(prefix="/api")

# ============================= TTS ========================================

@router.post("/play_tts")
async def play_tts(text: str = Body(..., min_length=1, max_length=200, description="播报文本内容", embed=True)):
    """TTS 播报"""
    result = await tts_service.play_tts(text)
    trace_id = result["trace_id"]
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "trace_id": trace_id
        }
    }


@router.post("/stop_tts")
async def stop_tts():
    """TTS 打断"""
    result = await tts_service.stop_tts()
    return {
        "code": 0,
        "msg": "success",
        "data": None
    }


@router.get("/get_audio_status")
async def get_audio_status(trace_id: str = Query(..., description="播报 id", min_length=1, max_length=100)):
    """TTS 播报状态查询"""
    result = await tts_service.get_audio_status(trace_id)
    tts_status = result["tts_status"]["tts_status"]
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "tts_status": tts_status
        }
    }


@router.get("/get_audio_volume")
async def get_audio_volume():
    """获取当前音量大小"""
    result = await tts_service.get_audio_volume()
    audio_volume = result["audio_volume"]
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "audio_volume": audio_volume
        }
    }


@router.post("/set_audio_volume")
async def set_audio_volume(audio_volume: int = Body(..., description="音量大小", ge=0, le=70, embed=True)):
    """设置音量大小"""
    result = await tts_service.set_audio_volume(audio_volume)
    return {
        "code": 0,
        "msg": "success",
        "data": None
    }


# ============================= Agent Control ========================================

@router.post("/set_agent_properties")
async def set_agent_properties(mode: Literal["only_voice", "voice_face", "normal"] = Body(..., description="交互运行模式", embed=True)):
    """设置机器人交互运行模式"""
    result = await agent_control_service.set_agent_properties(mode)
    result = await app_robot_service.agent_mode_reboot()
    return {
        "code": 0,
        "msg": "success",
        "data": None
    }


@router.get("/get_agent_properties")
async def get_agent_properties():
    """查询机器人交互运行模式"""
    result = await agent_control_service.get_agent_properties()
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "mode": result["contents"]["properties"]["2"]
        }
    }

# ============================== Face ========================================

@router.get("/cloud-face-db-info")
async def get_cloud_face_db_info():
    """获取云端人脸数据库信息"""
    user_info = await app_robot_service.get_cloud_face_db_info()
    return {
        "code": 0,
        "msg": "success",
        "data": user_info
    }