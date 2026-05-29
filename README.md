# 中小学作业智能批改系统

基于大模型的中小学作业智能批改系统后端API。

## 功能特性

- ✅ 用户管理（注册、登录、认证）
- ✅ 作业上传与处理
- ✅ 图像预处理（压缩、旋转、增强）
- ✅ 试卷切题（自动识别题目区域）
- ✅ OCR识别（题目内容和学生答案）
- ✅ 智能批改（规则引擎 + 大模型）
- ✅ 批改结果查询
- ✅ 统计分析（用户统计、全局统计）

## 技术栈

- **框架**: FastAPI
- **数据库**: MySQL 
- **异步任务**: Celery + Redis
- **日志**: Loguru
- **认证**: JWT
- **OCR**: 阿里云OCR（支持Mock模式）
- **大模型**: 通义千问（支持Mock模式）

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 并修改配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置数据库连接、API密钥等。

### 3. 启动服务

```bash
# 启动FastAPI服务
python main.py

# 或使用uvicorn
uvicorn main:app --reload --port 8000
```

### 4. 启动Celery（异步任务）

```bash
celery -A celery_app worker --loglevel=info --queue=homework
```

## API文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 项目结构

```
homework-grading-system/
├── app/                    # FastAPI应用
│   └── v1/                 # API路由（v1版本）
│       ├── homework.py     # 作业管理接口
│       ├── user.py         # 用户管理接口
│       └── statistics.py   # 统计分析接口
├── clients/                # 外部服务客户端
│   ├── aliyun_client.py    # 阿里云OCR客户端
│   └── tongyi_client.py    # 通义千问客户端
├── models/                 # SQLAlchemy模型
│   ├── base.py             # 基础模型
│   ├── homework.py         # 作业相关模型
│   ├── user.py             # 用户模型
│   └── knowledge.py        # 知识点模型
├── schemas/                # Pydantic数据模型
│   ├── common.py           # 通用响应模型
│   ├── homework.py         # 作业相关模型
│   └── user.py             # 用户相关模型
├── services/               # 业务逻辑服务
│   ├── task_service.py     # 任务管理服务
│   ├── ocr_service.py      # OCR服务
│   ├── llm_service.py      # 大模型服务
│   ├── image_service.py    # 图像处理服务
│   └── rule_engine.py      # 规则引擎
├── tasks/                  # Celery异步任务
│   └── homework_tasks.py   # 作业处理任务
├── utils/                  # 工具函数
│   ├── database.py         # 数据库连接
│   ├── logger.py           # 日志配置
│   ├── exceptions.py       # 异常类
│   └── security.py         # 安全工具
├── celery_app.py           # Celery配置
├── config.py               # 配置管理
├── main.py                 # FastAPI入口
└── requirements.txt        # 依赖列表
```

## API接口

### 用户管理

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/v1/users/register | 用户注册 |
| POST | /api/v1/users/login | 用户登录 |
| GET | /api/v1/users/{user_id} | 获取用户信息 |

### 作业管理

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/v1/homework/upload | 上传作业 |
| GET | /api/v1/homework/{task_id} | 获取作业状态 |
| GET | /api/v1/homework/{task_id}/result | 获取批改结果 |
| GET | /api/v1/homework/list | 获取作业列表 |
| DELETE | /api/v1/homework/{task_id} | 删除作业 |

### 统计分析

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/v1/statistics/user/{user_id} | 用户统计 |
| GET | /api/v1/statistics/global | 全局统计 |

## 配置说明

### 环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| HOST | 服务地址 | 0.0.0.0 |
| PORT | 服务端口 | 8000 |
| DEBUG | 调试模式 | False |
| DATABASE_URL | 数据库连接URL | sqlite:///./homework_grading.db |
| REDIS_URL | Redis连接URL | redis://localhost:6379/0 |
| ALIYUN_ACCESS_KEY_ID | 阿里云Access Key | - |
| ALIYUN_ACCESS_KEY_SECRET | 阿里云Secret Key | - |
| DASHSCOPE_API_KEY | 通义千问API Key | - |
| JWT_SECRET_KEY | JWT密钥 | - |

### Mock模式

当缺少阿里云OCR或通义千问API密钥时，系统会自动切换到Mock模式，使用模拟数据进行演示。

## 开发指南

### 添加新API

1. 在 `app/v1/` 目录下创建新的路由文件
2. 在 `schemas/` 目录下定义数据模型
3. 在 `services/` 目录下实现业务逻辑
4. 在 `main.py` 中注册路由

### 添加新服务

1. 在 `services/` 目录下创建新的服务文件
2. 在 `services/__init__.py` 中导出服务

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！
