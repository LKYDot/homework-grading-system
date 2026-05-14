from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Text,
    DECIMAL,
    Boolean,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship
from .base import BaseModel


class HomeworkTask(BaseModel):
    __tablename__ = "homework_task"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(String(64), unique=True, nullable=False, comment="任务ID")
    user_id = Column(
        BigInteger, ForeignKey("user.id"), nullable=False, comment="用户ID"
    )
    subject = Column(String(20), nullable=False, comment="学科")
    grade = Column(String(20), nullable=False, comment="年级")
    status = Column(
        String(20),
        nullable=False,
        default="PENDING",
        comment="任务状态：PENDING/PROCESSING/SUCCESS/FAILED",
    )
    total_score = Column(DECIMAL(5, 2), default=0, comment="总分")
    error_message = Column(Text, comment="错误信息")

    user = relationship("User", back_populates="homework_tasks")
    images = relationship(
        "HomeworkImage", back_populates="task", cascade="all, delete-orphan"
    )
    question_blocks = relationship(
        "QuestionBlock", back_populates="task", cascade="all, delete-orphan"
    )
    ocr_results = relationship(
        "OCRResult", back_populates="task", cascade="all, delete-orphan"
    )
    grading_results = relationship(
        "GradingResult", back_populates="task", cascade="all, delete-orphan"
    )


class HomeworkImage(BaseModel):
    __tablename__ = "homework_image"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(
        String(64),
        ForeignKey("homework_task.task_id"),
        nullable=False,
        comment="任务ID",
    )
    original_url = Column(String(255), nullable=False, comment="原始图片URL")
    processed_url = Column(String(255), comment="预处理后图片URL")

    task = relationship("HomeworkTask", back_populates="images")


class QuestionBlock(BaseModel):
    __tablename__ = "question_block"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(
        String(64),
        ForeignKey("homework_task.task_id"),
        nullable=False,
        comment="任务ID",
    )
    question_no = Column(String(20), nullable=False, comment="题号")
    question_image_url = Column(String(255), nullable=False, comment="题目图片URL")
    x1 = Column(BigInteger, nullable=False, comment="左上角x坐标")
    y1 = Column(BigInteger, nullable=False, comment="左上角y坐标")
    x2 = Column(BigInteger, nullable=False, comment="右下角x坐标")
    y2 = Column(BigInteger, nullable=False, comment="右下角y坐标")

    task = relationship("HomeworkTask", back_populates="question_blocks")
    ocr_result = relationship(
        "OCRResult", back_populates="question_block", uselist=False
    )
    grading_result = relationship(
        "GradingResult", back_populates="question_block", uselist=False
    )


class OCRResult(BaseModel):
    __tablename__ = "ocr_result"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(
        String(64),
        ForeignKey("homework_task.task_id"),
        nullable=False,
        comment="任务ID",
    )
    question_block_id = Column(
        BigInteger, ForeignKey("question_block.id"), nullable=False, comment="题目块ID"
    )
    question_no = Column(String(20), nullable=False, comment="题号")
    question_text = Column(Text, comment="题干文本")
    student_answer = Column(Text, comment="学生答案")
    question_type = Column(String(50), comment="题型")
    raw_response = Column(JSON, comment="原始OCR响应")

    task = relationship("HomeworkTask", back_populates="ocr_results")
    question_block = relationship("QuestionBlock", back_populates="ocr_result")


class StandardAnswer(BaseModel):
    __tablename__ = "standard_answer"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    subject = Column(String(20), nullable=False, comment="学科")
    grade = Column(String(20), nullable=False, comment="年级")
    question_key = Column(
        String(100), unique=True, nullable=False, comment="题目唯一标识"
    )
    question_text = Column(Text, nullable=False, comment="题干文本")
    standard_answer = Column(Text, nullable=False, comment="标准答案")
    question_type = Column(String(50), nullable=False, comment="题型")
    max_score = Column(DECIMAL(5, 2), nullable=False, comment="满分")


class GradingResult(BaseModel):
    __tablename__ = "grading_result"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(
        String(64),
        ForeignKey("homework_task.task_id"),
        nullable=False,
        comment="任务ID",
    )
    question_block_id = Column(
        BigInteger, ForeignKey("question_block.id"), nullable=False, comment="题目块ID"
    )
    question_no = Column(String(20), nullable=False, comment="题号")
    score = Column(DECIMAL(5, 2), nullable=False, comment="得分")
    max_score = Column(DECIMAL(5, 2), nullable=False, comment="满分")
    result = Column(String(20), nullable=False, comment="批改结果：正确/部分正确/错误")
    comment = Column(Text, comment="批改批注")
    analysis = Column(Text, comment="题目解析")
    confidence = Column(DECIMAL(3, 2), comment="模型置信度")
    is_reviewed = Column(Boolean, default=False, comment="是否已人工复核")
    reviewed_score = Column(DECIMAL(5, 2), comment="复核后得分")
    reviewer_id = Column(BigInteger, ForeignKey("user.id"), comment="复核人ID")
    raw_response = Column(JSON, comment="原始大模型响应")

    task = relationship("HomeworkTask", back_populates="grading_results")
    question_block = relationship("QuestionBlock", back_populates="grading_result")
    reviewer = relationship("User", back_populates="reviewed_results")
