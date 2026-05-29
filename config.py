from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ==================== 服务配置 ====================
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # ==================== 数据库配置 ====================
    DATABASE_URL: str = (
        "mysql+pymysql://homework_user:homework_password@localhost:3306/homework_db?charset=utf8mb4"
    )

    # 数据库连接池配置
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 50
    DB_POOL_RECYCLE: int = 280
    DB_ECHO: bool = False

    # ==================== Redis配置 ====================
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ==================== 阿里云服务配置 ====================
    ALIYUN_ACCESS_KEY_ID: str = ""
    ALIYUN_ACCESS_KEY_SECRET: str = ""
    ALIYUN_OCR_ENDPOINT: str = "ocr-api.cn-hangzhou.aliyuncs.com"

    # OCR服务开关
    ENABLE_ALIYUN_OCR: bool = True

    # ==================== DeepSeek 大模型配置（通过阿里云百炼 DashScope API）====================
    DASHSCOPE_API_KEY: str = ""

    LLM_MODEL: str = "deepseek-v4-flash"

    # LLM服务开关
    ENABLE_LLM: bool = True

    # LLM调用配置
    LLM_MAX_TOKENS: int = 2048
    LLM_TEMPERATURE: float = 0.1
    LLM_TIMEOUT: int = 60

    # ==================== JWT配置 ====================
    JWT_SECRET_KEY: str = "your-secret-key-change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    # 刷新token配置
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ==================== 文件存储配置 ====================
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB

    # 允许的文件类型
    ALLOWED_EXTENSIONS: List[str] = ["jpg", "jpeg", "png", "gif", "bmp", "pdf"]

    # 图片压缩配置
    IMAGE_COMPRESS_QUALITY: int = 85
    MAX_IMAGE_WIDTH: int = 2048
    MAX_IMAGE_HEIGHT: int = 2048

    # ==================== 日志配置 ====================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    LOG_FILE: Optional[str] = None
    LOG_ROTATION: str = "1 day"
    LOG_RETENTION: str = "30 days"

    # ==================== 跨域配置 ====================
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # ==================== 限流配置 ====================
    RATE_LIMIT_MAX_REQUESTS: int = 1000
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # ==================== 异步任务配置 ====================
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: List[str] = ["json"]
    CELERY_TASK_TIMEOUT: int = 300
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = 1

    # ==================== 安全配置 ====================
    SECURE_COOKIES: bool = False
    SESSION_COOKIE_NAME: str = "session_id"
    CSRF_PROTECTION_ENABLED: bool = False

    # ==================== 应用配置 ====================
    APP_NAME: str = "作业智能批改系统"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "基于AI的中小学作业智能批改系统"

    @property
    def upload_path(self) -> Path:
        """获取上传目录的Path对象"""
        path = Path(self.UPLOAD_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def is_aliyun_ocr_enabled(self) -> bool:
        """检查阿里云OCR是否可用"""
        return bool(
            self.ENABLE_ALIYUN_OCR
            and self.ALIYUN_ACCESS_KEY_ID
            and self.ALIYUN_ACCESS_KEY_SECRET
        )

    @property
    def is_llm_enabled(self) -> bool:
        """检查大模型是否可用"""
        return bool(self.ENABLE_LLM and self.DASHSCOPE_API_KEY)


settings = Settings()
