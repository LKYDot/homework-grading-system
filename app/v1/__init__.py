from .homework import router as homework_router
from .user import router as user_router
from .statistics import router as statistics_router

__all__ = ["homework_router", "user_router", "statistics_router"]
