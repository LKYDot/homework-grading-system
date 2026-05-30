import json
from pydantic import BaseModel as PydanticBaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
from pathlib import Path


class ModelConfig(PydanticBaseModel):
    """单个模型配置"""
    name: str                          # 前端展示名称
    provider: str = "openai"           # dashscope | openai | google | deepseek
    api_key: str = ""
    base_url: str = ""                 # 覆盖默认 base URL
    model_id: str = ""                 # API 调用时的 model 参数
    type: str = "text"                 # text | vision
    enabled: bool = True
    max_tokens: int = 2048
    temperature: float = 0.1


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
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 50
    DB_POOL_RECYCLE: int = 280
    DB_ECHO: bool = False

    # ==================== Redis配置 ====================
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ==================== 阿里云 OCR ====================
    ALIYUN_ACCESS_KEY_ID: str = ""
    ALIYUN_ACCESS_KEY_SECRET: str = ""
    ALIYUN_OCR_ENDPOINT: str = "ocr-api.cn-hangzhou.aliyuncs.com"
    ENABLE_ALIYUN_OCR: bool = True

    # ==================== 大模型配置 ====================
    # JSON 格式的多模型配置
    MODELS_CONFIG: str = "[]"

    # 批改模式: ocr (阿里云OCR流水线) | vision (视觉大模型直接分析)
    GRADING_MODE: str = "ocr"

    # LLM 全局默认值
    LLM_MAX_TOKENS: int = 2048
    LLM_TEMPERATURE: float = 0.1
    LLM_TIMEOUT: int = 60

    # ==================== JWT配置 ====================
    JWT_SECRET_KEY: str = "your-secret-key-change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ==================== 文件存储配置 ====================
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS: List[str] = ["jpg", "jpeg", "png", "gif", "bmp", "pdf"]
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

    # ----- computed -----

    @property
    def parsed_models(self) -> List[ModelConfig]:
        """解析 MODELS_CONFIG JSON 字符串为 ModelConfig 列表"""
        try:
            raw = json.loads(self.MODELS_CONFIG)
            return [ModelConfig(**item) for item in raw]
        except Exception:
            return []

    @property
    def text_models(self) -> List[ModelConfig]:
        return [m for m in self.parsed_models if m.type == "text" and m.enabled]

    @property
    def vision_models(self) -> List[ModelConfig]:
        return [m for m in self.parsed_models if m.type == "vision" and m.enabled]

    def get_model_by_name(self, name: str) -> Optional[ModelConfig]:
        for m in self.parsed_models:
            if m.name == name and m.enabled:
                return m
        return None

    @property
    def upload_path(self) -> Path:
        path = Path(self.UPLOAD_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def is_aliyun_ocr_enabled(self) -> bool:
        return bool(
            self.ENABLE_ALIYUN_OCR
            and self.ALIYUN_ACCESS_KEY_ID
            and self.ALIYUN_ACCESS_KEY_SECRET
        )

    @property
    def is_llm_enabled(self) -> bool:
        """有任意启用的模型即视为 LLM 可用"""
        return len(self.text_models) > 0 or len(self.vision_models) > 0


settings = Settings()
