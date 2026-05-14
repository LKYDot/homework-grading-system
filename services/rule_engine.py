import re
from typing import Optional
from schemas.homework import GradingResult


class RuleEngine:
    def grade(
        self,
        question_type: str,
        question_text: str,
        student_answer: str,
        standard_answer: str,
        max_score: float,
    ) -> Optional[GradingResult]:
        if question_type == "选择题":
            return self._grade_choice(student_answer, standard_answer, max_score)
        elif question_type == "判断题":
            return self._grade_judgment(student_answer, standard_answer, max_score)
        elif question_type == "填空题":
            return self._grade_fill_blank(student_answer, standard_answer, max_score)
        elif question_type in ["口算题", "计算题"]:
            return self._grade_calculation(student_answer, standard_answer, max_score)
        return None

    def _grade_choice(
        self, student_answer: str, standard_answer: str, max_score: float
    ) -> GradingResult:
        student_answer = student_answer.strip().upper()
        standard_answer = standard_answer.strip().upper()

        if student_answer == standard_answer:
            return GradingResult(
                question_block_id=0,
                question_no="",
                score=max_score,
                max_score=max_score,
                result="正确",
                comment="回答正确",
                analysis="",
                confidence=1.0,
            )
        elif student_answer in standard_answer:
            return GradingResult(
                question_block_id=0,
                question_no="",
                score=max_score * 0.5,
                max_score=max_score,
                result="部分正确",
                comment="部分正确",
                analysis="",
                confidence=0.8,
            )
        else:
            return GradingResult(
                question_block_id=0,
                question_no="",
                score=0,
                max_score=max_score,
                result="错误",
                comment="回答错误",
                analysis="",
                confidence=1.0,
            )

    def _grade_judgment(
        self, student_answer: str, standard_answer: str, max_score: float
    ) -> GradingResult:
        student_answer = student_answer.strip()
        standard_answer = standard_answer.strip()

        correct_values = ["正确", "对", "true", "True", "TRUE", "T"]
        wrong_values = ["错误", "错", "false", "False", "FALSE", "F"]

        is_correct = student_answer in correct_values
        is_wrong = student_answer in wrong_values
        std_correct = standard_answer in correct_values

        if is_correct and std_correct:
            return GradingResult(
                question_block_id=0,
                question_no="",
                score=max_score,
                max_score=max_score,
                result="正确",
                comment="判断正确",
                analysis="",
                confidence=1.0,
            )
        elif is_wrong and not std_correct:
            return GradingResult(
                question_block_id=0,
                question_no="",
                score=0,
                max_score=max_score,
                result="错误",
                comment="判断错误",
                analysis="",
                confidence=1.0,
            )
        else:
            return GradingResult(
                question_block_id=0,
                question_no="",
                score=0,
                max_score=max_score,
                result="错误",
                comment="答案格式错误",
                analysis="",
                confidence=1.0,
            )

    def _grade_fill_blank(
        self, student_answer: str, standard_answer: str, max_score: float
    ) -> GradingResult:
        student_answer = student_answer.strip()
        standard_answer = standard_answer.strip()

        if student_answer == standard_answer:
            return GradingResult(
                question_block_id=0,
                question_no="",
                score=max_score,
                max_score=max_score,
                result="正确",
                comment="回答正确",
                analysis="",
                confidence=1.0,
            )
        else:
            return GradingResult(
                question_block_id=0,
                question_no="",
                score=0,
                max_score=max_score,
                result="错误",
                comment="回答错误",
                analysis="",
                confidence=1.0,
            )

    def _grade_calculation(
        self, student_answer: str, standard_answer: str, max_score: float
    ) -> Optional[GradingResult]:
        try:
            student_clean = re.sub(r"[^\d.\-]", "", student_answer.strip())
            standard_clean = re.sub(r"[^\d.\-]", "", standard_answer.strip())

            if not student_clean or not standard_clean:
                return None

            student_val = float(student_clean)
            standard_val = float(standard_clean)

            if abs(student_val - standard_val) < 1e-9:
                return GradingResult(
                    question_block_id=0,
                    question_no="",
                    score=max_score,
                    max_score=max_score,
                    result="正确",
                    comment="计算正确",
                    analysis="",
                    confidence=1.0,
                )
            elif abs(student_val - standard_val) < max(0.01, standard_val * 0.01):
                return GradingResult(
                    question_block_id=0,
                    question_no="",
                    score=max_score * 0.5,
                    max_score=max_score,
                    result="部分正确",
                    comment="计算结果近似正确",
                    analysis="",
                    confidence=0.9,
                )
            else:
                return GradingResult(
                    question_block_id=0,
                    question_no="",
                    score=0,
                    max_score=max_score,
                    result="错误",
                    comment="计算结果错误",
                    analysis="",
                    confidence=1.0,
                )
        except (ValueError, ZeroDivisionError):
            return None


rule_engine = RuleEngine()
