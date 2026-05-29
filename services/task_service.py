from sqlalchemy.orm import Session
from models.homework import (
    HomeworkTask,
    HomeworkImage,
    QuestionBlock,
    OCRResult,
    GradingResult as GradingResultModel,
    StandardAnswer,
)
from schemas.homework import GradingResult
from utils.logger import logger
from typing import Optional, List
from decimal import Decimal


class TaskService:
    def create_task(
        self,
        db: Session,
        task_id: str,
        user_id: int,
        subject: str,
        grade: str,
        file_path: str,
    ) -> HomeworkTask:
        task = HomeworkTask(
            task_id=task_id,
            user_id=user_id,
            subject=subject,
            grade=grade,
            status="PENDING",
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        image = HomeworkImage(task_id=task_id, original_url=file_path)
        db.add(image)
        db.commit()

        logger.info(f"创建作业任务: {task_id}")
        return task

    def get_task_by_id(self, db: Session, task_id: str) -> Optional[HomeworkTask]:
        return db.query(HomeworkTask).filter(HomeworkTask.task_id == task_id).first()

    def update_task_status(
        self, db: Session, task_id: str, status: str, error_message: str = None
    ):
        task = self.get_task_by_id(db, task_id)
        if task:
            task.status = status
            if error_message:
                task.error_message = error_message
            db.commit()
            logger.info(f"更新任务状态: {task_id} -> {status}")

    def update_task_total_score(self, db: Session, task_id: str, total_score: float):
        task = self.get_task_by_id(db, task_id)
        if task:
            task.total_score = Decimal(str(total_score))
            db.commit()

    def save_processed_image(self, db: Session, task_id: str, processed_path: str):
        image = db.query(HomeworkImage).filter(HomeworkImage.task_id == task_id).first()
        if image:
            image.processed_url = processed_path
            db.commit()
        else:
            logger.warning(f"未找到任务 {task_id} 的图片记录")

    def save_question_blocks(self, db: Session, task_id: str, blocks: List[dict]):
        for block in blocks:
            question_block = QuestionBlock(
                task_id=task_id,
                question_no=block["question_no"],
                question_image_url=block["image_path"],
                x1=block["x1"],
                y1=block["y1"],
                x2=block["x2"],
                y2=block["y2"],
            )
            db.add(question_block)
        db.commit()

        for block, question_block in zip(
            blocks,
            db.query(QuestionBlock).filter(QuestionBlock.task_id == task_id).all(),
        ):
            block["id"] = question_block.id

    def save_ocr_results(self, db: Session, task_id: str, ocr_results: List[dict]):
        for ocr_result in ocr_results:
            ocr = OCRResult(
                task_id=task_id,
                question_block_id=ocr_result["question_block_id"],
                question_no=ocr_result["question_no"],
                question_text=ocr_result.get("question_text", ""),
                student_answer=ocr_result.get("student_answer", ""),
                question_type=ocr_result.get("question_type", ""),
                raw_response=ocr_result.get("raw_response", {}),
            )
            db.add(ocr)
        db.commit()

    def save_grading_results(
        self, db: Session, task_id: str, grading_results: List[GradingResult]
    ):
        for result in grading_results:
            grading = GradingResultModel(
                task_id=task_id,
                question_block_id=result.question_block_id,
                question_no=result.question_no,
                score=Decimal(str(result.score)),
                max_score=Decimal(str(result.max_score)),
                result=result.result,
                comment=result.comment or "",
                analysis=result.analysis or "",
                confidence=(
                    Decimal(str(result.confidence)) if result.confidence else None
                ),
            )
            db.add(grading)
        db.commit()

    def get_grading_result(self, db: Session, task_id: str) -> Optional[dict]:
        task = self.get_task_by_id(db, task_id)
        if not task:
            return None

        grading_results = (
            db.query(GradingResultModel)
            .filter(GradingResultModel.task_id == task_id)
            .all()
        )

        results = [
            GradingResult(
                question_block_id=r.question_block_id,
                question_no=r.question_no,
                score=float(r.score),
                max_score=float(r.max_score),
                result=r.result,
                comment=r.comment,
                analysis=r.analysis,
                confidence=float(r.confidence) if r.confidence else None,
            )
            for r in grading_results
        ]

        return {
            "task_id": task_id,
            "total_score": float(task.total_score) if task.total_score else 0,
            "results": results,
            "created_at": task.created_at,
        }

    def get_homework_list(self, db, user_id):
        tasks = (
            db.query(HomeworkTask)
            .filter(HomeworkTask.user_id == user_id)
            .order_by(HomeworkTask.created_at.desc())
            .all()
        )
        
        result = []
        for task in tasks:
            result.append({
                "task_id": task.task_id,
                "user_id": task.user_id,
                "subject": task.subject,
                "grade": task.grade,
                "status": task.status,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
            })
        
        return result

    def match_standard_answer(
        self, db: Session, subject: str, grade: str, question_text: str
    ) -> Optional[StandardAnswer]:
        if not question_text:
            return None
        
        try:
            exact_match = (
                db.query(StandardAnswer)
                .filter(
                    StandardAnswer.subject == subject,
                    StandardAnswer.grade == grade,
                    StandardAnswer.question_text == question_text,
                )
                .first()
            )
            if exact_match:
                return exact_match
            
            keywords = [word for word in question_text.strip()[:50].split() if len(word) >= 3]
            if keywords:
                for keyword in keywords[:3]:
                    fuzzy_match = (
                        db.query(StandardAnswer)
                        .filter(
                            StandardAnswer.subject == subject,
                            StandardAnswer.grade == grade,
                            StandardAnswer.question_text.like(f"%{keyword}%"),
                        )
                        .first()
                    )
                    if fuzzy_match:
                        logger.debug(f"模糊匹配成功: '{keyword}' -> {fuzzy_match.question_key}")
                        return fuzzy_match
            
            logger.debug(f"未找到匹配的标准答案: {question_text[:50]}...")
            return None
        except Exception as e:
            logger.error(f"匹配标准答案失败: {str(e)}")
            return None


task_service = TaskService()
