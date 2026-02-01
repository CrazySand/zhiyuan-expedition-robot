import tempfile
import os
from typing import Literal
import httpx
from fastapi import APIRouter, Body, File, Query, UploadFile
from app.robot_api_client import RobotAPIClient
from app.asr import recognize_audio

rac = RobotAPIClient(
    httpx.AsyncClient(timeout=60), server_ip="127.0.0.1")

router = APIRouter(prefix="/api")

# ============================= TTS ========================================

# POST   /api/tts         → 发起播报（body: text）
# DELETE /api/tts         → 打断播报
# GET    /api/tts/status  → 查询播报状态（query: trace_id）
# GET    /api/tts/volume  → 获取音量
# PUT    /api/tts/volume  → 设置音量（body: audio_volume）


@router.post("/tts")
async def play_tts(text: str = Body(..., min_length=1, max_length=200, description="播报文本内容", embed=True)):
    """发起 TTS 播报"""
    result = await rac.play_tts(text)
    trace_id = result["trace_id"]
    return {
        "code": 0,
        "msg": "success",
        "data": {"trace_id": trace_id},
    }


@router.delete("/tts")
async def stop_tts():
    """打断当前 TTS 播报"""
    result = await rac.stop_tts()
    return {"code": 0, "msg": "success", "data": None}


@router.get("/tts/status")
async def get_audio_status(trace_id: str = Query(..., description="播报 id", min_length=1, max_length=100)):
    """查询 TTS 播报状态"""
    result = await rac.get_audio_status(trace_id)
    tts_status = result["tts_status"]["tts_status"]
    return {
        "code": 0,
        "msg": "success",
        "data": {"tts_status": tts_status},
    }


@router.get("/tts/volume")
async def get_audio_volume():
    """获取当前音量"""
    result = await rac.get_audio_volume()
    audio_volume = result["audio_volume"]
    return {
        "code": 0,
        "msg": "success",
        "data": {"audio_volume": audio_volume},
    }


@router.put("/tts/volume")
async def set_audio_volume(audio_volume: int = Body(..., description="音量大小", ge=0, le=70, embed=True)):
    """设置音量"""
    result = await rac.set_audio_volume(audio_volume)
    return {"code": 0, "msg": "success", "data": None}

# ============================= Agent Control ========================================


@router.post("/agent-control/agent-properties")
async def set_agent_properties(mode: Literal["only_voice", "voice_face", "normal"] = Body(..., description="交互运行模式", embed=True)):
    """设置机器人交互运行模式"""
    result = await rac.set_agent_properties(mode)
    result = await rac.agent_mode_reboot()
    return {
        "code": 0,
        "msg": "success",
        "data": None
    }


@router.get("/agent-control/agent-properties")
async def get_agent_properties():
    """查询机器人交互运行模式"""
    result = await rac.get_agent_properties()
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "mode": result["contents"]["properties"]["2"]
        }
    }

# ============================== Face Recognition ========================================

# GET    /api/face-recognition           → 进程状态
# POST   /api/face-recognition           → 启动
# DELETE /api/face-recognition           → 停止
# GET    /api/face-recognition/cloud-db  → 云端人脸库信息


@router.get("/face-recognition/cloud-db")
async def get_cloud_face_db_info():
    """获取云端人脸数据库信息"""
    result = await rac.get_cloud_face_db_info()
    return result


@router.post("/face-recognition")
async def start_face_recognition():
    """启动人脸识别 Python 程序"""
    result = await rac.start_face_recognition()
    return result


@router.delete("/face-recognition")
async def stop_face_recognition():
    """停止人脸识别 Python 程序"""
    result = await rac.stop_face_recognition()
    return result


@router.get("/face-recognition")
async def get_face_recognition_status():
    """获取人脸识别进程状态"""
    result = await rac.get_face_recognition_status()
    return result


# ============================== ASR ========================================

# GET    /api/asr  → 进程状态
# POST   /api/asr  → 启动
# DELETE /api/asr  → 停止


@router.post("/asr")
async def start_asr():
    """启动机器人端 ASR 程序（get_voice.py）"""
    result = await rac.start_asr()
    return result


@router.delete("/asr")
async def stop_asr():
    """停止机器人端 ASR 程序"""
    result = await rac.stop_asr()
    return result


@router.get("/asr")
async def get_asr_status():
    """获取机器人端 ASR 进程状态"""
    result = await rac.get_asr_status()
    return result


# ============================== Webhooks（机器人回调）========================================


@router.post("/webhooks/face-recognition")
async def webhooks_face_recognition(data: dict = Body(..., embed=False)):
    """接收机器人端 FaceID 识别结果回调（由机器人端主动调用）"""
    timestamp = data["timestamp"]
    face_id = data["face_id"]
    confidence = data["confidence"]

    # 在这里把以上数据发送到中控即可
    print(f"""
    收到 FaceID 识别结果回调:
    timestamp: {timestamp}
    face_id: {face_id}
    confidence: {confidence}
    """)
    pass

    return {
        "code": 0,
        "msg": "success",
        "data": {
            "face_id": face_id,
        }
    }


@router.post("/webhooks/asr/audio")
async def webhooks_asr_audio(file: UploadFile = File(..., description="音频文件（二进制）")):
    """机器人上传音频 → 存 tempfile → 语音转文字 → 结果发给中控 → 返回识别文本 -> 删除临时文件"""
    suffix = os.path.splitext(file.filename or "")[1] or ".bin"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        content = await file.read()
        tmp.write(content)
        tmp.close()
        path = tmp.name
        text = recognize_audio(path)

        # 这里把识别到的文本发送到中控
        print(f"""
        收到 ASR 音频文件:
        size: {len(content)} bytes
        text: {text}
        """)
        pass

        return {
            "code": 0,
            "msg": "success",
            "data": {
                "text": text,
            },
        }
    finally:
        if os.path.exists(tmp.name):
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
