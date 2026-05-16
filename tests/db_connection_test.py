# test_database.py
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from config import settings


def test_database_connection():
    """测试数据库连接和基本操作"""
    print("=" * 60)
    print("          MySQL 数据库连接测试")
    print("=" * 60)

    all_passed = True

    # 1. 测试引擎创建
    print("\n[1/5] 创建数据库引擎")
    try:
        engine = create_engine(
            settings.DATABASE_URL,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_recycle=settings.DB_POOL_RECYCLE,
            echo=False,
        )
        print(f"     ✅ 引擎创建成功")
        print(f"     连接字符串: {settings.DATABASE_URL}")
    except Exception as e:
        print(f"     ❌ 引擎创建失败: {e}")
        all_passed = False
        return

    # 2. 测试连接
    print("\n[2/5] 测试数据库连接")
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            value = result.scalar()
            if value == 1:
                print("     ✅ 连接成功")
            else:
                print("     ❌ 连接异常")
                all_passed = False
    except Exception as e:
        print(f"     ❌ 连接失败: {e}")
        all_passed = False

    # 3. 测试会话
    print("\n[3/5] 测试数据库会话")
    try:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        # 测试查询
        result = db.execute(text("SELECT VERSION()"))
        version = result.scalar()
        print(f"     ✅ 会话创建成功")
        print(f"     MySQL 版本: {version}")

        db.close()
    except Exception as e:
        print(f"     ❌ 会话测试失败: {e}")
        all_passed = False

    # 4. 测试表创建
    print("\n[4/5] 测试表创建")
    try:
        from models.base import Base
        from models import user, homework, knowledge

        # 创建所有表
        Base.metadata.create_all(bind=engine)
        print("     ✅ 表创建成功")

        # 检查表是否存在

        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"     当前数据库表: {', '.join(tables)}")

    except Exception as e:
        print(f"     ❌ 表创建失败: {e}")
        all_passed = False

    # 5. 测试数据插入和查询
    print("\n[5/5] 测试数据操作")
    try:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        # 创建测试用户
        from models.user import User

        test_user = User(
            username="test_user",
            email="test@example.com",
            hashed_password="test_password",
            full_name="测试用户",
            role="student",
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        print(f"     ✅ 数据插入成功，用户ID: {test_user.id}")

        # 查询测试
        user_count = db.query(User).count()
        print(f"     ✅ 用户总数: {user_count}")

        # 清理测试数据
        db.delete(test_user)
        db.commit()
        print("     ✅ 测试数据已清理")

        db.close()
    except Exception as e:
        print(f"     ❌ 数据操作失败: {e}")
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过！MySQL 可以正常为项目服务")
    else:
        print("⚠️ 部分测试失败，请检查数据库配置")
    print("=" * 60)


if __name__ == "__main__":
    test_database_connection()
