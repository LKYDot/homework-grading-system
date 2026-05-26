from clients.tongyi_client import tongyi_client, GradeResult
from services.rule_engine import rule_engine
from schemas.homework import GradingResult
from utils.logger import logger


def _to_schema(r: GradeResult) -> GradingResult:
    return GradingResult(
        question_block_id=r.question_block_id,
        question_no=r.question_no,
        score=r.score,
        max_score=r.max_score,
        result=r.result,
        comment=r.comment or None,
        analysis=r.analysis or None,
        confidence=r.confidence or None,
    )


class LLMService:
    def __init__(self):
        self.tongyi_client = tongyi_client
        self.rule_engine = rule_engine

    def grade_question(
        self,
        question_type: str,
        question_text: str,
        student_answer: str,
        standard_answer: str,
        max_score: float,
    ) -> GradingResult:
        """智能批改题目，优先使用规则引擎，复杂题目使用大模型"""
        try:
            if question_type in ["选择题", "判断题", "填空题", "口算题", "计算题"]:
                rule_result = self.rule_engine.grade(
                    question_type,
                    question_text,
                    student_answer,
                    standard_answer,
                    max_score,
                )
                if rule_result is not None:
                    llm_result = self.tongyi_client.grade_question(
                        question_type,
                        question_text,
                        student_answer,
                        standard_answer,
                        max_score,
                    )
                    rule_result.comment = llm_result.comment if llm_result.comment else rule_result.comment
                    rule_result.analysis = llm_result.analysis if llm_result.analysis else rule_result.analysis
                    rule_result.confidence = 1.0
                    return rule_result

            return _to_schema(
                self.tongyi_client.grade_question(
                    question_type, question_text, student_answer, standard_answer, max_score
                )
            )

        except Exception as e:
            logger.error(f"题目批改失败: {str(e)}", exc_info=True)
            return GradingResult(
                question_block_id=0,
                question_no="",
                score=0,
                max_score=max_score,
                result="错误",
                comment="系统批改失败，请人工复核",
                analysis="",
                confidence=0.0,
            )


llm_service = LLMService()