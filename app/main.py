import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.api import router
from app.api_common import router as common_router
from app.shared import rac, send_callback_to_cloud
from app.config import SECRET_KEY, SERVER_HOST, SERVER_PORT, RELOAD, CLOUD_PUSH_INTERVAL

logger = logging.getLogger(__name__)

# ============================= 定时任务 =====================================


async def on_periodic_tick():
    """定时回调，每 5 分钟执行一次，在此填写逻辑"""
    system_state = await rac.get_system_state()
    bms_state = await rac.get_bms_state()
    alert_list = await rac.get_alert_list()

    params = {
        "current_state": system_state["cur_state"],  # 当前系统状态
        "temperature": bms_state["data"]["temperature"],  # 当前温度
        "battery_percent": bms_state["data"]["charge"],  # 当前电量
        "alert_list": alert_list["data"]["alerts"],
    }

    await send_callback_to_cloud("statusReport", params)


async def _periodic_loop(stop_event: asyncio.Event):
    while not stop_event.is_set():
        try:
            await on_periodic_tick()
        except Exception:
            pass
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=CLOUD_PUSH_INTERVAL)
        except asyncio.TimeoutError:
            pass


def start_periodic_task():
    """启动定时任务，返回 (task, stop_event)"""
    stop_event = asyncio.Event()
    task = asyncio.create_task(_periodic_loop(stop_event))
    return task, stop_event


# ==================================== 生命周期 ====================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时开启定时任务，关闭时停止"""
    task, stop_event = start_periodic_task()
    logger.info("设置定时回调上报系统状态任务完成")
    # 设置 Agent 交互模式
    if (await rac.get_agent_properties())["contents"]["properties"]["2"] != "voice_face":
        await rac.set_agent_properties("voice_face")
        await rac.agent_mode_reboot()
        logger.info("当前 Agent 交互模式不为 voice_face，已设置并重启 Agent")
    else:
        logger.info("Agent 交互模式为 voice_face")
    # 切换运控状态机
    await rac.set_mc_action("RL_LOCOMOTION_DEFAULT")
    logger.info("切换运控状态机为 RL_LOCOMOTION_DEFAULT")
    yield
    # 关闭时：通知停止 -> 取消任务 -> 等待结束
    stop_event.set()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

# ==================================== 异常处理器 ====================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """处理 HTTP 异常"""
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
    """处理全局异常"""
    return JSONResponse(status_code=200, content={"code": 500, "msg": str(exc), "data": None})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证异常"""
    errors = exc.errors()
    custom_message = None
    for error in errors:
        if error.get("type") == "value_error":
            custom_message = error.get("msg", "").removeprefix("Value error, ")
            break
    error_details = [
        {"loc": error.get("loc", []), "msg": error.get(
            "msg", ""), "type": error.get("type", "")}
        for error in errors
    ]
    message = custom_message if custom_message else "数据验证失败"
    return JSONResponse(status_code=200, content={"code": 400, "msg": message, "data": error_details})


# 包含 API 路由
app.include_router(router)
app.include_router(common_router)

# ==================================== 中间件 ====================================

# 配置 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuthMiddleware(BaseHTTPMiddleware):
    """认证中间件，用于验证请求头中的 Authorization 字段是否包含正确的密钥"""

    async def dispatch(self, request, call_next):
        x_api_key = request.headers.get("X-API-KEY")
        if x_api_key != SECRET_KEY:
            return JSONResponse(
                status_code=200,
                content={"code": 401, "msg": "认证失败", "data": None}
            )
        response = await call_next(request)
        return response


# 添加认证中间件
app.add_middleware(AuthMiddleware)

# ===================================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=SERVER_HOST,
                port=SERVER_PORT, reload=RELOAD)
