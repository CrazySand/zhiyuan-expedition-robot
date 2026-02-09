import asyncio
import tempfile
import os
import json
from typing import Literal
from fastapi import APIRouter, Body, File, Query, UploadFile
from app.shared import rac, recognize_audio, send_callback_to_cloud, poll_nav_task_until_done, tts_finished_callback_delayed

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
    asyncio.create_task(tts_finished_callback_delayed(trace_id, text))
    return {
        "code": 0,
        "msg": "操作成功",
        "data": {"trace_id": trace_id},
    }


@router.delete("/tts")
async def stop_tts():
    """打断当前 TTS 播报"""
    result = await rac.stop_tts()
    return {"code": 0, "msg": "操作成功", "data": None}


@router.get("/tts/status")
async def get_audio_status(trace_id: str = Query(..., description="播报ID", min_length=1, max_length=100)):
    """查询 TTS 播报状态"""
    result = await rac.get_audio_status(trace_id)
    tts_status = result["tts_status"]["tts_status"]
    return {
        "code": 0,
        "msg": "操作成功",
        "data": {"tts_status": tts_status},
    }


@router.get("/tts/volume")
async def get_audio_volume():
    """获取当前音量"""
    result = await rac.get_audio_volume()
    audio_volume = result["audio_volume"]
    return {
        "code": 0,
        "msg": "操作成功",
        "data": {"audio_volume": audio_volume},
    }


@router.put("/tts/volume")
async def set_audio_volume(audio_volume: int = Body(..., description="音量大小", ge=0, le=70, embed=True)):
    """设置音量"""
    result = await rac.set_audio_volume(audio_volume)
    return {"code": 0, "msg": "操作成功", "data": None}

# ============================= Agent Control ========================================


@router.post("/agent-control/agent-properties")
async def set_agent_properties(mode: Literal["only_voice", "voice_face", "normal"] = Body(..., description="交互运行模式", embed=True)):
    """设置机器人交互运行模式"""
    result = await rac.set_agent_properties(mode)
    result = await rac.agent_mode_reboot()
    return {
        "code": 0,
        "msg": "操作成功",
        "data": None
    }


@router.get("/agent-control/agent-properties")
async def get_agent_properties():
    """查询机器人交互运行模式"""
    result = await rac.get_agent_properties()
    return {
        "code": 0,
        "msg": "操作成功",
        "data": {
            "mode": result["contents"]["properties"]["2"]
        }
    }

# ============================= Motion Control ========================================

# POST   /api/motion-control/mc-action  → 切换运控状态机（body: ext_action）
# GET    /api/motion-control/mc-action  → 查询当前运控状态机


@router.post("/motion-control/mc-action")
async def set_mc_action(ext_action: Literal["RL_LOCOMOTION_DEFAULT", "PASSIVE_UPPER_BODY_JOINT_SERVO", "RL_LOCOMOTION_ARM_EXT_JOINT_SERVO"] = Body(..., description="目标运控 Action", embed=True)):
    """切换运动控制状态机"""
    result = await rac.set_mc_action(ext_action)
    return {"code": 0, "msg": "操作成功", "data": None}


