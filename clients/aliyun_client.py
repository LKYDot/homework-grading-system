import json
import base64
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from config import settings
from utils.logger import logger

try:
    from aliyunsdkcore.client import AcsClient
    from aliyunsdkcore.acs_exception.exceptions import ClientException, ServerException
    
    try:
        from aliyunsdkocr.request.v20191230.RecognizeEduPaperCutRequest import RecognizeEduPaperCutRequest
        from aliyunsdkocr.request.v20191230.RecognizeEduQuestionOCRRequest import RecognizeEduQuestionOCRRequest
        ALIYUN_OCR_AVAILABLE = True
    except ImportError:
        try:
            from aliyunsdkocr.request import RecognizeEduPaperCutRequest
            from aliyunsdkocr.request import RecognizeEduQuestionOCRRequest
            ALIYUN_OCR_AVAILABLE = True
        except ImportError:
            ALIYUN_OCR_AVAILABLE = False
            RecognizeEduPaperCutRequest = None
            RecognizeEduQuestionOCRRequest = None
            logger.warning("阿里云OCR SDK不可用，将使用mock模式")
except ImportError:
    ALIYUN_OCR_AVAILABLE = False
    AcsClient = None
    ClientException = Exception
    ServerException = Exception
    RecognizeEduPaperCutRequest = None
    RecognizeEduQuestionOCRRequest = None
    logger.warning("阿里云SDK不可用，将使用mock模式")


class AliyunOCRClient:
    def __init__(self):
        if ALIYUN_OCR_AVAILABLE and AcsClient:
            self.client: Optional[AcsClient] = AcsClient(
                settings.ALIYUN_ACCESS_KEY_ID,
                settings.ALIYUN_ACCESS_KEY_SECRET,
                "cn-shanghai",
            )
            self.endpoint = settings.ALIYUN_OCR_ENDPOINT
        else:
            self.client = None
            self.endpoint = None

    def recognize_edu_paper_cut(self, image_path: str) -> List[Dict[str, Any]]:
        """调用阿里云试卷切题接口"""
        if not ALIYUN_OCR_AVAILABLE or not self.client:
            return self._mock_paper_cut(image_path)
            
        try:
            with open(image_path, "rb") as f:
                image_content = base64.b64encode(f.read()).decode("utf-8")

            if RecognizeEduPaperCutRequest:
                request = RecognizeEduPaperCutRequest()
                request.set_accept_format("json")
                request.set_ImageContent(image_content)

                response = self.client.do_action_with_exception(request)
                result = json.loads(response)

                if result.get("Code") != "OK":
                    raise Exception(f"试卷切题失败: {result.get('Message')}")

                questions = []
                for item in result.get("Data", {}).get("Questions", []):
                    questions.append(
                        {
                            "question_no": item.get("QuestionNo"),
                            "x1": item.get("X1"),
                            "y1": item.get("Y1"),
                            "x2": item.get("X2"),
                            "y2": item.get("Y2"),
                        }
                    )

                logger.info(f"试卷切题完成，共识别到{len(questions)}道题")
                return questions
            else:
                return self._mock_paper_cut(image_path)

        except (ClientException, ServerException) as e:
            logger.error(f"阿里云API调用失败: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"试卷切题失败: {str(e)}", exc_info=True)
            raise

    def recognize_edu_question_ocr(self, image_path: str) -> Dict[str, Any]:
        """调用阿里云题目OCR接口"""
        if not ALIYUN_OCR_AVAILABLE or not self.client:
            return self._mock_question_ocr(image_path)
            
        try:
            with open(image_path, "rb") as f:
                image_content = base64.b64encode(f.read()).decode("utf-8")

            if RecognizeEduQuestionOCRRequest:
                request = RecognizeEduQuestionOCRRequest()
                request.set_accept_format("json")
                request.set_ImageContent(image_content)
                request.set_WithAnswer(True)

                response = self.client.do_action_with_exception(request)
                result = json.loads(response)

                if result.get("Code") != "OK":
                    raise Exception(f"题目OCR失败: {result.get('Message')}")

                data = result.get("Data", {})
                ocr_result = {
                    "question_text": data.get("QuestionText", ""),
                    "student_answer": data.get("AnswerText", ""),
                    "question_type": data.get("QuestionType", ""),
                    "raw_response": data,
                }

                logger.debug(f"题目OCR完成: {ocr_result['question_text'][:30]}...")
                return ocr_result
            else:
                return self._mock_question_ocr(image_path)

        except (ClientException, ServerException) as e:
            logger.error(f"阿里云API调用失败: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"题目OCR失败: {str(e)}", exc_info=True)
            raise

    def _mock_paper_cut(self, image_path: str) -> List[Dict[str, Any]]:
        """Mock试卷切题结果"""
        logger.info(f"使用mock模式进行试卷切题: {image_path}")
        return [
            {"question_no": "1", "x1": 50, "y1": 50, "x2": 550, "y2": 150},
            {"question_no": "2", "x1": 50, "y1": 180, "x2": 550, "y2": 280},
            {"question_no": "3", "x1": 50, "y1": 310, "x2": 550, "y2": 410},
        ]

    def _mock_question_ocr(self, image_path: str) -> Dict[str, Any]:
        """Mock题目OCR结果"""
        logger.info(f"使用mock模式进行题目OCR: {image_path}")
        return {
            "question_text": "计算：2 + 3 = ?",
            "student_answer": "5",
            "question_type": "计算题",
            "raw_response": {},
        }


aliyun_ocr_client = AliyunOCRClient()