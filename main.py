from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager
from config import settings
from app.v1 import homework, user, statistics
from utils.database import create_tables
from utils.logger import logger
from utils.exceptions import BusinessException


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    logger.info("启动服务...")
    create_tables()
    logger.info(f"服务启动成功，访问地址：http://{settings.HOST}:{settings.PORT}")
    yield
    logger.info("服务正在关闭...")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=app_lifespan,
)

# 配置CORS---中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


# 全局异常处理
@app.exception_handler(BusinessException)
async def business_exception_handler(request: Request, exc: BusinessException):
    logger.error(f"业务异常: {exc.message}")
    return JSONResponse(
        status_code=exc.code,
        content={"code": exc.code, "message": exc.message, "data": None},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"系统异常: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500, content={"code": 500, "message": "系统内部错误", "data": None}
    )


# 注册路由
app.include_router(homework.router, prefix="/api/v1")
app.include_router(user.router, prefix="/api/v1")
app.include_router(statistics.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "message": "欢迎使用中小学作业批改系统 API",
    }


# 健康检查
@app.get("/status")
async def health_check():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
