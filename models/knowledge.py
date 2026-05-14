from sqlalchemy import Column, BigInteger, String, Text, DECIMAL
from .base import BaseModel


class KnowledgePoint(BaseModel):
    __tablename__ = "knowledge_point"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    subject = Column(String(20), nullable=False, comment="学科")
    grade = Column(String(20), nullable=False, comment="年级")
    chapter = Column(String(100), comment="章节")
    knowledge_point = Column(String(200), nullable=False, comment="知识点")
    difficulty = Column(DECIMAL(2, 1), default=3.0, comment="难度系数")
    description = Column(Text, comment="知识点描述")
