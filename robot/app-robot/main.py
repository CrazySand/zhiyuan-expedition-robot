import httpx
from typing import Literal
from fastapi import FastAPI, Request, Depends, HTTPException, Header, Query, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
import service
from utils import run_command_live_output

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

http_client = httpx.AsyncClient(timeout=10)

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

# =======================================================================


@app.post("/api/agent-mode-reboot")
async def agent_mode_reboot():
    """重启 agent 模块"""
    run_command_live_output(
        "aima em stop-app agent && aima em start-app agent")
    return {
        "code": 0,
        "msg": "success",
        "data": None
    }

# =======================================================================


@app.get("/api/cloud-face-db-info")
async def get_cloud_face_db_info():
    """获取云端人脸数据库信息"""
    user_info = await service.read_cloud_face_db_info()
    return {
        "code": 0,
        "msg": "success",
        "data": user_info
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=59888)
