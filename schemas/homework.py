from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal


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
    results: list[GradingResult]
    created_at: datetime


class HomeworkUploadRequest(BaseModel):
    subject: str
    grade: str
    user_id: int
