from sqlalchemy import Column, BigInteger, String, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel


class User(BaseModel):
    __tablename__ = "user"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, comment="用户名")
    email = Column(String(100), unique=True, nullable=False, comment="邮箱")
    hashed_password = Column(String(255), nullable=False, comment="密码哈希")
    full_name = Column(String(100), comment="真实姓名")
    role = Column(String(20), nullable=False, default="student", comment="角色：student/teacher/admin")
    is_active = Column(Boolean, default=True, comment="是否激活")

    homework_tasks = relationship("HomeworkTask", back_populates="user")
