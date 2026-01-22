# =============================== 依赖导入 =======================================

import json
import subprocess
import sys

import httpx
import aiofiles

from fastapi import FastAPI, Request, HTTPException, Header, Query, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError


# ================================ 应用初始化 =======================================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================== 异常处理器 ========================================


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


# ================================ 工具函数 =======================================

def run_command_live_output(command):
    """
    执行系统命令并实时打印输出，执行完成后函数才返回。
    适合耗时较长的命令（如 apt update），可实时看到执行过程。

    Args:
        command (str): 要在 Ubuntu 系统上执行的系统命令字符串（如 "sudo apt update"）

    Returns:
        int: 命令执行返回码（0 表示成功，-1 表示执行过程中出现异常）
    """
    # 启动子进程，stdout/stderr 重定向到管道
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # 将错误输出合并到标准输出，方便实时打印
        text=True,
        encoding='utf-8',
        bufsize=1  # 行缓冲，保证输出实时性
    )

    # 实时读取并打印输出(调试)
    for line in process.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()

    # 阻塞等待命令执行完成，获取返回码
    process.wait()
    return process.returncode


# ================================  API 路由 =======================================

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


@app.get("/api/cloud-face-db-info")
async def get_cloud_face_db_info():
    """获取云端人脸数据库信息"""
    async with aiofiles.open("/agibot/data/param/interaction/face_id/user_info.json", "r", encoding="utf-8") as f:
        data = await f.read()
    return {
        "code": 0,
        "msg": "success",
        "data": json.loads(data)
    }

# ================================  应用启动 =======================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=59888)
