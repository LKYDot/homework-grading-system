from clients.tongyi_client import tongyi_client
from services.rule_engine import rule_engine
from schemas.homework import GradingResult
from utils.logger import logger


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
            # 客观题优先使用规则引擎
            if question_type in ["选择题", "判断题", "填空题", "口算题", "计算题"]:
                rule_result = self.rule_engine.grade(
                    question_type,
                    question_text,
                    student_answer,
                    standard_answer,
                    max_score,
                )
                if rule_result is not None:
                    # 使用大模型生成解析和评语
                    llm_result = self.tongyi_client.grade_question(
                        question_type,
                        question_text,
                        student_answer,
                        standard_answer,
                        max_score,
                    )
                    # 合并结果
                    rule_result.comment = llm_result.comment
                    rule_result.analysis = llm_result.analysis
                    rule_result.confidence = 1.0  # 规则引擎置信度为1
                    return rule_result

            # 主观题使用大模型
            return self.tongyi_client.grade_question(
                question_type, question_text, student_answer, standard_answer, max_score
            )

        except Exception as e:
            logger.error(f"题目批改失败: {str(e)}", exc_info=True)
            # 降级处理：返回默认结果
            return GradingResult(
                score=0,
                max_score=max_score,
                result="错误",
                comment="系统批改失败，请人工复核",
                analysis="",
                confidence=0.0,
            )


llm_service = LLMService()
