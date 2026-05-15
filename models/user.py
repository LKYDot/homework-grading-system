from sqlalchemy import BigInteger, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import BaseModel


class User(BaseModel):
    """
    用户表
    """

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="用户名")
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, comment="邮箱")
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码哈希")
    full_name: Mapped[str | None] = mapped_column(String(100), comment="真实姓名")
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="student",
        comment="角色：student/teacher/admin",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否激活")

    homework_tasks = relationship("HomeworkTask", back_populates="user")
    reviewed_results = relationship("GradingResult", back_populates="reviewer")