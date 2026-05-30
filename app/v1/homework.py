from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
import os
from typing import Optional, List
from utils.database import get_db
from schemas.common import APIResponse
from schemas.homework import (
    HomeworkListResponse,
    TaskStatusResponse,
    GradingResultResponse,
)
from services.task_service import task_service
from tasks.homework_tasks import (
    process_homework_task,
    process_analyze_task,
    process_grade_only_task,
)
from config import settings
from utils.logger import logger
from utils.deps import get_current_user
from models.user import User

router = APIRouter(prefix="/homework", tags=["作业管理"])


async def _save_upload(file: UploadFile) -> tuple[str, str, bytes]:
    """保存上传文件，返回 (task_id, file_path, file_bytes)"""
    file_bytes = await file.read()
    if len(file_bytes) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="文件大小不能超过10MB")

    task_id = f"task_{uuid.uuid4().hex}"
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(settings.UPLOAD_DIR, f"{task_id}_{file.filename}")

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    return task_id, file_path, file_bytes


@router.post("/upload", response_model=APIResponse)
async def upload_homework(
    file: UploadFile = File(...),
    subject: str = Form(...),
    grade: str = Form(...),
    model: Optional[str] = Form(None),
    mode: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """上传作业图片并开始批改

    mode: ocr (阿里云OCR流水线逐题识别) | vision (视觉大模型一次分析整张试卷)
    model: 可选指定模型名，不传则使用第一个启用的 text 模型
    """
    try:
        if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
            raise HTTPException(status_code=400, detail="仅支持JPG/PNG格式的图片")

        task_id, file_path, _ = await _save_upload(file)

        grading_mode = mode or settings.GRADING_MODE
        model_name = model or (settings.text_models[0].name if settings.text_models else None)

        if grading_mode == "vision" and not settings.vision_models:
            raise HTTPException(status_code=400, detail="vision 模式需要配置视觉模型")

        task_service.create_task(db, task_id, user.id, subject, grade, file_path)
        process_homework_task.delay(
            task_id, file_path, subject, grade, user.id,
            grading_mode=grading_mode,
            model_name=model_name,
        )

        logger.info(f"作业上传成功: {task_id}, mode={grading_mode}, model={model_name}")
        return APIResponse(data={"task_id": task_id})

    except HTTPException:
        raise
    except Exception as e:
        logger.opt(exception=True).error("作业上传失败: {}", str(e))
        raise HTTPException(status_code=500, detail="作业上传失败")


@router.post("/analyze", response_model=APIResponse)
async def analyze_homework(
    file: UploadFile = File(...),
    subject: str = Form(...),
    grade: str = Form(...),
    model: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """分析并批改作业（使用大模型直接分析）"""
    try:
        task_id, file_path, _ = await _save_upload(file)
        grading_mode = "vision"

        task_service.create_task(db, task_id, user.id, subject, grade, file_path)
        process_analyze_task.delay(
            task_id, file_path, subject, grade, user.id,
            grading_mode=grading_mode,
            model_name=model,
        )

        logger.info(f"分析任务已创建: {task_id}, mode={grading_mode}, model={model}")
        return APIResponse(data={"task_id": task_id})

    except HTTPException:
        raise
    except Exception as e:
        logger.opt(exception=True).error("分析任务创建失败: {}", str(e))
        raise HTTPException(status_code=500, detail="分析任务创建失败")


@router.post("/grade", response_model=APIResponse)
async def grade_homework(
    task_id: str = Form(...),
    model: str = Form(...),
    db: Session = Depends(get_db),
):
    """使用指定模型对已有任务重新批改"""
    try:
        task = task_service.get_task_by_id(db, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        model_cfg = settings.get_model_by_name(model)
        if not model_cfg:
            raise HTTPException(status_code=400, detail=f"模型不可用: {model}")

        process_grade_only_task.delay(task_id, model)
        logger.info(f"重新批改任务: {task_id}, model={model}")
        return APIResponse(data={"task_id": task_id, "model": model})

    except HTTPException:
        raise
    except Exception as e:
        logger.opt(exception=True).error("重新批改失败: {}", str(e))
        raise HTTPException(status_code=500, detail="重新批改失败")


@router.get("/status/{task_id}", response_model=APIResponse[TaskStatusResponse])
async def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """查询任务状态"""
    try:
        task = task_service.get_task_by_id(db, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        return APIResponse(data=TaskStatusResponse(
            task_id=task.task_id,
            status=task.status,
            created_at=task.created_at,
            updated_at=task.updated_at,
        ))

    except HTTPException:
        raise
    except Exception as e:
        logger.opt(exception=True).error("查询任务状态失败: {}", str(e))
        raise HTTPException(status_code=500, detail="查询任务状态失败")


@router.get("/result/{task_id}", response_model=APIResponse[GradingResultResponse])
async def get_grading_result(task_id: str, db: Session = Depends(get_db)):
    """查询批改结果"""
    try:
        result = task_service.get_grading_result(db, task_id)
        if not result:
            raise HTTPException(status_code=404, detail="批改结果不存在")
        return APIResponse(data=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.opt(exception=True).error("查询批改结果失败: {}", str(e))
        raise HTTPException(status_code=500, detail="查询批改结果失败")


@router.get("/list", response_model=APIResponse)
async def get_homework_list(
    page: int = 1,
    page_size: int = 20,
    subject: Optional[str] = None,
    grade: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """获取作业列表（分页）"""
    try:
        skip = (page - 1) * page_size
        tasks = task_service.get_homework_list(db, skip=skip, limit=page_size, subject=subject, grade=grade, status=status)
        total = task_service.get_homework_count(db, subject=subject, grade=grade, status=status)
        
        return APIResponse(data={
            "items": tasks,
            "total": total,
            "page": page,
            "page_size": page_size,
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.opt(exception=True).error("获取作业列表失败: {}", str(e))
        raise HTTPException(status_code=500, detail="获取作业列表失败")


@router.delete("/{task_id}", response_model=APIResponse)
async def delete_homework(task_id: str, db: Session = Depends(get_db)):
    """删除单个作业任务"""
    try:
        task = task_service.get_task_by_id(db, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        task_service.delete_task(db, task_id)
        logger.info(f"任务已删除: {task_id}")
        return APIResponse(data={"task_id": task_id})
    
    except HTTPException:
        raise
    except Exception as e:
        logger.opt(exception=True).error("删除任务失败: {}", str(e))
        raise HTTPException(status_code=500, detail="删除任务失败")


@router.post("/batch/delete", response_model=APIResponse)
async def batch_delete_homework(task_ids: List[str] = Form(...), db: Session = Depends(get_db)):
    """批量删除作业任务"""
    try:
        success_count = 0
        failed_count = 0
        
        for task_id in task_ids:
            try:
                task = task_service.get_task_by_id(db, task_id)
                if task:
                    task_service.delete_task(db, task_id)
                    success_count += 1
                else:
                    failed_count += 1
            except:
                failed_count += 1
        
        logger.info(f"批量删除完成: 成功{success_count}个, 失败{failed_count}个")
        return APIResponse(data={"success_count": success_count, "failed_count": failed_count})
    
    except Exception as e:
        logger.opt(exception=True).error("批量删除失败: {}", str(e))
        raise HTTPException(status_code=500, detail="批量删除失败")


@router.post("/{task_id}/cancel", response_model=APIResponse)
async def cancel_task(task_id: str, db: Session = Depends(get_db)):
    """取消正在处理的任务"""
    try:
        task = task_service.get_task_by_id(db, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        if task.status in ["PENDING", "PROCESSING", "GRADING"]:
            task_service.update_task_status(db, task_id, "CANCELLED")
            logger.info(f"任务已取消: {task_id}")
            return APIResponse(data={"task_id": task_id, "status": "CANCELLED"})
        else:
            raise HTTPException(status_code=400, detail="只有待处理或处理中的任务才能取消")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.opt(exception=True).error("取消任务失败: {}", str(e))
        raise HTTPException(status_code=500, detail="取消任务失败")


@router.get("/subjects")
async def get_subjects():
    """获取支持的科目列表"""
    subjects = ["math", "chinese", "english", "physics", "chemistry", "biology", "history", "geography"]
    subject_names = {
        "math": "数学",
        "chinese": "语文",
        "english": "英语",
        "physics": "物理",
        "chemistry": "化学",
        "biology": "生物",
        "history": "历史",
        "geography": "地理",
    }
    
    return {
        "code": 200,
        "message": "success",
        "data": [
            {"code": s, "name": subject_names[s]} for s in subjects
        ]
    }


@router.get("/grades")
async def get_grades():
    """获取支持的年级列表"""
    grades = ["grade1", "grade2", "grade3", "grade4", "grade5", "grade6", "grade7", "grade8", "grade9"]
    grade_names = {
        "grade1": "一年级",
        "grade2": "二年级",
        "grade3": "三年级",
        "grade4": "四年级",
        "grade5": "五年级",
        "grade6": "六年级",
        "grade7": "初一",
        "grade8": "初二",
        "grade9": "初三",
    }
    
    return {
        "code": 200,
        "message": "success",
        "data": [
            {"code": g, "name": grade_names[g]} for g in grades
        ]
    }


@router.get("/statuses")
async def get_statuses():
    """获取任务状态列表及说明"""
    statuses = [
        {"code": "PENDING", "name": "待处理", "description": "任务已创建，等待处理"},
        {"code": "PROCESSING", "name": "处理中", "description": "正在进行题目识别"},
        {"code": "GRADING", "name": "批改中", "description": "正在进行智能批改"},
        {"code": "SUCCESS", "name": "已完成", "description": "批改完成"},
        {"code": "FAILED", "name": "失败", "description": "处理失败"},
        {"code": "CANCELLED", "name": "已取消", "description": "任务已取消"},
    ]
    
    return {
        "code": 200,
        "message": "success",
        "data": statuses
    }
