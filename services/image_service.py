import cv2
import numpy as np
import os
import uuid
from PIL import Image
from config import settings
from utils.logger import logger


class ImageService:
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        os.makedirs(self.upload_dir, exist_ok=True)

    def preprocess_image(self, image_path: str) -> str:
        """图像预处理：EXIF校正、灰度化、边缘检测、透视变换、二值化"""
        try:
            # 读取图片并校正EXIF方向
            img = Image.open(image_path)
            img = self._correct_exif_orientation(img)
            img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

            # 灰度化
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

            # 自适应直方图均衡化
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)

            # 高斯滤波去噪
            blur = cv2.GaussianBlur(gray, (5, 5), 0)

            # 边缘检测
            edged = cv2.Canny(blur, 75, 200)

            # 查找最大轮廓（试卷区域）
            contours, _ = cv2.findContours(
                edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
            )
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

            screen_cnt = None
            for c in contours:
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.02 * peri, True)
                if len(approx) == 4:
                    screen_cnt = approx
                    break

            if screen_cnt is not None:
                # 透视变换
                warped = self._four_point_transform(gray, screen_cnt.reshape(4, 2))
            else:
                # 如果找不到轮廓，使用原图
                warped = gray

            # 自适应阈值二值化
            thresh = cv2.adaptiveThreshold(
                warped, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )

            # 保存预处理后的图片
            processed_filename = f"processed_{uuid.uuid4().hex}.jpg"
            processed_path = os.path.join(self.upload_dir, processed_filename)
            cv2.imwrite(processed_path, thresh)

            logger.info(f"图像预处理完成: {processed_path}")
            return processed_path

        except Exception as e:
            logger.error(f"图像预处理失败: {str(e)}", exc_info=True)
            raise

    def _correct_exif_orientation(self, img: Image.Image) -> Image.Image:
        """校正EXIF方向"""
        try:
            exif = img._getexif()
            if exif is not None:
                orientation = exif.get(0x0112)
                if orientation == 3:
                    img = img.rotate(180, expand=True)
                elif orientation == 6:
                    img = img.rotate(270, expand=True)
                elif orientation == 8:
                    img = img.rotate(90, expand=True)
        except (AttributeError, KeyError, IndexError):
            pass
        return img

    def _four_point_transform(self, image: np.ndarray, pts: np.ndarray) -> np.ndarray:
        """四点透视变换"""
        rect = np.zeros((4, 2), dtype="float32")

        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]

        tl, tr, br, bl = rect

        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))

        heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        maxHeight = max(int(heightA), int(heightB))

        dst = np.array(
            [
                [0, 0],
                [maxWidth - 1, 0],
                [maxWidth - 1, maxHeight - 1],
                [0, maxHeight - 1],
            ],
            dtype="float32",
        )

        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))

        return warped

    def crop_question_blocks(self, image_path: str, blocks: list) -> list:
        """根据切题结果裁剪单题图片"""
        img = cv2.imread(image_path)
        cropped_blocks = []

        for block in blocks:
            x1, y1, x2, y2 = block["x1"], block["y1"], block["x2"], block["y2"]
            question_img = img[y1:y2, x1:x2]

            cropped_filename = f"question_{uuid.uuid4().hex}.jpg"
            cropped_path = os.path.join(self.upload_dir, cropped_filename)
            cv2.imwrite(cropped_path, question_img)

            cropped_blocks.append(
                {
                    "question_no": block["question_no"],
                    "image_path": cropped_path,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                }
            )

        return cropped_blocks


image_service = ImageService()
