from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
import os
from utils.database import get_db
from schemas.common import APIResponse
from schemas.homework import (
    HomeworkListResponse,
    TaskStatusResponse,
    GradingResultResponse,
)
from typing import List
from services.task_service import task_service
from tasks.homework_tasks import process_homework_task
from config import settings
from utils.logger import logger

router = APIRouter(prefix="/homework", tags=["作业管理"])


@router.post("/upload", response_model=APIResponse)
async def upload_homework(
    file: UploadFile = File(...),
    subject: str = Form(...),
    grade: str = Form(...),
    user_id: int = Form(...),
    db: Session = Depends(get_db),
):
    """上传作业图片"""
    try:
        # 校验文件类型
        if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
            raise HTTPException(status_code=400, detail="仅支持JPG/PNG格式的图片")

        # 校验文件大小
        file_size = await file.read()
        if len(file_size) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=400, detail="文件大小不能超过10MB")
        await file.seek(0)

        # 生成任务ID
        task_id = f"task_{uuid.uuid4().hex}"

        # 保存文件
        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{task_id}_{file.filename}")

        with open(file_path, "wb") as f:
            f.write(file_size)

        # 创建任务记录
        task_service.create_task(db, task_id, user_id, subject, grade, file_path)

        # 提交异步任务
        process_homework_task.delay(task_id, file_path, subject, grade, user_id)

        logger.info(f"作业上传成功: {task_id}")
        return APIResponse(data={"task_id": task_id})

    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"作业上传失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="作业上传失败")


@router.get("/status/{task_id}", response_model=APIResponse[TaskStatusResponse])
async def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """查询任务状态"""
    try:
        task = task_service.get_task_by_id(db, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        return APIResponse(
            data=TaskStatusResponse(
                task_id=task.task_id,
                status=task.status,
                created_at=task.created_at,
                updated_at=task.updated_at,
            )
        )

    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"查询任务状态失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询任务状态失败")


@router.get("/result/{task_id}", response_model=APIResponse[GradingResultResponse])
async def get_grading_result(task_id: str, db: Session = Depends(get_db)):
    """查询批改结果"""
    try:
        result = task_service.get_grading_result(db, task_id)
        if not result:
            raise HTTPException(status_code=404, detail="批改结果不存在")

        return APIResponse(data=result)

    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"查询批改结果失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询批改结果失败")


@router.get("/list", response_model=APIResponse[List[HomeworkListResponse]])
async def get_homework_list(user_id: int, db: Session = Depends(get_db)):
    """获取作业列表"""
    try:
        result = task_service.get_homework_list(db, user_id)
        return APIResponse(data=result)

    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"获取作业列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取作业列表失败")