@router.get("/motion-control/mc-action")
async def get_mc_action():
    """查询当前运动控制状态机"""
    result = await rac.get_mc_action()
    return {
        "code": 0,
        "msg": "操作成功",
        "data": {
            "current_action": result["info"]["current_action"]
        },
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
    current_agent_mode = (await rac.get_agent_properties())["contents"]["properties"]["2"]
    if current_agent_mode not in ["voice_face", "normal"]:
        return {
            "code": 400,
            "msg": "当前交互模式不是 voice_face 或 normal",
            "data": None
        }
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
    """启动机器人端 ASR 程序"""
    current_agent_mode = (await rac.get_agent_properties())["contents"]["properties"]["2"]
    if current_agent_mode not in ["only_voice", "voice_face"]:
        return {
            "code": 400,
            "msg": "当前交互模式不是 only_voice 或 voice_face",
            "data": None
        }
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


# ============================== MAP ========================================

# GET    /api/map/list          → 获取地图列表
# GET    /api/map/detail        → 获取地图详情（query: map_id）


@router.get("/map/list")
async def get_map_list():
    """获取地图列表"""
    map_lists = (await rac.get_stored_map_names())["data"]["map_lists"]
    current_working_map_id = (await rac.get_current_working_map())["data"]["map_id"]
    current_working_map_name = next(
        (map for map in map_lists if map["map_id"] == current_working_map_id), None)["map_name"]
    return {
        "code": 0,
        "msg": "操作成功",
        "data": {
            "current_working_map_id": current_working_map_id,
            "current_working_map_name": current_working_map_name,
            "map_lists": map_lists,
        },
    }


@router.get("/map/detail")
async def get_map_detail(map_id: str = Query(..., description="地图ID")):
    """获取地图详情"""
    if map_id not in [map["map_id"] for map in (await rac.get_stored_map_names())["data"]["map_lists"]]:
        return {
            "code": 400,
            "msg": "地图ID不存在",
            "data": None
        }
    whole_map_result = await rac.get_2d_whole_map(map_id)
    topo_result = await rac.get_topo_msgs(map_id)
    points = []
    for point in topo_result["data"]["points"]:
        points.append({
            "point_id": point["point_id"],
            "point_name": point["name"],
        })
    return {
        "code": 0,
        "msg": "操作成功",
        "data": {
            "map_id": whole_map_result["data"]["map_id"],
            "map_name": whole_map_result["data"]["map_name"],
            "points": points,
        }}


# ============================== NAV ========================================

# POST   /api/nav/planning-to-goal  → 下发到点规划导航任务（body: task_id, map_id, target_id, ...）
# POST   /api/nav/task-control      → 取消/暂停/恢复导航任务（body: action=cancel|pause|resume, task_id）
# GET    /api/nav/status            → 获取导航任务状态（query: task_id，0 表示最近一次任务）


@router.post("/nav/planning-to-goal")
async def nav_planning_to_goal(
    task_id: str | None = Body(None, description="任务ID，None 表示自动生成"),
    point_id: int = Body(..., description="导航点ID"),
):
    """下发给定目标点 ID 的规划导航任务；后台每 5s 轮询状态，结束或失败时回调中控"""
    current_working_map_id = (await rac.get_current_working_map())["data"]["map_id"]
    result = await rac.planning_navi_to_goal(
        task_id=task_id or 0,
        map_id=current_working_map_id,
        target_id=point_id,
    )
    out_task_id = result["task_id"]
    asyncio.create_task(poll_nav_task_until_done(str(out_task_id)))
    return {
        "code": 0,
        "msg": "操作成功",
        "data": {
            "task_id": out_task_id
        },
    }


_NAV_TASK_FAIL_MSG = "任务不存在、已结束或 task_id 不匹配"

_NAV_TASK_ACTIONS = {
    "cancel": rac.cancel_navi_task,
    "pause": rac.pause_navi_task,
    "resume": rac.resume_navi_task,
}


@router.post("/nav/task-control")
async def nav_task_control(
    action: Literal["cancel", "pause",
                    "resume"] = Body(..., description="cancel=取消, pause=暂停, resume=恢复"),
    task_id: str = Body(..., description="任务ID", embed=True),
):
    """取消 / 暂停 / 恢复导航任务（仅当 task_id 匹配时才响应）"""
    try:
        fn = _NAV_TASK_ACTIONS[action]
        result = await fn(task_id)
        if result["state"] == "CommonState_SUCCESS":
            return {"code": 0, "msg": "操作成功", "data": None}
        return {"code": 400, "msg": _NAV_TASK_FAIL_MSG, "data": None}
    except json.JSONDecodeError:
        return {"code": 400, "msg": _NAV_TASK_FAIL_MSG, "data": None}


@router.get("/nav/status")
async def nav_status(task_id: str | None = Query(None, description="任务ID，None 表示最近一次任务")):
    """获取导航任务状态"""
    try:
        result = await rac.get_navi_task_status(task_id or 0)
        return {
            "code": 0,
            "msg": "操作成功",
            "data": {
                "task_id": result["task_id"],
                "state": result["state"]
            },
        }
    except json.JSONDecodeError:
        return {
            "code": 400,
            "msg": "任务不存在或已结束",
            "data": None
        }


# ============================== Webhooks（机器人回调）========================================


@router.post("/webhooks/face-recognition")
async def webhooks_face_recognition(data: dict = Body(..., embed=False)):
    """接收机器人端 FaceID 识别结果回调（由机器人端主动调用）"""
    timestamp = data["timestamp"]
    face_id = data["face_id"]
    confidence = data["confidence"]

    await send_callback_to_cloud(
        "faceRecognition",
        {
            "timestamp": timestamp,
            "face_id": face_id,
            "confidence": confidence,
        },
    )

    return {
        "code": 0,
        "msg": "操作成功",
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

        await send_callback_to_cloud(
            "asr",
            {"text": text},
        )
        return {
            "code": 0,
            "msg": "操作成功",
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
