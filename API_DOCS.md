# 作业智能批改系统 — API 接口文档

> 版本：2.0.0 | 基础路径：`http://localhost:8000/api/v1`

---

## 目录

1. [项目概述](#1-项目概述)
2. [通用约定](#2-通用约定)
3. [用户模块](#3-用户模块)
4. [作业模块](#4-作业模块)
5. [模型模块](#5-模型模块)
6. [统计模块](#6-统计模块)
7. [数据模型](#7-数据模型)
8. [异步任务流程](#8-异步任务流程)
9. [外部服务集成](#9-外部服务集成)
10. [部署与配置](#10-部署与配置)
11. [错误码表](#11-错误码表)

---

## 1. 项目概述

作业智能批改系统是一套基于 AI 的中小学作业自动批改平台，支持学生上传手写作业图片，系统自动进行 OCR 识别、题目切分、答案匹配和大模型批改，最终返回逐题评分与评语。

**核心能力：**

| 能力 | 技术实现 |
|------|----------|
| 图像预处理 | PIL：EXIF 校正 → 灰度化 → 图像增强 |
| 试卷切题 | 阿里云 RecognizeEduPaperCut，返回每题坐标 |
| 题目 OCR | 阿里云 RecognizeEduQuestionOcr，识别题干 + 学生答案 + 题型 |
| 智能批改 | 规则引擎（选择/判断/填空/计算题）+ 大模型（主观题） |
| 异步任务 | Celery + Redis，支持自动重试 |

**技术栈：** FastAPI + SQLAlchemy + Celery + Redis + MySQL + Vue 3

---

## 2. 通用约定

### 2.1 基础路径

```
http://localhost:8000/api/v1
```

### 2.2 统一响应格式

所有业务接口返回以下 JSON 结构：

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | int | 状态码，200 表示成功 |
| `message` | string | 提示信息 |
| `data` | object/null | 业务数据 |

### 2.3 错误响应

```json
{
  "code": 400,
  "message": "错误描述信息",
  "data": null
}
```

HTTP 状态码：400（业务异常）、401（未认证）、403（无权限）、500（服务器错误）。

### 2.4 日期时间格式

所有日期时间字段使用 ISO 8601 格式：`YYYY-MM-DDTHH:MM:SS`

### 2.5 健康检查

**`GET /status`** — 无认证

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "status": "ok",
    "service": "作业智能批改系统",
    "version": "2.0.0"
  }
}
```

---

## 3. 用户模块

基础路径：`/api/v1/users`

### 3.1 用户注册

```http
POST /api/v1/users/register
Content-Type: application/json
```

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `username` | string | 是 | 用户名，唯一，长度 3-50 |
| `email` | string | 是 | 邮箱，唯一，需合法格式 |
| `password` | string | 是 | 明文密码，长度 6-128 |
| `full_name` | string | 否 | 真实姓名 |
| `role` | string | 否 | 角色，默认 `student`，可选 `teacher`、`admin` |

**请求示例：**

```json
{
  "username": "zhangsan",
  "email": "zhangsan@example.com",
  "password": "123456",
  "full_name": "张三",
  "role": "student"
}
```

**响应示例：**

```json
{
  "code": 200,
  "message": "注册成功",
  "data": {
    "id": 1,
    "username": "zhangsan",
    "email": "zhangsan@example.com",
    "full_name": "张三",
    "role": "student",
    "is_active": true,
    "created_at": "2026-05-28T10:30:00"
  }
}
```

---

### 3.2 用户登录

```http
POST /api/v1/users/login
Content-Type: application/json
```

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `username` | string | 是 | 用户名或邮箱 |
| `password` | string | 是 | 明文密码 |

**请求示例：**

```json
{
  "username": "zhangsan",
  "password": "123456"
}
```

**响应示例：**

```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 7200,
    "user": {
      "id": 1,
      "username": "zhangsan",
      "email": "zhangsan@example.com",
      "full_name": "张三",
      "role": "student",
      "is_active": true,
      "created_at": "2026-05-28T10:30:00"
    }
  }
}
```

> Token 有效期：120 分钟（可配置 `ACCESS_TOKEN_EXPIRE_MINUTES`）。后续需要认证的请求在 `Authorization` 头中携带 `Bearer <access_token>`。

---

### 3.3 获取用户信息

```http
GET /api/v1/users/{user_id}
Authorization: Bearer <access_token>
```

**路径参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `user_id` | int | 用户 ID |

**响应：** 同 3.1 注册响应的 `data` 字段。

---

### 3.4 更新用户状态（管理员）

```http
PUT /api/v1/users/{user_id}/status
Authorization: Bearer <access_token>
Content-Type: application/json
```

**认证要求：** 必须登录，且 `role == "admin"`。

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `is_active` | bool | 是 | 启用或禁用用户 |

**请求示例：**

```json
{
  "is_active": true
}
```

**响应示例：**

```json
{
  "code": 200,
  "message": "状态更新成功",
  "data": null
}
```

---

## 4. 作业模块

基础路径：`/api/v1/homework`

### 4.1 上传作业

```http
POST /api/v1/homework/upload
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**认证要求：** 必须登录。

**表单参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | file | 是 | 作业图片，支持 jpg/jpeg/png/gif/bmp，最大 10MB |
| `subject` | string | 是 | 学科（`math`、`chinese`、`english`、`physics`、`chemistry`） |
| `grade` | string | 是 | 年级（`grade1` ~ `grade9`） |

**请求示例（curl）：**

```bash
curl -X POST http://localhost:8000/api/v1/homework/upload \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@homework.jpg" \
  -F "subject=math" \
  -F "grade=grade3"
```

**响应示例：**

```json
{
  "code": 200,
  "message": "作业上传成功，正在处理中",
  "data": {
    "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }
}
```

> 上传成功后立即返回 `task_id`，批改在后台异步执行。客户端应通过状态查询接口轮询进度。

---

### 4.2 分析作业（大模型直接分析）

```http
POST /api/v1/homework/analyze
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**认证要求：** 必须登录。

**表单参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | file | 是 | 作业图片，支持 jpg/jpeg/png/gif/bmp，最大 10MB |
| `subject` | string | 是 | 学科 |
| `grade` | string | 是 | 年级 |
| `model` | string | 否 | 模型名称，默认使用配置的视觉模型 |

**响应示例：**

```json
{
  "code": 200,
  "message": "分析任务已创建",
  "data": {
    "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }
}
```

---

### 4.3 查询任务状态

```http
GET /api/v1/homework/status/{task_id}
Authorization: Bearer <access_token>
```

**认证要求：** 必须登录，且只能查询自己的任务。

**路径参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `task_id` | string | 上传接口返回的任务 ID |

**响应示例：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "status": "OCRING",
    "created_at": "2026-05-28T10:30:00",
    "updated_at": "2026-05-28T10:30:15"
  }
}
```

**状态流转：**

| 状态 | 说明 |
|------|------|
| `PENDING` | 已创建，等待处理 |
| `PROCESSING` | 开始处理 |
| `PREPROCESSING` | 图像预处理中 |
| `CUTTING` | 试卷切题中 |
| `OCRING` | 题目 OCR 识别中 |
| `GRADING` | 大模型批改中 |
| `SUCCESS` | 批改完成 |
| `FAILED` | 处理失败（自动重试 3 次后最终失败） |

> 前端建议每 2-3 秒轮询一次，直到状态变为 `SUCCESS` 或 `FAILED`。

---

### 4.4 查询批改结果

```http
GET /api/v1/homework/result/{task_id}
Authorization: Bearer <access_token>
```

**认证要求：** 必须登录，且只能查询自己的任务。

**路径参数：** 同 4.3。

**响应示例：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "subject": "math",
    "grade": "grade3",
    "total_score": 85.5,
    "total_max_score": 100.0,
    "accuracy": 85.5,
    "created_at": "2026-05-28T10:30:00",
    "results": [
      {
        "question_block_id": 10,
        "question_no": "1",
        "question_text": "计算：2 + 3 = ?",
        "student_answer": "5",
        "score": 10.0,
        "max_score": 10.0,
        "result": "正确",
        "comment": "答案完全正确",
        "analysis": "本题考查基本加法运算，学生掌握良好",
        "confidence": 0.95
      },
      {
        "question_block_id": 11,
        "question_no": "2",
        "question_text": "解方程：2x + 5 = 15",
        "student_answer": "x = 4",
        "score": 5.0,
        "max_score": 10.0,
        "result": "部分正确",
        "comment": "解题思路正确，但计算有误",
        "analysis": "正确答案应为 x = 5，学生在移项时出现计算错误",
        "confidence": 0.88
      },
      {
        "question_block_id": 12,
        "question_no": "3",
        "question_text": "简述光合作用的过程",
        "student_answer": "植物吸收阳光制造养分",
        "score": 7.0,
        "max_score": 10.0,
        "result": "部分正确",
        "comment": "回答基本正确，但不够完整",
        "analysis": "光合作用包括光反应和暗反应两个阶段...",
        "confidence": 0.85
      }
    ]
  }
}
```

**批改结果字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `question_block_id` | int | 题目块 ID |
| `question_no` | string | 题号 |
| `question_text` | string | 题目文本 |
| `student_answer` | string | 学生答案 |
| `score` | float | 实际得分 |
| `max_score` | float | 满分 |
| `result` | string | 批改结论：`正确` / `部分正确` / `错误` |
| `comment` | string | 简短评语 |
| `analysis` | string | 详细分析 |
| `confidence` | float | 置信度（0.0 ~ 1.0） |

---

### 4.5 查询作业列表

```http
GET /api/v1/homework/list?page=1&page_size=20
Authorization: Bearer <access_token>
```

**认证要求：** 必须登录。

**查询参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `page` | int | 否 | 1 | 页码 |
| `page_size` | int | 否 | 20 | 每页数量 |

**响应示例：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "subject": "math",
        "grade": "grade3",
        "status": "SUCCESS",
        "total_score": 85.5,
        "total_max_score": 100.0,
        "accuracy": 85.5,
        "created_at": "2026-05-28T10:30:00"
      }
    ],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

---

## 5. 模型模块

基础路径：`/api/v1/models`

### 5.1 获取模型列表

```http
GET /api/v1/models
Authorization: Bearer <access_token>
```

**认证要求：** 必须登录。

**响应示例：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "models": [
      {
        "name": "qwen-turbo",
        "provider": "dashscope",
        "type": "text",
        "model_id": "qwen-turbo",
        "enabled": true
      },
      {
        "name": "qwen-vl",
        "provider": "dashscope",
        "type": "vision",
        "model_id": "qwen-vl-plus",
        "enabled": true
      }
    ]
  }
}
```

**模型类型说明：**

| 类型 | 说明 | 适用场景 |
|------|------|----------|
| `text` | 文本模型 | 纯文本批改、评语生成 |
| `vision` | 视觉模型 | 图片分析、直接识别题目 |

---

## 6. 统计模块

基础路径：`/api/v1/statistics`

### 6.1 用户统计

```http
GET /api/v1/statistics/user/{user_id}
Authorization: Bearer <access_token>
```

**认证要求：** 必须登录，且只能查询自己的统计。

**响应示例：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total_tasks": 25,
    "completed_tasks": 22,
    "average_score": 87.3,
    "average_accuracy": 87.3,
    "recent_scores": [90, 85, 92, 78, 88, 95, 83]
  }
}
```

---

### 6.2 全局统计

```http
GET /api/v1/statistics/global
Authorization: Bearer <access_token>
```

**认证要求：** 必须登录，且 `role == "admin"`。

**响应示例：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total_users": 150,
    "total_tasks": 1200,
    "completed_tasks": 1050,
    "average_score": 82.6,
    "average_accuracy": 82.6
  }
}
```

---

## 7. 数据模型

### 7.1 核心表结构

#### `user` — 用户表

| 列 | 类型 | 说明 |
|----|------|------|
| id | BIGINT PK | 自增主键 |
| username | VARCHAR(50) UNIQUE | 用户名 |
| email | VARCHAR(100) UNIQUE | 邮箱 |
| hashed_password | VARCHAR(255) | bcrypt 哈希 |
| full_name | VARCHAR(100) | 真实姓名 |
| role | VARCHAR(20) | student / teacher / admin |
| is_active | BOOLEAN | 是否激活 |
| created_at | DATETIME | 注册时间 |
| updated_at | DATETIME | 更新时间 |

#### `homework_task` — 作业任务表

| 列 | 类型 | 说明 |
|----|------|------|
| id | BIGINT PK | 自增主键 |
| task_id | VARCHAR(64) UNIQUE | 业务任务 ID（UUID） |
| user_id | BIGINT FK | 关联用户 |
| subject | VARCHAR(20) | 学科 |
| grade | VARCHAR(20) | 年级 |
| status | VARCHAR(20) | 状态 |
| total_score | DECIMAL(5,2) | 总分 |
| total_max_score | DECIMAL(5,2) | 满分 |
| accuracy | DECIMAL(5,2) | 正确率 |
| grading_mode | VARCHAR(20) | 批改模式 |
| error_message | TEXT | 失败时的错误信息 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

#### `grading_result` — 批改结果表

| 列 | 类型 | 说明 |
|----|------|------|
| id | BIGINT PK | 自增主键 |
| task_id | VARCHAR(64) FK | 关联任务 |
| question_block_id | BIGINT | 题目块 ID |
| question_no | VARCHAR(20) | 题号 |
| question_text | TEXT | 题目文本 |
| student_answer | TEXT | 学生答案 |
| score | DECIMAL(5,2) | 得分 |
| max_score | DECIMAL(5,2) | 满分 |
| result | VARCHAR(20) | 正确 / 部分正确 / 错误 |
| comment | TEXT | 评语 |
| analysis | TEXT | 解题分析 |
| confidence | DECIMAL(3,2) | 置信度 |
| created_at | DATETIME | 创建时间 |

---

## 8. 异步任务流程

### 8.1 Celery 配置

| 配置项 | 值 |
|--------|-----|
| Broker | Redis（`redis://localhost:6379/1`） |
| Result Backend | Redis（`redis://localhost:6379/2`） |
| 序列化 | JSON |
| 队列 | `homework` |
| 超时 | 300 秒 |
| 最大重试 | 3 次（间隔 5 秒） |

### 8.2 任务流水线

```
PENDING → PROCESSING → PREPROCESSING → CUTTING → OCRING → GRADING → SUCCESS
                                      ↓ (异常)
                                   FAILED → retry (最多3次)
```

### 8.3 启动 Worker

```bash
celery -A celery_app worker -Q homework -l info -P solo
```

> Windows 下必须使用 `-P solo`，Linux/Mac 可使用 `-P prefork`。

---

## 9. 外部服务集成

### 9.1 阿里云 OCR

**SDK：** `alibabacloud-ocr-api20210707==3.1.3`

**接口：**

| 接口 | 用途 | 输入 | 输出 |
|------|------|------|------|
| `RecognizeEduPaperCut` | 试卷切题 | 作业图片 | 每题坐标 + 题号 |
| `RecognizeEduQuestionOcr` | 单题 OCR | 裁剪后的题目图片 | 题干文本 + 学生答案 + 题型 |

**配置项：**

```env
ALIYUN_ACCESS_KEY_ID=your_key
ALIYUN_ACCESS_KEY_SECRET=your_secret
ALIYUN_OCR_ENDPOINT=ocr-api.cn-shanghai.aliyuncs.com
ENABLE_ALIYUN_OCR=true
```

### 9.2 OpenAI 兼容接口

系统通过 OpenAI 兼容接口调用大模型，支持多种模型提供商。

**支持的端点：**

| 提供商 | 端点 | 说明 |
|--------|------|------|
| 阿里云百炼 | `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions` | 使用 DashScope API Key |
| DeepSeek | `https://api.deepseek.com/v1/chat/completions` | 使用 DeepSeek API Key |
| OpenAI | `https://api.openai.com/v1/chat/completions` | 使用 OpenAI API Key |

**调用格式：**

```python
# POST /v1/chat/completions
{
  "model": "qwen-turbo",
  "messages": [
    {"role": "system", "content": "你是一名严谨的教师..."},
    {"role": "user", "content": "请批改以下作业..."}
  ],
  "max_tokens": 2048,
  "temperature": 0.1,
  "response_format": {"type": "json_object"}
}
```

**配置项：**

```env
# 模型配置（支持多个模型）
MODELS_CONFIG=[{"name":"qwen-turbo","provider":"dashscope","api_key":"your_key","type":"text","model_id":"qwen-turbo","enabled":true},{"name":"qwen-vl","provider":"dashscope","api_key":"your_key","type":"vision","model_id":"qwen-vl-plus","enabled":true}]

# 默认模型
DEFAULT_TEXT_MODEL=qwen-turbo
DEFAULT_VISION_MODEL=qwen-vl

# 模型参数
LLM_MAX_TOKENS=2048
LLM_TEMPERATURE=0.1
LLM_TIMEOUT=60
```

**模型配置格式说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 模型名称（前端展示用） |
| `provider` | string | 提供商：`dashscope`、`deepseek`、`openai` |
| `api_key` | string | API Key |
| `type` | string | 模型类型：`text`、`vision` |
| `model_id` | string | 模型 ID（提供商平台的标识） |
| `enabled` | bool | 是否启用 |
| `base_url` | string | 自定义端点 URL（可选） |
| `max_tokens` | int | 最大 token 数（可选） |
| `temperature` | float | 温度参数（可选） |

---

## 10. 部署与配置

### 10.1 环境要求

| 依赖 | 版本 |
|------|------|
| Python | ≥ 3.11 |
| MySQL | ≥ 8.0 |
| Redis | ≥ 6.0 |

### 10.2 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入数据库连接、阿里云密钥、模型 API Key

# 3. 创建数据库
mysql -u root -p -e "CREATE DATABASE homework_db CHARACTER SET utf8mb4;"

# 4. 启动 Redis（如果未运行）
redis-server

# 5. 启动 FastAPI
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 6. 启动 Celery Worker（另一个终端）
celery -A celery_app worker -Q homework -l info -P solo
```

### 10.3 环境变量一览

```env
# 服务
HOST=0.0.0.0
PORT=8000
DEBUG=false

# 数据库
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/homework_db?charset=utf8mb4

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# 阿里云 OCR
ALIYUN_ACCESS_KEY_ID=your_key
ALIYUN_ACCESS_KEY_SECRET=your_secret
ALIYUN_OCR_ENDPOINT=ocr-api.cn-shanghai.aliyuncs.com
ENABLE_ALIYUN_OCR=true

# 大模型配置
MODELS_CONFIG=[{"name":"qwen-turbo","provider":"dashscope","api_key":"your_key","type":"text","model_id":"qwen-turbo","enabled":true},{"name":"qwen-vl","provider":"dashscope","api_key":"your_key","type":"vision","model_id":"qwen-vl-plus","enabled":true}]
DEFAULT_TEXT_MODEL=qwen-turbo
DEFAULT_VISION_MODEL=qwen-vl
LLM_MAX_TOKENS=2048
LLM_TEMPERATURE=0.1
LLM_TIMEOUT=60

# JWT
JWT_SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=120

# 文件
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE=10485760

# 日志
LOG_LEVEL=INFO
LOG_FILE=
LOG_ROTATION=1 day
LOG_RETENTION=30 days
```

### 10.4 API 路由汇总

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/status` | 无 | 健康检查 |
| POST | `/api/v1/users/register` | 无 | 用户注册 |
| POST | `/api/v1/users/login` | 无 | 用户登录 |
| GET | `/api/v1/users/{user_id}` | 是 | 获取用户信息 |
| PUT | `/api/v1/users/{user_id}/status` | 管理员 | 启用/禁用用户 |
| POST | `/api/v1/homework/upload` | 是 | 上传作业图片 |
| POST | `/api/v1/homework/analyze` | 是 | 分析作业（大模型） |
| GET | `/api/v1/homework/status/{task_id}` | 是 | 查询任务状态 |
| GET | `/api/v1/homework/result/{task_id}` | 是 | 查询批改结果 |
| GET | `/api/v1/homework/list` | 是 | 查询作业列表 |
| GET | `/api/v1/models` | 是 | 获取模型列表 |
| GET | `/api/v1/statistics/user/{user_id}` | 是 | 用户统计 |
| GET | `/api/v1/statistics/global` | 管理员 | 全局统计 |

---

## 11. 错误码表

| 错误码 | HTTP状态码 | 说明 |
|--------|-----------|------|
| 200 | 200 | 成功 |
| 400 | 400 | 请求参数错误 |
| 401 | 401 | 未认证或 token 过期 |
| 403 | 403 | 无权限 |
| 404 | 404 | 资源不存在 |
| 409 | 409 | 冲突（如用户名已存在） |
| 500 | 500 | 服务器内部错误 |
| 1001 | 400 | 文件类型不支持 |
| 1002 | 400 | 文件大小超过限制 |
| 1003 | 400 | 用户不存在 |
| 1004 | 400 | 密码错误 |
| 1005 | 400 | 用户名已存在 |
| 1006 | 400 | 邮箱已存在 |
| 1007 | 404 | 任务不存在 |
| 1008 | 400 | 任务状态不允许此操作 |
| 2001 | 500 | OCR 服务调用失败 |
| 2002 | 500 | 大模型服务调用失败 |

---

## 附录：前端集成说明

### A. 认证流程

1. 用户登录获取 token
2. 在后续请求的 `Authorization` 头中携带 `Bearer <token>`
3. token 过期时重新登录

### B. 作业提交流程

1. 调用 `POST /api/v1/homework/upload` 上传图片
2. 获取 `task_id`
3. 轮询 `GET /api/v1/homework/status/{task_id}` 检查状态
4. 状态为 `SUCCESS` 时调用 `GET /api/v1/homework/result/{task_id}` 获取结果

### C. 响应处理示例

```javascript
// 统一响应处理
async function request(url, options = {}) {
  const token = localStorage.getItem('access_token');
  const headers = {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  };
  
  const response = await fetch(url, { ...options, headers });
  const data = await response.json();
  
  if (data.code === 401) {
    // token 过期，重新登录
    localStorage.removeItem('access_token');
    window.location.href = '/login';
    throw new Error('登录已过期');
  }
  
  if (data.code !== 200) {
    throw new Error(data.message || '请求失败');
  }
  
  return data.data;
}
```