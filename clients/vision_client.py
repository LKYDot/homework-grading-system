import json
import re
import base64
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import List
from config import ModelConfig
from utils.logger import logger


@dataclass
class VisionQuestion:
    question_text: str = ""
    student_answer: str = ""
    position: dict = field(default_factory=lambda: {"x1": 0, "y1": 0, "x2": 0, "y2": 0})
    question_type: str = "解答题"


class VisionClient:
    """视觉模型客户端 — 通过 OpenAI 兼容接口调用 (GPT-4V / Qwen-VL / Gemini 等)

    两种模式:
    - analyze_homework: 仅识别题目，不做批改
    - grade_homework_directly: 直接批改整张试卷，一步到位 (Mode B)
    """

    PROMPT_ANALYZE = (
        "请仔细分析这张作业/试卷图片，识别出每一道题目。\n\n"
        "对每道题，请提取：\n"
        "1. question_text: 完整题目文本（数学公式请用 LaTeX 格式）\n"
        "2. student_answer: 学生手写作答内容\n"
        "3. question_type: 题型（选择题/判断题/填空题/计算题/口算题/解答题）\n\n"
        "严格只输出 JSON 数组：\n"
        '[{"question_text":"...","student_answer":"...","question_type":"计算题"}]'
    )

    PROMPT_GRADE = (
        "你是一位中小学作业批改老师。请仔细查看这张作业图片，逐题批改。\n\n"
        "批改要求：\n"
        "1. 识别每道题目和学生的作答内容\n"
        "2. 判断学生答案是否正确\n"
        "3. 给出得分（每题满分 10 分）、评语和分析\n\n"
        "输出格式：严格的 JSON 数组，每个元素包含：\n"
        '- question_no: 题号字符串\n'
        '- question_text: 题目文本（LaTeX格式）\n'
        '- student_answer: 学生作答内容\n'
        '- question_type: 题型\n'
        '- score: 得分数字 (0-10)\n'
        '- max_score: 满分数字 (通常是10)\n'
        '- result: "正确" / "部分正确" / "错误"\n'
        '- comment: 简短评语\n'
        '- analysis: 解题分析和知识点\n\n'
        "不要输出 markdown 代码块，直接输出 JSON 数组：\n"
        '[{"question_no":"1","question_text":"计算：3+5","student_answer":"8","question_type":"口算题","score":10,"max_score":10,"result":"正确","comment":"计算正确","analysis":"掌握了基本加法"}]'
    )

    def analyze_homework(self, image_path: str, model_config: ModelConfig) -> List[VisionQuestion]:
        """分析整张试卷图片，仅识别题目不批改"""
        image_b64 = self._encode_image(image_path)
        text = self._call_vision_api(image_b64, model_config, self.PROMPT_ANALYZE)
        return self._parse(text)

    def grade_homework_directly(self, image_path: str, model_config: ModelConfig) -> List[dict]:
        """视觉模型直接批改整张试卷，返回结构化评分结果"""
        image_b64 = self._encode_image(image_path)
        text = self._call_vision_api(image_b64, model_config, self.PROMPT_GRADE)
        return self._parse_grading(text)

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _call_vision_api(self, image_b64: str, cfg: ModelConfig, prompt: str) -> str:
        """OpenAI 兼容 vision 接口"""
        url = (cfg.base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/")
        url += "/chat/completions"

        body = json.dumps({
            "model": cfg.model_id or cfg.name,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{image_b64}"
                    }},
                ],
            }],
            "max_tokens": max(cfg.max_tokens or 4096, 4096),
            "temperature": cfg.temperature,
        }).encode("utf-8")

        req = urllib.request.Request(url, data=body, method="POST", headers={
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json",
        })

        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"]
                logger.info(f"视觉模型返回内容长度: {len(content)}")
                return content
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            logger.error(f"视觉API HTTP {e.code}: {body[:300]}")
            raise Exception(f"视觉模型API调用失败: HTTP {e.code}")
        except Exception as e:
            logger.error(f"视觉模型调用异常: {e}")
            raise

    def _clean_json(self, text: str) -> str:
        """清理并修复截断的 JSON"""
        text = text.strip()
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
        text = text.replace("“", '"').replace("”", '"')
        text = text.replace("‘", "'").replace("’", "'")

        m = re.search(r"\[.*", text, re.DOTALL)
        if m:
            text = m.group(0)

        # 修复截断: 补上未闭合的字符串和括号
        text = self._repair_truncated(text)
        return text

    def _repair_truncated(self, text: str) -> str:
        """修复被 max_tokens 截断的 JSON"""
        # 找到最后一个完整的 ] 作为结束
        depth = 0
        in_str = False
        escape = False
        last_complete = 0

        for i, ch in enumerate(text):
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if ch == '"':
                in_str = not in_str
            if not in_str:
                if ch == '[':
                    depth += 1
                elif ch == ']':
                    depth -= 1
                    if depth == 0:
                        last_complete = i + 1
                elif ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1

        if last_complete > 0:
            text = text[:last_complete]
            return text

        # 没有完整闭合，手动修复: 去掉最后一个不完整的对象
        # 找到倒数第二个完整的 }, 截断到那里并补 ]
        last_obj_end = 0
        obj_depth = 0
        in_str = False
        escape = False

        for i, ch in enumerate(text):
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if ch == '"':
                in_str = not in_str
            if not in_str and ch == '}':
                obj_depth -= 1
                if obj_depth == 0:
                    last_obj_end = i + 1

        if last_obj_end > 0:
            text = text[:last_obj_end] + "\n]"
            return text

        # 最后手段: 关闭所有打开的结构
        if in_str:
            text += '"'
        text += ']'
        return text

    def _parse(self, text: str) -> List[VisionQuestion]:
        """解析题目分析结果"""
        text = self._clean_json(text)
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Vision JSON解析失败: {e}, text={text[:300]}")
            raw = None

        if isinstance(raw, list):
            results = [VisionQuestion(
                question_text=item.get("question_text", ""),
                student_answer=item.get("student_answer", ""),
                position=item.get("position", {}),
                question_type=item.get("question_type", "解答题"),
            ) for item in raw if isinstance(item, dict)]
            if results:
                logger.info(f"视觉分析解析成功: {len(results)} 道题")
            return results
        return []

    def _parse_grading(self, text: str) -> List[dict]:
        """解析批改结果，返回 grading dict 列表"""
        text = self._clean_json(text)
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Vision批改JSON解析失败: {e}, text={text[:500]}")
            raw = None

        if isinstance(raw, list):
            results = []
            for item in raw:
                if isinstance(item, dict):
                    score = float(item.get("score", 0))
                    max_s = float(item.get("max_score", 10))
                    results.append({
                        "question_no": str(item.get("question_no", "")),
                        "question_text": item.get("question_text", ""),
                        "student_answer": item.get("student_answer", ""),
                        "question_type": item.get("question_type", "解答题"),
                        "score": score,
                        "max_score": max_s,
                        "accuracy": round(score / max_s * 100, 1) if max_s > 0 else 0,
                        "result": item.get("result", "错误"),
                        "comment": item.get("comment", ""),
                        "analysis": item.get("analysis", ""),
                    })
            if results:
                logger.info(f"视觉批改解析成功: {len(results)} 道题")
            return results
        return []


vision_client = VisionClient()
