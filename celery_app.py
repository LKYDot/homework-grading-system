from celery import Celery
from config import settings

celery_app = Celery(
    "homework_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.homework_tasks"],
)

# 配置Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_max_retries=3,
    worker_prefetch_multiplier=1,
)

# 路由配置
celery_app.conf.task_routes = {
    "app.tasks.homework_tasks.process_homework_task": {"queue": "homework"},
}
