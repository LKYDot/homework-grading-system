from celery_app import celery_app
from services.image_service import image_service
from clients.aliyun_client import aliyun_ocr_client
from services.llm_service import llm_service
from services.task_service import task_service
from schemas.homework import GradingResult
from utils.logger import logger
from sqlalchemy.orm import Session
from utils.database import get_db
import asyncio


@celery_app.task(
    bind=True, max_retries=3, name="app.tasks.homework_tasks.process_homework_task"
)
def process_homework_task(
    self, task_id: str, image_path: str, subject: str, grade: str, user_id: int
):
    """处理作业批改任务"""
    db: Session = next(get_db())

    try:
        task_service.update_task_status(db, task_id, "PROCESSING")
        logger.info(f"开始处理作业任务: {task_id}")

        task_service.update_task_status(db, task_id, "PREPROCESSING")
        processed_image_path = image_service.preprocess_image(image_path)

        task_service.save_processed_image(db, task_id, processed_image_path)

        task_service.update_task_status(db, task_id, "CUTTING")
        question_blocks = aliyun_ocr_client.recognize_edu_paper_cut(
            processed_image_path
        )

        cropped_blocks = image_service.crop_question_blocks(
            processed_image_path, question_blocks
        )

        task_service.save_question_blocks(db, task_id, cropped_blocks)

        task_service.update_task_status(db, task_id, "OCRING")
        ocr_results = []
        for block in cropped_blocks:
            ocr_result = aliyun_ocr_client.recognize_edu_question_ocr(
                block["image_path"]
            )
            ocr_result["question_block_id"] = block["id"]
            ocr_result["question_no"] = block["question_no"]
            ocr_results.append(ocr_result)

        task_service.save_ocr_results(db, task_id, ocr_results)

        task_service.update_task_status(db, task_id, "GRADING")
        total_score = 0
        grading_results = []

        for ocr_result in ocr_results:
            standard_answer = task_service.match_standard_answer(
                db, subject, grade, ocr_result["question_text"]
            )

            if standard_answer is None:
                grading_result = GradingResult(
                    question_block_id=ocr_result["question_block_id"],
                    question_no=ocr_result["question_no"],
                    score=0,
                    max_score=0,
                    result="待复核",
                    comment="未找到标准答案，请人工批改",
                    analysis="",
                    confidence=0.0,
                )
            else:
                grading_result = llm_service.grade_question(
                    question_type=standard_answer.question_type,
                    question_text=ocr_result["question_text"],
                    student_answer=ocr_result["student_answer"],
                    standard_answer=standard_answer.standard_answer,
                    max_score=float(standard_answer.max_score),
                )
                grading_result.question_block_id = ocr_result["question_block_id"]
                grading_result.question_no = ocr_result["question_no"]
                total_score += grading_result.score

            grading_results.append(grading_result)

        task_service.save_grading_results(db, task_id, grading_results)

        task_service.update_task_total_score(db, task_id, total_score)
        task_service.update_task_status(db, task_id, "SUCCESS")

        logger.info(f"作业任务处理完成: {task_id}, 总分: {total_score}")
        return {"task_id": task_id, "status": "SUCCESS", "total_score": total_score}

    except Exception as e:
        logger.error(f"作业任务处理失败: {task_id}, 错误: {str(e)}", exc_info=True)
        task_service.update_task_status(db, task_id, "FAILED", str(e))
        raise self.retry(exc=e, countdown=5)
    finally:
        db.close()