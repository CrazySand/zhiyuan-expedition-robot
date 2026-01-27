from typing import Literal

from fastapi import APIRouter, Body, Query

from app.services import tts_service, agent_control_service, app_robot_service

router = APIRouter(prefix="/api")

# ============================= TTS ========================================

@router.post("/tts/play-tts")
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


@router.post("/tts/stop-tts")
async def stop_tts():
    """TTS 打断"""
    result = await tts_service.stop_tts()
    return {
        "code": 0,
        "msg": "success",
        "data": None
    }


@router.get("/tts/get-audio-status")
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


@router.get("/tts/get-audio-volume")
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


@router.post("/tts/set-audio-volume")
async def set_audio_volume(audio_volume: int = Body(..., description="音量大小", ge=0, le=70, embed=True)):
    """设置音量大小"""
    result = await tts_service.set_audio_volume(audio_volume)
    return {
        "code": 0,
        "msg": "success",
        "data": None
    }


# ============================= Agent Control ========================================

@router.post("/agent-control/set-agent-properties")
async def set_agent_properties(mode: Literal["only_voice", "voice_face", "normal"] = Body(..., description="交互运行模式", embed=True)):
    """设置机器人交互运行模式"""
    result = await agent_control_service.set_agent_properties(mode)
    result = await app_robot_service.agent_mode_reboot()
    return {
        "code": 0,
        "msg": "success",
        "data": None
    }


@router.get("/agent-control/get-agent-properties")
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

@router.post("/face-id-callback")
async def face_id_callback(data: dict = Body(..., embed=True)):
    """接收机器人端 FaceID 识别结果回调（由机器人端主动调用）"""
    print(data)
    return {
        "code": 0,
        "msg": "success",
        "data": data
    }


@router.get("/face/cloud-face-db-info")
async def get_cloud_face_db_info():
    """获取云端人脸数据库信息"""
    user_info = await app_robot_service.get_cloud_face_db_info()
    return {
        "code": 0,
        "msg": "success",
        "data": user_info
    }