import httpx
from typing import Literal
from fastapi import FastAPI, Request, Depends, HTTPException, Header, Query, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from tts_service import TTSClient
from agent_control_service import AgentControlService
from app_robot_service import AppRobotService

SECRET_KEY = "your-secret-key-here"

# =======================================================================

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

http_client = httpx.AsyncClient(
    headers={"Authorization": "Bearer your-secret-key-here"}, timeout=60)
tts_client = TTSClient(http_client)
agent_control_service = AgentControlService(http_client)
app_robot_service = AppRobotService(http_client)

# =======================================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """处理 HTTP 异常，返回统一的响应格式"""
    return JSONResponse(
        status_code=200,
        content={
            "code": exc.status_code,
            "msg": exc.detail if isinstance(exc.detail, str) else "请求失败",
            "data": None
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=200,
        content={
            "code": 500,
            "msg": str(exc),
            "data": None
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证异常，返回自定义响应格式"""
    errors = exc.errors()

    # 提取第一个自定义验证错误的消息（field_validator 中的 ValueError）
    custom_message = None
    for error in errors:
        if error.get("type") == "value_error":
            msg = error.get("msg", "")
            # 移除 Pydantic 添加的 "Value error, " 前缀
            custom_message = msg.removeprefix("Value error, ")
            break

    # 构建错误详情列表
    error_details = [
        {
            "loc": error.get("loc", []),
            "msg": error.get("msg", ""),
            "type": error.get("type", ""),
        }
        for error in errors
    ]

    # 使用自定义消息或默认消息
    message = custom_message if custom_message else "数据验证失败"
    return JSONResponse(
        status_code=200,
        content={"code": 400, "msg": message, "data": error_details}
    )


async def authenticate(
    authorization: str = Header(default="", alias="Authorization")
):
    # 检查 Authorization header 格式并验证 token
    if not authorization or not authorization.startswith("Bearer ") or authorization[7:] != SECRET_KEY:
        raise HTTPException(status_code=401, detail="认证失败")
    return authorization[7:]

# ================================ TTS Service======================================


@app.post("/api/play_tts", dependencies=[Depends(authenticate)])
async def play_tts(text: str = Body(..., min_length=1, max_length=200, description="播报文本内容", embed=True)):
    """TTS 播报"""
    result = await tts_client.play_tts(text)
    trace_id = result["trace_id"]
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "trace_id": trace_id
        }
    }


@app.post("/api/stop_tts", dependencies=[Depends(authenticate)])
async def stop_tts():
    """TTS 打断"""
    result = await tts_client.stop_tts()
    return {
        "code": 0,
        "msg": "success",
        "data": None
    }


@app.get("/api/get_audio_status", dependencies=[Depends(authenticate)])
async def get_audio_status(trace_id: str = Query(..., description="播报 id", min_length=1, max_length=100)):
    """TTS 播报状态查询"""
    result = await tts_client.get_audio_status(trace_id)
    tts_status = result["tts_status"]["tts_status"]
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "tts_status": tts_status
        }
    }


@app.get("/api/get_audio_volume", dependencies=[Depends(authenticate)])
async def get_audio_volume():
    """获取当前音量大小"""
    result = await tts_client.get_audio_volume()
    audio_volume = result["audio_volume"]
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "audio_volume": audio_volume
        }
    }


@app.post("/api/set_audio_volume", dependencies=[Depends(authenticate)])
async def set_audio_volume(audio_volume: int = Body(..., description="音量大小", ge=0, le=70, embed=True)):
    """设置音量大小"""
    result = await tts_client.set_audio_volume(audio_volume)
    return {
        "code": 0,
        "msg": "success",
        "data": None
    }


# ================================ Agent Control Service ======================================

@app.post("/api/set_agent_properties", dependencies=[Depends(authenticate)])
async def set_agent_properties(mode: Literal["only_voice", "voice_face", "normal"] = Body(..., description="交互运行模式", embed=True)):
    """设置机器人交互运行模式"""
    result = await agent_control_service.set_agent_properties(mode)
    result = await app_robot_service.agent_mode_reboot()
    return {
        "code": 0,
        "msg": "success",
        "data": None
    }


@app.get("/api/get_agent_properties", dependencies=[Depends(authenticate)])
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
