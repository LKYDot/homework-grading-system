from celery_app import celery_app
from services.image_service import image_service
from clients.aliyun_client import aliyun_ocr_client
from clients.vision_client import vision_client
from services.llm_service import llm_service
from services.task_service import task_service
from config import settings
from utils.logger import logger
from utils.database import SessionLocal


def _ocr_pipeline(image_path, db, task_id):
    """Mode A: OCR 流水线 — 切题 → 裁剪 → 单题 OCR"""
    # CUTTING
    task_service.update_task_status(db, task_id, "CUTTING")
    question_blocks = aliyun_ocr_client.recognize_edu_paper_cut(image_path)
    n = len(question_blocks)
    logger.info(f"切题完成，共 {n} 道题")

    cropped = image_service.crop_question_blocks(image_path, question_blocks)
    task_service.save_question_blocks(db, task_id, cropped)

    # OCRING
    task_service.update_task_status(db, task_id, "OCRING")
    ocr_results = []
    for idx, block in enumerate(cropped):
        enhanced_path = image_service.enhance_for_ocr(block["image_path"])
        ocr = aliyun_ocr_client.recognize_edu_question_ocr(enhanced_path)

        if not ocr.get("question_text"):
            ocr = aliyun_ocr_client.recognize_edu_question_ocr(block["image_path"])

        if not ocr.get("question_text") and idx < len(question_blocks):
            t = question_blocks[idx].get("text", "")
            if t:
                ocr["question_text"] = t

        ocr["question_block_id"] = block["id"]
        ocr["question_no"] = block["question_no"]
        ocr_results.append(ocr)

    task_service.save_ocr_results(db, task_id, ocr_results)
    return ocr_results


def _vision_pipeline(image_path, db, task_id, model_name=None):
    """Mode B: 视觉大模型一步到位 — 看图 → 直接批改出结果"""
    task_service.update_task_status(db, task_id, "GRADING")

    cfg = None
    if model_name:
        cfg = settings.get_model_by_name(model_name)
        if cfg and cfg.type != "vision":
            logger.warning(f"模型 {model_name} 不是视觉模型，自动切换")
            cfg = None

    if not cfg:
        if settings.vision_models:
            cfg = settings.vision_models[0]
        elif settings.text_models:
            cfg = settings.text_models[0]
            logger.info(f"无视觉模型，尝试用文本模型 {cfg.name}")
        else:
            raise Exception("未配置任何可用模型")

    logger.info(f"视觉批改使用模型: {cfg.name} ({cfg.model_id})")
    grading_dicts = vision_client.grade_homework_directly(image_path, cfg)
    n = len(grading_dicts)
    logger.info(f"视觉批改完成，共 {n} 道题")

    if not grading_dicts:
        raise Exception("视觉模型未识别到任何题目")

    # 构建虚拟题目块 + OCR 结果（用于 DB 存储）
    from models.homework import QuestionBlock
    from schemas.homework import GradingResult

    virtual_blocks = [
        {"question_no": r["question_no"], "image_path": image_path,
         "x1": 0, "y1": 0, "x2": 100, "y2": 80}
        for r in grading_dicts
    ]
    task_service.save_question_blocks(db, task_id, virtual_blocks)

    saved_blocks = (
        db.query(QuestionBlock)
        .filter(QuestionBlock.task_id == task_id)
        .order_by(QuestionBlock.id).all()
    )

    ocr_results = []
    grading_results = []
    total_score = 0.0

    for i, (r, b) in enumerate(zip(grading_dicts, saved_blocks)):
        ocr_results.append({
            "question_block_id": b.id, "question_no": r["question_no"],
            "question_text": r["question_text"], "student_answer": r["student_answer"],
            "question_type": r["question_type"], "raw_response": {},
        })

        gr = GradingResult(
            question_block_id=b.id, question_no=r["question_no"],
            score=r["score"], max_score=r["max_score"],
            accuracy=r.get("accuracy", round(r["score"]/max(r["max_score"],1)*100, 1)),
            result=r["result"], comment=r.get("comment", ""),
            analysis=r.get("analysis", ""),
        )
        total_score += gr.score
        grading_results.append(gr)
        logger.info(
            f"批改 #{r['question_no']}: score={r['score']}/{r['max_score']} "
            f"accuracy={gr.accuracy}% result={r['result']} "
            f"comment={r.get('comment','')[:30]}"
        )

    task_service.save_ocr_results(db, task_id, ocr_results)
    task_service.save_grading_results(db, task_id, grading_results)
    task_service.update_task_total_score(db, task_id, total_score)

    total_acc = None
    accs = [r.accuracy for r in grading_results if r.accuracy is not None]
    if accs:
        total_acc = round(sum(accs) / len(accs), 1)
    logger.info(f"视觉批改完成: total_score={total_score}, total_accuracy={total_acc}%")
    return total_score, grading_results


