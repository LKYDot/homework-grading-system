from clients.aliyun_client import aliyun_ocr_client
from utils.logger import logger


class OCRService:
    def __init__(self):
        self.aliyun_client = aliyun_ocr_client

    def recognize_paper(self, image_path: str) -> list:
        return self.aliyun_client.recognize_edu_paper_cut(image_path)

    def recognize_question(self, image_path: str) -> dict:
        return self.aliyun_client.recognize_edu_question_ocr(image_path)


ocr_service = OCRService()
