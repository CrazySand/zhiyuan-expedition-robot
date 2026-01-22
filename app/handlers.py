from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


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


async def global_exception_handler(request: Request, exc: Exception):
    """处理全局异常，返回统一的响应格式"""
    return JSONResponse(
        status_code=200,
        content={
            "code": 500,
            "msg": str(exc),
            "data": None
        }
    )


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