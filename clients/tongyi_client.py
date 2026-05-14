import json
from config import settings
from utils.logger import logger
from schemas.homework import GradingResult

try:
    import dashscope
    from dashscope import Generation
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False
    logger.warning("通义千问SDK不可用，将使用mock模式")

try:
    import pybreaker
    
    def on_failure_handler(exc):
        logger.error(f"大模型调用失败: {str(exc)}")
    
    circuit_breaker = pybreaker.CircuitBreaker(
        fail_max=5,
        reset_timeout=30,
    )
    circuit_breaker.on_failure = on_failure_handler
except ImportError:
    circuit_breaker = None
    logger.warning("pybreaker不可用，将不使用熔断器")

if DASHSCOPE_AVAILABLE:
    dashscope.api_key = settings.DASHSCOPE_API_KEY


class TongyiClient:
    def __init__(self):
        if DASHSCOPE_AVAILABLE:
            self.model = settings.LLM_MODEL or "qwen-turbo"
        else:
            self.model = "mock"

    def grade_homework(self, ocr_results: list) -> list:
        """调用大模型进行作业批改"""
        if not DASHSCOPE_AVAILABLE:
            return self._mock_grade_homework(ocr_results)
            
        try:
            messages = self._build_prompt(ocr_results)

            if circuit_breaker:
                response = circuit_breaker.call(
                    self._call_dashscope,
                    messages=messages,
                )
            else:
                response = self._call_dashscope(messages=messages)

            results = self._parse_response(response)
            logger.info(f"大模型批改完成，共批改{len(results)}道题")
            return results

        except Exception as e:
            logger.error(f"大模型批改失败: {str(e)}", exc_info=True)
            raise

    def _call_dashscope(self, messages: list) -> dict:
        """调用通义千问API"""
        response = Generation.call(
            model=self.model,
            messages=messages,
            result_format="json",
            max_tokens=2048,
            temperature=0.1,
        )

        if response.status_code != 200:
            raise Exception(f"API调用失败: {response.message}")

        return response.output.choices[0].message.content

    def _build_prompt(self, ocr_results: list) -> list:
        """构建批改提示词"""
        questions_text = "\n".join(
            [
                f"题目{i+1}（{ocr.get('question_type', '未知')}）：\n问题：{ocr.get('question_text', '')}\n学生答案：{ocr.get('student_answer', '')}"
                for i, ocr in enumerate(ocr_results)
            ]
        )

        system_prompt = """
你是一名中小学作业批改老师，请根据学生的答案进行批改。
输出格式必须是JSON数组，每个元素包含：question_no, score, max_score, result, comment, analysis。
question_no: 题目编号
score: 得分（数字）
max_score: 满分（默认10分）
result: 结果（正确/错误/部分正确）
comment: 简短评语
analysis: 详细分析（可选）
"""

        user_prompt = f"""
请批改以下作业：

{questions_text}

请给出批改结果。
"""

        return [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()},
        ]

    def _parse_response(self, response: str) -> list:
        """解析大模型响应"""
        try:
            result = json.loads(response)
            if isinstance(result, list):
                return [
                    GradingResult(
                        question_block_id=idx,
                        question_no=str(r.get("question_no", idx + 1)),
                        score=r.get("score", 0),
                        max_score=r.get("max_score", 10),
                        result=r.get("result", "错误"),
                        comment=r.get("comment", ""),
                        analysis=r.get("analysis", ""),
                        confidence=0.8,
                    )
                    for idx, r in enumerate(result)
                ]
            return []
        except json.JSONDecodeError:
            logger.error(f"解析大模型响应失败: {response}")
            return []

    def _mock_grade_homework(self, ocr_results: list) -> list:
        """Mock大模型批改结果"""
        logger.info(f"使用mock模式进行作业批改，共{len(ocr_results)}道题")
        results = []
        for idx, ocr in enumerate(ocr_results):
            question_type = ocr.get("question_type", "计算题")
            student_answer = ocr.get("student_answer", "").strip()
            
            # 简单的mock逻辑
            if question_type == "计算题":
                if student_answer == "5" or student_answer == "五":
                    score = 10
                    result = "正确"
                    comment = "计算正确"
                else:
                    score = 0
                    result = "错误"
                    comment = "计算错误"
            elif question_type == "选择题":
                if student_answer.upper() in ["A", "B", "C", "D"]:
                    score = 10
                    result = "正确"
                    comment = "回答正确"
                else:
                    score = 0
                    result = "错误"
                    comment = "答案格式错误"
            else:
                score = 5
                result = "部分正确"
                comment = "需要人工复核"
            
            results.append(
                GradingResult(
                    question_block_id=idx,
                    question_no=str(idx + 1),
                    score=score,
                    max_score=10,
                    result=result,
                    comment=comment,
                    analysis="",
                    confidence=0.7,
                )
            )
        return results


tongyi_client = TongyiClient()
