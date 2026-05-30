from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    created_at: datetime
    updated_at: datetime


class GradingResult(BaseModel):
    question_block_id: int
    question_no: str
    score: float
    max_score: float
    accuracy: Optional[float] = None   # 正确率 0-100
    result: str
    comment: Optional[str] = None
    analysis: Optional[str] = None
    confidence: Optional[float] = None
    raw_response: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class GradingResultResponse(BaseModel):
    task_id: str
    total_score: float
    total_accuracy: Optional[float] = None   # 整体正确率 0-100
    grading_mode: Optional[str] = None       # ocr | vision
    results: list[GradingResult]
    created_at: datetime


class HomeworkUploadRequest(BaseModel):
    subject: str
    grade: str
    user_id: int


class HomeworkListResponse(BaseModel):
    task_id: str
    subject: str
    grade: str
    user_id: int
    status: str
    created_at: datetime
    updated_at: datetime
