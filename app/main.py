from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.handlers import http_exception_handler, global_exception_handler, validation_exception_handler
from app.api import router
from app.config import SECRET_KEY, SERVER_HOST, SERVER_PORT

# =======================================================================

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

# =======================================================================

app = FastAPI()

# 包含 API 路由
app.include_router(router)

# 配置 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加认证中间件
app.add_middleware(AuthMiddleware)

# 注册异常处理器
app.exception_handler(HTTPException)(http_exception_handler)
app.exception_handler(Exception)(global_exception_handler)
app.exception_handler(RequestValidationError)(validation_exception_handler)

# =======================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
