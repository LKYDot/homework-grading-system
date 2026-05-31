import base64
import json
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
import os
from typing import Optional
from utils.database import get_db
from schemas.common import APIResponse
from schemas.homework import (
    HomeworkListResponse,
    TaskStatusResponse,
    GradingResultResponse,
)
from services.task_service import task_service
from tasks.homework_tasks import process_homework_task, process_analyze_task
from config import settings
from utils.logger import logger
from utils.deps import get_current_user
from models.user import User

router = APIRouter(prefix="/homework", tags=["作业管理"])


async def _save_upload(file: UploadFile) -> tuple[str, str, bytes]:
    file_bytes = await file.read()
    if len(file_bytes) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="文件大小不能超过10MB")
    task_id = f"task_{uuid.uuid4().hex}"
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(settings.UPLOAD_DIR, f"{task_id}_{file.filename}")
    with open(file_path, "wb") as f:
        f.write(file_bytes)
    return task_id, file_path, file_bytes


# ======================== 提交作业 ========================

@router.post("/analyze", response_model=APIResponse)
async def analyze_homework(
    file: UploadFile = File(...),
    subject: str = Form(...),
    grade: str = Form(...),
    model: Optional[str] = Form(None),
    mode: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """提交作业图片进行分析/批改

    mode=ocr:  OCR 流水线 - 先切题返回区域供前端选择，确认后逐题识别+批改
    mode=vision: 视觉大模型直接看图批改，一步到位
    """
    try:
        task_id, file_path, _ = await _save_upload(file)
        grading_mode = mode or settings.GRADING_MODE

        model_name = model or (settings.text_models[0].name if settings.text_models else None)

        task_service.create_task(db, task_id, user.id, subject, grade, file_path)

        if grading_mode == "vision":
            # 视觉模式: 直接批改
            process_homework_task.delay(
                task_id, file_path, subject, grade, user.id,
                grading_mode="vision", model_name=model_name,
            )
            return APIResponse(data={
                "task_id": task_id, "mode": "vision",
                "status": "processing", "message": "视觉模型正在批改中"
            })
        else:
            # OCR 模式: 先切题，返回区域
            from clients.aliyun_client import aliyun_ocr_client
            question_blocks = aliyun_ocr_client.recognize_edu_paper_cut(file_path)

            # 保存切题结果到 DB
            task_service.save_question_blocks_raw(db, task_id, question_blocks, file_path)

            regions = []
            for i, b in enumerate(question_blocks):
                regions.append({
                    "index": i,
                    "question_no": b.get("question_no", str(i + 1)),
                    "x1": int(b.get("x1", 0)),
                    "y1": int(b.get("y1", 0)),
                    "x2": int(b.get("x2", 0)),
                    "y2": int(b.get("y2", 0)),
                    "text_preview": (b.get("text", "") or "")[:80],
                })

            logger.info(f"切题完成: {task_id}, {len(regions)} 个区域")
            return APIResponse(data={
                "task_id": task_id, "mode": "ocr",
                "status": "regions_ready",
                "regions": regions,
                "image_url": f"/api/v1/homework/image/{task_id}",
            })

    except HTTPException:
        raise
    except Exception as e:
        logger.opt(exception=True).error("提交失败: {}", str(e))
        raise HTTPException(status_code=500, detail="提交失败")


# ======================== 切题区域 ========================

@router.get("/regions/{task_id}", response_model=APIResponse)
def get_regions(task_id: str, db: Session = Depends(get_db)):
    """获取切题区域信息，包含裁剪后的小图 base64 预览"""
    try:
        task = task_service.get_task_by_id(db, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        from models.homework import QuestionBlock
        blocks = (
            db.query(QuestionBlock)
            .filter(QuestionBlock.task_id == task_id)
            .order_by(QuestionBlock.id)
            .all()
        )

        if not blocks:
            raise HTTPException(status_code=404, detail="该任务无切题数据，请先提交分析")

        regions = []
        for i, b in enumerate(blocks):
            preview_b64 = None
            if b.question_image_url and os.path.exists(b.question_image_url):
                with open(b.question_image_url, "rb") as f:
                    preview_b64 = base64.b64encode(f.read()).decode("utf-8")

            regions.append({
                "block_id": b.id,
                "index": i,
                "question_no": b.question_no,
                "x1": b.x1, "y1": b.y1, "x2": b.x2, "y2": b.y2,
                "preview_base64": preview_b64,
            })

        return APIResponse(data={
            "task_id": task_id,
            "regions": regions,
            "region_count": len(regions),
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.opt(exception=True).error("获取区域失败: {}", str(e))
        raise HTTPException(status_code=500, detail="获取区域失败")


# ======================== 确认并批改 ========================

@router.post("/{task_id}/confirm", response_model=APIResponse)
async def confirm_and_grade(
    task_id: str,
    model: Optional[str] = Form(None),
    selected_indices: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """确认切题区域并开始 OCR + 批改

    selected_indices: 逗号分隔的 region index (如 "0,1,3,5")，为空则使用全部区域
    """
    try:
        task = task_service.get_task_by_id(db, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        from models.homework import HomeworkImage, QuestionBlock
        image = db.query(HomeworkImage).filter(HomeworkImage.task_id == task_id).first()
        if not image or not image.original_url:
            raise HTTPException(status_code=400, detail="找不到原始图片")

        model_name = model or (settings.text_models[0].name if settings.text_models else None)

        # 解析选中的区域
        if selected_indices:
            indices = [int(x.strip()) for x in selected_indices.split(",") if x.strip()]
        else:
            indices = None

        process_analyze_task.delay(
            task_id, image.original_url, task.subject, task.grade, task.user_id,
            grading_mode="ocr", model_name=model_name,
            selected_indices=json.dumps(indices) if indices else "",
        )

        task_service.update_task_status(db, task_id, "PROCESSING")
        logger.info(f"确认批改: {task_id}, model={model_name}, indices={indices}")
        return APIResponse(data={
            "task_id": task_id,
            "mode": "ocr",
            "status": "processing",
            "selected_count": len(indices) if indices else "all",
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.opt(exception=True).error("确认批改失败: {}", str(e))
        raise HTTPException(status_code=500, detail="确认批改失败")


# ======================== 原图预览 ========================

@router.get("/image/{task_id}")
async def get_original_image(task_id: str, db: Session = Depends(get_db)):
    """获取原始上传图片 (用于前端切题区域叠加显示)"""
    from fastapi.responses import FileResponse
    from models.homework import HomeworkImage

    image = db.query(HomeworkImage).filter(HomeworkImage.task_id == task_id).first()
    if not image or not image.original_url or not os.path.exists(image.original_url):
        raise HTTPException(status_code=404, detail="图片不存在")

    return FileResponse(image.original_url, media_type="image/jpeg")


# ======================== 状态 / 结果 / 列表 ========================

@router.get("/status/{task_id}", response_model=APIResponse[TaskStatusResponse])
async def get_task_status(task_id: str, db: Session = Depends(get_db)):
    try:
        task = task_service.get_task_by_id(db, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        return APIResponse(data=TaskStatusResponse(
            task_id=task.task_id, status=task.status,
            created_at=task.created_at, updated_at=task.updated_at,
        ))
    except HTTPException:
        raise
    except Exception as e:
        logger.opt(exception=True).error("查询状态失败: {}", str(e))
        raise HTTPException(status_code=500, detail="查询状态失败")


@router.get("/result/{task_id}", response_model=APIResponse[GradingResultResponse])
async def get_grading_result(task_id: str, db: Session = Depends(get_db)):
    try:
        result = task_service.get_grading_result(db, task_id)
        if not result:
            raise HTTPException(status_code=404, detail="批改结果不存在")
        return APIResponse(data=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.opt(exception=True).error("查询结果失败: {}", str(e))
        raise HTTPException(status_code=500, detail="查询结果失败")


@router.get("/list", response_model=APIResponse)
async def get_homework_list(
    page: int = 1,
    page_size: int = 20,
    subject: Optional[str] = None,
    grade: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    try:
        skip = (page - 1) * page_size
        tasks = task_service.get_homework_list(
            db, skip=skip, limit=page_size, subject=subject, grade=grade, status=status
        )
        total = task_service.get_homework_count(
            db, subject=subject, grade=grade, status=status
        )
        return APIResponse(data={
            "items": tasks, "total": total, "page": page, "page_size": page_size,
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.opt(exception=True).error("获取列表失败: {}", str(e))
        raise HTTPException(status_code=500, detail="获取列表失败")


@router.delete("/{task_id}", response_model=APIResponse)
async def delete_homework(task_id: str, db: Session = Depends(get_db)):
    try:
        task = task_service.get_task_by_id(db, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        task_service.delete_task(db, task_id)
        return APIResponse(data={"task_id": task_id})
    except HTTPException:
        raise
    except Exception as e:
        logger.opt(exception=True).error("删除失败: {}", str(e))
        raise HTTPException(status_code=500, detail="删除失败")


# ======================== 元数据 ========================

@router.get("/subjects")
async def get_subjects():
    subjects = ["math", "chinese", "english", "physics", "chemistry", "biology", "history", "geography"]
    names = {"math":"数学","chinese":"语文","english":"英语","physics":"物理","chemistry":"化学","biology":"生物","history":"历史","geography":"地理"}
    return APIResponse(data=[{"code": s, "name": names[s]} for s in subjects])


@router.get("/grades")
async def get_grades():
    grades = [f"grade{i}" for i in range(1, 10)]
    names = {f"grade{i}": f"{['','一','二','三','四','五','六','初一','初二','初三'][i]}年级" for i in range(1,10)}
    return APIResponse(data=[{"code": g, "name": names[g]} for g in grades])


@router.get("/statuses")
async def get_statuses():
    statuses = [
        {"code":"PENDING","name":"待处理","description":"任务已创建，等待处理"},
        {"code":"PROCESSING","name":"处理中","description":"正在进行题目识别"},
        {"code":"GRADING","name":"批改中","description":"正在进行智能批改"},
        {"code":"SUCCESS","name":"已完成","description":"批改完成"},
        {"code":"FAILED","name":"失败","description":"处理失败"},
        {"code":"CANCELLED","name":"已取消","description":"任务已取消"},
    ]
    return APIResponse(data=statuses)