def _grading_loop(ocr_results, db, task_id, model_name, subject="", grade=""):
    """逐题批改：优先查标准答案，有标答用标答参考批改，无标答让 LLM 直接解题"""
    task_service.update_task_status(db, task_id, "GRADING")
    total_score = 0.0
    grading_results = []

    for ocr in ocr_results:
        q_text = ocr.get("question_text", "")
        s_answer = ocr.get("student_answer", "")
        q_type = ocr.get("question_type", "解答题")

        if not q_text:
            from schemas.homework import GradingResult
            gr = GradingResult(
                question_block_id=ocr.get("question_block_id", 0),
                question_no=ocr.get("question_no", ""),
                score=0, max_score=0, accuracy=0,
                result="待复核", comment="题目识别失败",
            )
        else:
            std = task_service.match_standard_answer(db, subject, grade, q_text)
            if std is not None:
                logger.info(f"#{ocr.get('question_no','?')} 匹配到标准答案: {std.question_key}")
                gr = llm_service.grade_with_answer(
                    question_type=std.question_type,
                    question_text=q_text,
                    student_answer=s_answer,
                    standard_answer=std.standard_answer,
                    max_score=float(std.max_score),
                    model_name=model_name,
                )
            else:
                gr = llm_service.grade_without_answer(
                    question_type=q_type,
                    question_text=q_text,
                    student_answer=s_answer,
                    max_score=10.0,
                    model_name=model_name,
                )

        gr.question_block_id = ocr.get("question_block_id", 0)
        gr.question_no = ocr.get("question_no", "")
        total_score += gr.score
        grading_results.append(gr)
        logger.info(
            f"批改 #{gr.question_no}: score={gr.score}/{gr.max_score} "
            f"accuracy={gr.accuracy}% result={gr.result} "
            f"comment={gr.comment[:30] if gr.comment else ''}"
        )

    total_accuracy = None
    if grading_results:
        accs = [r.accuracy for r in grading_results if r.accuracy is not None]
        if accs:
            total_accuracy = round(sum(accs) / len(accs), 1)

    task_service.save_grading_results(db, task_id, grading_results)
    task_service.update_task_total_score(db, task_id, total_score)
    logger.info(f"全卷批改完成: total_score={total_score}, total_accuracy={total_accuracy}%")
    return total_score, grading_results


@celery_app.task(
    bind=True, max_retries=3, name="tasks.homework_tasks.process_homework_task"
)
def process_homework_task(
    self, task_id: str, image_path: str, subject: str, grade: str,
    user_id: int, grading_mode: str = "ocr", model_name: str = None,
):
    """处理作业批改任务"""
    db = SessionLocal()
    try:
        task_service.update_task_status(db, task_id, "PROCESSING")
        task_service.update_task_grading_mode(db, task_id, grading_mode)
        logger.info(f"开始处理: {task_id}, mode={grading_mode}, model={model_name}")

        # 分析与批改
        if grading_mode == "vision":
            # Mode B: 视觉模型一步到位，直接批改
            total_score, _ = _vision_pipeline(image_path, db, task_id, model_name)
        else:
            # Mode A: OCR 流水线 → 逐题 LLM 批改
            ocr_results = _ocr_pipeline(image_path, db, task_id)
            total_score, _ = _grading_loop(ocr_results, db, task_id, model_name, subject, grade)

        task_service.update_task_status(db, task_id, "SUCCESS")
        logger.info(f"批改完成: {task_id}, 总分: {total_score}")
        return {"task_id": task_id, "status": "SUCCESS", "total_score": total_score}

    except Exception as e:
        logger.opt(exception=True).error(
            "任务失败: task_id={}, 错误: {}", task_id, str(e)
        )
        db.rollback()
        task_service.update_task_status(db, task_id, "FAILED", str(e))
        raise self.retry(exc=e, countdown=5)
    finally:
        db.close()


@celery_app.task(
    bind=True, max_retries=3, name="tasks.homework_tasks.process_analyze_task"
)
def process_analyze_task(
    self, task_id: str, image_path: str, subject: str, grade: str,
    user_id: int, grading_mode: str = "ocr", model_name: str = None,
):
    """分析并批改作业（使用大模型直接分析）"""
    db = SessionLocal()
    try:
        task_service.update_task_status(db, task_id, "PROCESSING")
        task_service.update_task_grading_mode(db, task_id, grading_mode)
        logger.info(f"开始分析: {task_id}, mode={grading_mode}, model={model_name}")

        if grading_mode == "vision":
            total_score, _ = _vision_pipeline(image_path, db, task_id, model_name)
        else:
            ocr_results = _ocr_pipeline(image_path, db, task_id)
            total_score, _ = _grading_loop(ocr_results, db, task_id, model_name, subject, grade)

        task_service.update_task_status(db, task_id, "SUCCESS")
        logger.info(f"分析批改完成: {task_id}, 总分: {total_score}")
        return {"task_id": task_id, "status": "SUCCESS", "total_score": total_score}

    except Exception as e:
        logger.opt(exception=True).error("分析失败: task_id={}, 错误: {}", task_id, str(e))
        db.rollback()
        task_service.update_task_status(db, task_id, "FAILED", str(e))
        raise self.retry(exc=e, countdown=5)
    finally:
        db.close()


@celery_app.task(
    bind=True, max_retries=3, name="tasks.homework_tasks.process_grade_only_task"
)
def process_grade_only_task(self, task_id: str, model_name: str):
    """对已有分析结果用新模型重新批改"""
    db = SessionLocal()
    try:
        from models.homework import OCRResult
        ocr_rows = (
            db.query(OCRResult).filter(OCRResult.task_id == task_id).all()
        )
        if not ocr_rows:
            raise Exception("未找到OCR分析结果")

        ocr_results = [
            {
                "question_block_id": r.question_block_id,
                "question_no": r.question_no,
                "question_text": r.question_text or "",
                "student_answer": r.student_answer or "",
                "question_type": r.question_type or "解答题",
            }
            for r in ocr_rows
        ]

        task = task_service.get_task_by_id(db, task_id)
        total_score, _ = _grading_loop(
            ocr_results, db, task_id, model_name,
            subject=task.subject if task else "",
            grade=task.grade if task else "",
        )
        task_service.update_task_status(db, task_id, "SUCCESS")
        logger.info(f"重新批改完成: {task_id}, model={model_name}, 总分={total_score}")
        return {"task_id": task_id, "status": "SUCCESS", "total_score": total_score}

    except Exception as e:
        logger.opt(exception=True).error("重新批改失败: {}", str(e))
        db.rollback()
        raise
    finally:
        db.close()
