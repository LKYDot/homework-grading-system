from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from utils.database import get_db
from utils.security import create_access_token, verify_password, get_password_hash
from utils.deps import get_current_user
from models.user import User
from schemas.user import UserCreate, UserResponse, LoginRequest, TokenResponse
from utils.logger import logger
from datetime import timedelta
from config import settings

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    try:
        # 检查用户名是否已存在
        existing_user = db.query(User).filter(User.username == user.username).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="用户名已存在")

        # 检查邮箱是否已存在
        existing_email = db.query(User).filter(User.email == user.email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="邮箱已被注册")

        # 创建用户
        hashed_password = get_password_hash(user.password)
        new_user = User(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password,
            role=user.role,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        logger.info(f"用户注册成功: {user.username}")
        return new_user

    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"用户注册失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="用户注册失败")


@router.post("/login", response_model=TokenResponse)
async def login_user(login: LoginRequest, db: Session = Depends(get_db)):
    """用户登录"""
    try:
        # 查找用户
        user = db.query(User).filter(User.email == login.email).first()
        if not user:
            raise HTTPException(status_code=401, detail="邮箱或密码错误")
        if not user.is_active:
            raise HTTPException(status_code=401, detail="用户因违规已被禁用")

        # 验证密码
        if not verify_password(login.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="邮箱或密码错误")

        # 生成token
        access_token = create_access_token(
            data={"sub": user.username, "user_id": user.id},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        logger.info(f"用户登录成功: {user.username}")
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user,
        }

    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"用户登录失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="用户登录失败")


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """获取用户信息"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        return user

    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"获取用户信息失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取用户信息失败")


@router.put("/{user_id}/status")
async def update_user_status(
    user_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新用户状态（管理员功能）"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="权限不足")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.is_active = is_active
    db.commit()
    db.refresh(user)

    logger.info(f"用户状态更新: {user.username}, is_active={is_active}")
    return user
