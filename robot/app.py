# =============================== 依赖导入 =======================================

import json
import subprocess
import sys
import os
import asyncio
from typing import Optional

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


# ================================ 通用进程管理器 =======================================

FACE_RECOGNITION_COMMAND = """
source /opt/ros/humble/setup.bash && \
source /agibot/data/home/agi/Desktop/agibot_a2_aimdk-dev1.3/prebuilt/ros2_plugin_proto_aarch64/share/ros2_plugin_proto/local_setup.bash && \
source /agibot/data/home/agi/Desktop/mydev/bin/activate && \
export ROS_DOMAIN_ID=232 && \
export ROS_LOCALHOST_ONLY=0 && \
export FASTRTPS_DEFAULT_PROFILES_FILE=/agibot/software/v0/entry/bin/cfg/ros_dds_configuration.xml && \
python /agibot/data/home/agi/Desktop/robot/get_face_id.py
"""

ASR_COMMAND = """
source /opt/ros/humble/setup.bash && \
source /agibot/data/home/agi/Desktop/agibot_a2_aimdk-dev1.3/prebuilt/ros2_plugin_proto_aarch64/share/ros2_plugin_proto/local_setup.bash && \
source /agibot/data/home/agi/Desktop/mydev/bin/activate && \
export ROS_DOMAIN_ID=232 && \
export ROS_LOCALHOST_ONLY=0 && \
export FASTRTPS_DEFAULT_PROFILES_FILE=/agibot/software/v0/entry/bin/cfg/ros_dds_configuration.xml && \
python /agibot/data/home/agi/Desktop/robot/get_voice.py
"""


class ProcessManager:
    """
    通用子进程管理器，用于启动/停止通过 bash 执行的命令（如人脸识别、ASR）。
    start(command) 时传入要执行的命令字符串，用 bash -c 执行。
    """

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False
        self._lock = asyncio.Lock()

    async def start(self, command: str) -> dict:
        """
        启动子进程，执行 command（通过 bash -c）。

        Args:
            command: 要执行的完整命令字符串（如 FACE_RECOGNITION_COMMAND 或 ASR_COMMAND）

        Returns:
            dict: {"pid": int, "status": "started"}

        Raises:
            HTTPException: 已在运行或启动失败
        """
        async with self._lock:
            if self.is_running:
                raise HTTPException(status_code=400, detail="进程已在运行中")

            try:
                kwargs = {
                    "args": ["bash", "-c", command],
                    "stdout": subprocess.PIPE,
                    "stderr": subprocess.PIPE,
                }
                if os.name != "nt":
                    kwargs["preexec_fn"] = os.setsid  # Linux：创建进程组，便于整组终止

                self.process = subprocess.Popen(**kwargs)
                self.is_running = True
                asyncio.create_task(self._monitor_process())
                return {"pid": self.process.pid, "status": "started"}
            except Exception as e:
                self.is_running = False
                raise HTTPException(status_code=500, detail=f"启动失败: {str(e)}")

    async def stop(self) -> dict:
        """停止子进程（含进程组）。"""
        async with self._lock:
            if not self.is_running:
                raise HTTPException(status_code=400, detail="进程未运行")

            try:
                if self.process:
                    try:
                        if os.name != "nt":
                            pgid = os.getpgid(self.process.pid)
                            os.killpg(pgid, 15)
                        else:
                            self.process.terminate()
                    except (ProcessLookupError, OSError):
                        try:
                            self.process.terminate()
                        except ProcessLookupError:
                            pass

                    try:
                        await asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(None, self.process.wait),
                            timeout=5.0,
                        )
                    except asyncio.TimeoutError:
                        try:
                            if os.name != "nt":
                                pgid = os.getpgid(self.process.pid)
                                os.killpg(pgid, 9)
                            else:
                                self.process.kill()
                        except (ProcessLookupError, OSError):
                            try:
                                self.process.kill()
                            except ProcessLookupError:
                                pass
                        self.process.wait()
                    self.process = None
                self.is_running = False
                return {"status": "stopped"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"停止失败: {str(e)}")

    async def get_status(self) -> dict:
        """返回当前进程状态：is_running, status, 可选 pid/return_code。"""
        async with self._lock:
            if self.is_running and self.process:
                return_code = self.process.returncode
                if return_code is not None:
                    self.is_running = False
                    self.process = None
                    return {"is_running": False, "status": "stopped", "return_code": return_code}
                return {"is_running": True, "status": "running", "pid": self.process.pid}
            return {"is_running": False, "status": "stopped"}

    async def _monitor_process(self):
        """后台监控：进程意外退出时更新状态。"""
        if self.process:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.process.wait)
            async with self._lock:
                if self.is_running:
                    self.is_running = False
                    self.process = None


# 人脸识别、ASR 各一个实例，start 时传入对应 command
face_recognition_process_manager = ProcessManager()
asr_process_manager = ProcessManager()


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


# RESTful：GET/POST/DELETE 同一资源路径，用方法区分
# GET    /api/face-recognition           → 进程状态
# POST   /api/face-recognition           → 启动
# DELETE /api/face-recognition           → 停止
# GET    /api/face-recognition/cloud-db  → 云端人脸库


@app.get("/api/face-recognition/cloud-db")
async def get_cloud_face_db_info():
    """获取云端人脸数据库信息"""
    async with aiofiles.open("/agibot/data/param/interaction/face_id/user_info.json", "r", encoding="utf-8") as f:
        data = await f.read()
    return {
        "code": 0,
        "msg": "success",
        "data": json.loads(data)
    }


@app.post("/api/face-recognition")
async def start_face_recognition():
    """启动人脸识别 Python 程序"""
    result = await face_recognition_process_manager.start(FACE_RECOGNITION_COMMAND)
    return {"code": 0, "msg": "success", "data": result}


@app.delete("/api/face-recognition")
async def stop_face_recognition():
    """停止人脸识别 Python 程序"""
    result = await face_recognition_process_manager.stop()
    return {"code": 0, "msg": "success", "data": result}


@app.get("/api/face-recognition")
async def get_face_recognition_status():
    """获取人脸识别进程状态"""
    status = await face_recognition_process_manager.get_status()
    return {"code": 0, "msg": "success", "data": status}


# GET    /api/asr  → 进程状态
# POST   /api/asr  → 启动
# DELETE /api/asr  → 停止


@app.post("/api/asr")
async def start_asr():
    """启动 ASR 程序（get_voice.py）"""
    result = await asr_process_manager.start(ASR_COMMAND)
    return {"code": 0, "msg": "success", "data": result}


@app.delete("/api/asr")
async def stop_asr():
    """停止 ASR 程序"""
    result = await asr_process_manager.stop()
    return {"code": 0, "msg": "success", "data": result}


@app.get("/api/asr")
async def get_asr_status():
    """获取 ASR 进程状态"""
    status = await asr_process_manager.get_status()
    return {"code": 0, "msg": "success", "data": status}


# ================================  应用启动 =======================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=59888)
