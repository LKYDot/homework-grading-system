# 中小学作业智能批改系统

基于 DeepSeek-v4-pro 大模型的中小学作业智能批改系统后端 API。

## 功能特性

- 用户管理（注册、登录、JWT 认证）
- 作业上传与异步处理（Celery + Redis）
- 图像预处理（EXIF 校正 → 灰度化 → CLAHE 增强 → 透视纠偏）
- 试卷切题（阿里云 RecognizeEduPaperCut，自动识别题目区域）
- OCR 识别（阿里云 RecognizeEduQuestionOcr，题干 + 学生答案 + 题型）
- 智能批改（规则引擎精确匹配 + DeepSeek-v4-pro 语义理解）
- 统计分析（用户统计、全局统计）
- Mock 模式（无外部 API 密钥时自动降级，方便本地开发）

## 技术栈

- **框架**: FastAPI + SQLAlchemy + Pydantic
- **数据库**: MySQL 8.0+
- **异步任务**: Celery + Redis
- **日志**: Loguru
- **认证**: JWT (python-jose + bcrypt)
- **OCR**: 阿里云 OCR（支持 Mock 模式）
- **大模型**: DeepSeek-v4-pro（通过阿里云百炼 DashScope API 调用，支持 Mock 模式）
- **前端**: Vue 3

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入数据库连接和 API 密钥：

```env
# 必需：数据库
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/homework_db?charset=utf8mb4

# 必需：Redis
REDIS_URL=redis://localhost:6379/0

# 可选：阿里云 OCR（不填则自动使用 Mock 模式）
ALIYUN_ACCESS_KEY_ID=your_key
ALIYUN_ACCESS_KEY_SECRET=your_secret

# 可选：DeepSeek 大模型（不填则自动使用 Mock 模式）
DASHSCOPE_API_KEY=your_dashscope_api_key
LLM_MODEL=deepseek-v4-pro
```

### 3. 启动 Redis

```bash
redis-server
```

### 4. 启动 FastAPI

```bash
python main.py
# 或
uvicorn main:app --reload --port 8000
```

### 5. 启动 Celery Worker（异步任务）

```bash
# Windows
celery -A celery_app worker -Q homework -l info -P solo

# Linux / macOS
celery -A celery_app worker -Q homework -l info -P prefork
```

## API 文档

启动服务后访问：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- 详细接口文档：[API_DOCS.md](API_DOCS.md)

## 项目结构

```
homework-grading-system/
├── app/                        # FastAPI 应用
│   └── v1/                     # API 路由（v1 版本）
│       ├── homework.py         # 作业管理接口
│       ├── user.py             # 用户管理接口
│       └── statistics.py       # 统计分析接口
├── clients/                    # 外部服务客户端
│   ├── aliyun_client.py        # 阿里云 OCR 客户端
│   └── deepseek_client.py      # DeepSeek 大模型客户端
├── models/                     # SQLAlchemy 模型
│   ├── base.py                 # 基础模型
│   ├── homework.py             # 作业相关模型
│   ├── user.py                 # 用户模型
│   └── knowledge.py            # 知识点模型
├── schemas/                    # Pydantic 数据模型
│   ├── common.py               # 通用响应模型
│   ├── homework.py             # 作业相关模型
│   └── user.py                 # 用户相关模型
├── services/                   # 业务逻辑服务
│   ├── task_service.py         # 任务管理服务
│   ├── ocr_service.py          # OCR 服务
│   ├── llm_service.py          # 大模型批改服务
│   ├── image_service.py        # 图像处理服务
│   └── rule_engine.py          # 规则引擎
├── tasks/                      # Celery 异步任务
│   └── homework_tasks.py       # 作业处理任务
├── celery_app.py               # Celery 配置
├── config.py                   # 配置管理
├── main.py                     # FastAPI 入口
└── requirements.txt            # 依赖列表
```

## API 接口概览

### 用户管理

| 方法 | 路径 | 认证 | 描述 |
|------|------|------|------|
| POST | /api/v1/users/register | 无 | 用户注册 |
| POST | /api/v1/users/login | 无 | 用户登录 |
| GET | /api/v1/users/{user_id} | 无 | 获取用户信息 |
| PUT | /api/v1/users/{user_id}/status | 管理员 | 启用/禁用用户 |

### 作业管理

| 方法 | 路径 | 认证 | 描述 |
|------|------|------|------|
| POST | /api/v1/homework/upload | 无 | 上传作业图片 |
| GET | /api/v1/homework/status/{task_id} | 无 | 查询任务状态 |
| GET | /api/v1/homework/result/{task_id} | 无 | 查询批改结果 |

### 统计分析

| 方法 | 路径 | 认证 | 描述 |
|------|------|------|------|
| GET | /api/v1/statistics/user/{user_id} | 无 | 用户统计 |
| GET | /api/v1/statistics/global | 无 | 全局统计 |

## 配置说明

### 环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| HOST | 服务地址 | 0.0.0.0 |
| PORT | 服务端口 | 8000 |
| DEBUG | 调试模式 | false |
| DATABASE_URL | 数据库连接 URL | mysql+pymysql://... |
| REDIS_URL | Redis 连接 URL | redis://localhost:6379/0 |
| ALIYUN_ACCESS_KEY_ID | 阿里云 Access Key | - |
| ALIYUN_ACCESS_KEY_SECRET | 阿里云 Secret Key | - |
| DASHSCOPE_API_KEY | 阿里云百炼 API Key | - |
| LLM_MODEL | 大模型名称 | deepseek-v4-pro |
| JWT_SECRET_KEY | JWT 签名密钥 | - |
| ACCESS_TOKEN_EXPIRE_MINUTES | Token 有效期（分钟） | 120 |

### DeepSeek-v4-pro 重要约束

**该模型不支持 `system` 角色**，messages 中只能使用 `user` 和 `assistant` 角色。所有系统提示词必须合并到 `user` 消息的 content 开头：

```python
# 错误：不支持 system 角色
messages = [
    {"role": "system", "content": "你是一名批改老师..."},
    {"role": "user", "content": "请批改作业..."},
]

# 正确：合并到 user content
messages = [
    {"role": "user", "content": "你是一名批改老师，输出JSON格式。\n\n请批改作业..."},
]
```

### Mock 模式

当缺少阿里云 OCR 密钥或 DashScope API 密钥时，系统会自动切换到 Mock 模式，使用模拟数据进行演示，方便本地开发和调试。

## 批改流程

```
上传图片 → 图像预处理 → 试卷切题 → 逐题OCR → 智能批改 → 返回结果
                                              │
                              ┌───────────────┴───────────────┐
                              ▼                               ▼
                    规则引擎精确匹配                    DeepSeek-v4-pro
                    (选择/判断/填空/计算)              (解答题/作文等主观题)
```

## 开发指南

### 添加新 API

1. 在 `app/v1/` 目录下创建新的路由文件
2. 在 `schemas/` 目录下定义数据模型
3. 在 `services/` 目录下实现业务逻辑
4. 在 `main.py` 中注册路由

### 添加新的大模型

1. 在 `clients/` 目录下创建新的客户端文件
2. 在 `services/llm_service.py` 中集成
3. 在 `config.py` 中添加相关配置

## 许可证

MIT License
