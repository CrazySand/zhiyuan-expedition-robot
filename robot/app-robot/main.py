# =============================== 依赖导入 =======================================

import json
import subprocess
import sys
import asyncio
from typing import Optional

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


# ================================ 人脸识别进程管理器 =======================================

class FaceRecognitionProcessManager:
    """人脸识别进程管理器，用于启动和停止人脸识别 Python 程序"""

    def __init__(self):
        self.process: Optional[asyncio.subprocess.Process] = None
        self.is_running = False
        self._lock = asyncio.Lock()

    async def start(self) -> dict:
        """
        启动人脸识别 Python 程序（包含环境设置）

        Returns:
            dict: 启动结果，包含进程 ID

        Raises:
            HTTPException: 如果程序已在运行或启动失败
        """
        async with self._lock:
            if self.is_running:
                raise HTTPException(status_code=400, detail="人脸识别程序已在运行中")

            try:
                # 构建完整的启动命令（包含所有环境设置）
                command = """
                source /opt/ros/humble/setup.bash && \
                source /agibot/data/home/agi/Desktop/agibot_a2_aimdk-dev1.3/prebuilt/ros2_plugin_proto_aarch64/share/ros2_plugin_proto/local_setup.bash && \
                source /agibot/data/home/agi/Desktop/mydev/bin/activate && \
                export ROS_DOMAIN_ID=232 && \
                export ROS_LOCALHOST_ONLY=0 && \
                export FASTRTPS_DEFAULT_PROFILES_FILE=/agibot/software/v0/entry/bin/cfg/ros_dds_configuration.xml && \
                python /agibot/data/home/agi/Desktop/get_face_id.py
                """

                # 使用 bash -c 执行命令
                self.process = await asyncio.create_subprocess_exec(
                    "bash",
                    "-c",
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                self.is_running = True
                asyncio.create_task(self._monitor_process())

                return {
                    "pid": self.process.pid,
                    "status": "started"
                }
            except Exception as e:
                self.is_running = False
                raise HTTPException(status_code=500, detail=f"启动失败: {str(e)}")

    async def stop(self) -> dict:
        """
        停止人脸识别 Python 程序

        Returns:
            dict: 停止结果

        Raises:
            HTTPException: 如果程序未运行
        """
        async with self._lock:
            if not self.is_running:
                raise HTTPException(status_code=400, detail="人脸识别程序未运行")

            try:
                if self.process:
                    # 终止进程（这会终止整个 bash 进程及其子进程）
                    self.process.terminate()

                    # 等待进程结束（最多等待 5 秒）
                    try:
                        await asyncio.wait_for(self.process.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        # 如果进程没有正常结束，强制杀死
                        self.process.kill()
                        await self.process.wait()

                    self.process = None

                self.is_running = False

                return {
                    "status": "stopped"
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"停止失败: {str(e)}")

    async def get_status(self) -> dict:
        """
        获取人脸识别进程状态

        Returns:
            dict: 进程状态信息
        """
        async with self._lock:
            if self.is_running and self.process:
                # 检查进程是否真的还在运行
                return_code = self.process.returncode
                if return_code is not None:
                    # 进程已结束，但状态未更新（意外退出）
                    self.is_running = False
                    self.process = None
                    return {
                        "is_running": False,
                        "status": "stopped",
                        "return_code": return_code
                    }

                return {
                    "is_running": True,
                    "status": "running",
                    "pid": self.process.pid
                }
            else:
                return {
                    "is_running": False,
                    "status": "stopped"
                }

    async def _monitor_process(self):
        """监控进程状态，如果进程意外退出则自动更新状态"""
        if self.process:
            await self.process.wait()
            async with self._lock:
                if self.is_running:
                    # 进程意外退出，更新状态
                    self.is_running = False
                    self.process = None


# 创建人脸识别进程管理器实例
face_recognition_process_manager = FaceRecognitionProcessManager()


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


@app.post("/api/face-recognition/start")
async def start_face_recognition():
    """启动人脸识别 Python 程序"""
    try:
        result = await face_recognition_process_manager.start()
        return {
            "code": 0,
            "msg": "success",
            "data": result
        }
    except HTTPException as e:
        return {
            "code": e.status_code,
            "msg": e.detail,
            "data": None
        }


@app.post("/api/face-recognition/stop")
async def stop_face_recognition():
    """停止人脸识别 Python 程序"""
    try:
        result = await face_recognition_process_manager.stop()
        return {
            "code": 0,
            "msg": "success",
            "data": result
        }
    except HTTPException as e:
        return {
            "code": e.status_code,
            "msg": e.detail,
            "data": None
        }


@app.get("/api/face-recognition/status")
async def get_face_recognition_status():
    """获取人脸识别进程状态"""
    status = await face_recognition_process_manager.get_status()
    return {
        "code": 0,
        "msg": "success",
        "data": status
    }


# ================================  应用启动 =======================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=59888)
