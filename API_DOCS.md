# 作业智能批改系统 — API 接口文档

> 版本：1.0.0 | 基础路径：`http://localhost:8000/api/v1`

---

## 目录

1. [项目概述](#1-项目概述)
2. [系统架构](#2-系统架构)
3. [通用约定](#3-通用约定)
4. [用户模块](#4-用户模块)
5. [作业模块](#5-作业模块)
6. [统计模块](#6-统计模块)
7. [数据模型](#7-数据模型)
8. [异步任务流程](#8-异步任务流程)
9. [外部服务集成](#9-外部服务集成)
10. [部署与配置](#10-部署与配置)

---

## 1. 项目概述

作业智能批改系统是一套基于 AI 的中小学作业自动批改平台，支持学生上传手写作业图片，系统自动进行 OCR 识别、题目切分、答案匹配和大模型批改，最终返回逐题评分与评语。

**核心能力：**

| 能力 | 技术实现 |
|------|----------|
| 图像预处理 | OpenCV：EXIF 校正 → 灰度化 → CLAHE 增强 → 透视纠偏 |
| 试卷切题 | 阿里云 RecognizeEduPaperCut，返回每题坐标 |
| 题目 OCR | 阿里云 RecognizeEduQuestionOcr，识别题干 + 学生答案 + 题型 |
| 智能批改 | 规则引擎（选择/判断/填空/计算题）+ DeepSeek大模型（主观题） |
| 异步任务 | Celery + Redis，支持自动重试 |

**技术栈：** FastAPI + SQLAlchemy + Celery + Redis + MySQL + OpenCV + Vue 3

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────┐
│                    前端 (Vue 3)                       │
└─────────────────┬───────────────────────────────────┘
                  │ HTTP REST
                  ▼
┌─────────────────────────────────────────────────────┐
│               FastAPI 应用 (main.py)                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ 用户路由  │  │ 作业路由  │  │   统计路由        │   │
│  │ /users   │  │ /homework │  │  /statistics     │   │
│  └────┬─────┘  └────┬─────┘  └───────┬──────────┘   │
│       │              │               │               │
│       ▼              ▼               ▼               │
│  ┌──────────────────────────────────────────────┐    │
│  │           业务服务层 (services/)               │    │
│  │  UserService │ TaskService │ OCRService      │    │
│  │  LLMService  │ ImageService│ RuleEngine      │    │
│  └──────────────────┬───────────────────────────┘    │
│                     │                                 │
└─────────────────────┼─────────────────────────────────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
    ┌─────────┐ ┌─────────┐ ┌──────────┐
    │  MySQL  │ │  Redis  │ │  Celery  │
    │ (数据)  │ │ (队列)  │ │ (Worker) │
    └─────────┘ └─────────┘ └────┬─────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
             ┌──────────┐ ┌──────────┐ ┌──────────┐
             │ 阿里云OCR │ │ DeepSeek  │ │ 规则引擎  │
             │ (切题+识别)│ │ (大模型)  │ │ (精确匹配) │
             └──────────┘ └──────────┘ └──────────┘
```

**请求生命周期（以作业上传为例）：**

1. 用户通过 `POST /api/v1/homework/upload` 上传图片
2. FastAPI 校验文件类型与大小，保存到 `uploads/` 目录
3. 创建 `HomeworkTask` 记录（状态：PENDING），返回 `task_id`
4. 通过 Celery 异步提交 `process_homework_task` 到 `homework` 队列
5. Celery Worker 消费任务，依次执行：预处理 → 切题 → OCR → 批改
6. 客户端轮询 `GET /api/v1/homework/status/{task_id}` 获取进度
7. 客户端调用 `GET /api/v1/homework/result/{task_id}` 获取最终批改结果

---

## 3. 通用约定

### 3.1 基础路径

```
http://localhost:8000/api/v1
```

### 3.2 统一响应格式

所有业务接口返回以下 JSON 结构：

```json
{
  "code": 200,
  "message": "success",
  "data": { }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | int | 状态码，200 表示成功 |
| `message` | string | 提示信息 |
| `data` | object/null | 业务数据 |

### 3.3 错误响应

```json
{
  "detail": "错误描述信息"
}
```

HTTP 状态码：400（业务异常）、500（服务器错误）。

### 3.4 健康检查

**`GET /status`** — 无认证

```json
{
  "status": "ok",
  "service": "作业智能批改系统",
  "version": "1.0.0"
}
```

---

## 4. 用户模块

基础路径：`/api/v1/users`

### 4.1 用户注册

```http
POST /api/v1/users/register
Content-Type: application/json
```

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `username` | string | 是 | 用户名，唯一 |
| `email` | string | 是 | 邮箱，唯一，需合法格式 |
| `password` | string | 是 | 明文密码，后端 bcrypt 加密存储 |
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
  "message": "success",
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

### 4.2 用户登录

```http
POST /api/v1/users/login
Content-Type: application/json
```

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `username` | string | 是 | 用户名 |
| `password` | string | 是 | 明文密码 |

**响应示例：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
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

### 4.3 获取用户信息

```http
GET /api/v1/users/{user_id}
```

**路径参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `user_id` | int | 用户 ID |

**响应：** 同 4.1 注册响应的 `data` 字段。

---

### 4.4 更新用户状态（管理员）

```http
PUT /api/v1/users/{user_id}/status?is_active=true
Authorization: Bearer <access_token>
```

**认证要求：** 必须登录，且 `role == "admin"`。

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `is_active` | bool | 是 | 启用或禁用用户 |

---

## 5. 作业模块

基础路径：`/api/v1/homework`

### 5.1 上传作业

```http
POST /api/v1/homework/upload
Content-Type: multipart/form-data
```

**表单参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | file | 是 | 作业图片，支持 jpg/jpeg/png/gif/bmp/pdf，最大 10MB |
| `subject` | string | 是 | 学科（如 `math`、`chinese`、`english`） |
| `grade` | string | 是 | 年级（如 `grade1`、`grade7`） |
| `user_id` | int | 是 | 上传用户 ID |

**请求示例（curl）：**

```bash
curl -X POST http://localhost:8000/api/v1/homework/upload \
  -F "file=@homework.jpg" \
  -F "subject=math" \
  -F "grade=grade3" \
  -F "user_id=1"
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

### 5.2 查询任务状态

```http
GET /api/v1/homework/status/{task_id}
```

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

```
PENDING       → 已创建，等待处理
PROCESSING    → 开始处理
PREPROCESSING → 图像预处理中
CUTTING       → 试卷切题中
OCRING        → 题目 OCR 识别中
GRADING       → 大模型批改中
SUCCESS       → 批改完成
FAILED        → 处理失败（自动重试 3 次后最终失败）
```

> 前端建议每 2 秒轮询一次，直到状态变为 `SUCCESS` 或 `FAILED`。

---

### 5.3 查询批改结果

```http
GET /api/v1/homework/result/{task_id}
```

**路径参数：** 同 5.2。

**响应示例：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "total_score": 85.5,
    "created_at": "2026-05-28T10:30:00",
    "results": [
      {
        "question_block_id": 10,
        "question_no": "1",
        "score": 10.0,
        "max_score": 10.0,
        "result": "正确",
        "comment": "答案完全正确，解题步骤清晰",
        "analysis": "本题考查的是分数加法，学生掌握了通分和约分的方法...",
        "confidence": 0.95
      },
      {
        "question_block_id": 11,
        "question_no": "2",
        "score": 5.0,
        "max_score": 10.0,
        "result": "部分正确",
        "comment": "解题思路正确，但最后一步计算有误",
        "analysis": "学生在列方程时正确，但在解方程过程中符号处理出现错误...",
        "confidence": 0.88
      },
      {
        "question_block_id": 12,
        "question_no": "3",
        "score": 0.0,
        "max_score": 10.0,
        "result": "待复核",
        "comment": "未找到标准答案，请人工批改",
        "analysis": "",
        "confidence": 0.0
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
| `score` | float | 实际得分 |
| `max_score` | float | 满分 |
| `result` | string | 批改结论：`正确` / `部分正确` / `错误` / `待复核` |
| `comment` | string | 评语 |
| `analysis` | string | 解题分析 |
| `confidence` | float | 置信度（0.0 ~ 1.0），待复核时为 0 |

---

## 6. 统计模块

基础路径：`/api/v1/statistics`

### 6.1 用户统计

```http
GET /api/v1/statistics/user/{user_id}
```

**响应示例：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total_tasks": 25,
    "completed_tasks": 22,
    "average_score": 87.3,
    "recent_scores": [90, 85, 92, 78, 88, 95, 83]
  }
}
```

---

### 6.2 全局统计

```http
GET /api/v1/statistics/global
```

**响应示例：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total_users": 150,
    "total_tasks": 1200,
    "completed_tasks": 1050,
    "average_score": 82.6
  }
}
```

---

## 7. 数据模型

### 7.1 模型关系图

```
User (用户)
  │
  ├── 1:N → HomeworkTask (作业任务)
  │            │
  │            ├── 1:N → HomeworkImage (作业图片：原图 + 处理后)
  │            ├── 1:N → QuestionBlock (题目块：坐标 + 裁剪图路径)
  │            │            │
  │            │            ├── 1:1 → OCRResult (OCR 识别结果)
  │            │            └── 1:1 → GradingResult (批改结果)
  │            │
  │            └── 1:N → GradingResult (批改结果，含 reviewer 外键回 User)
  │
  └── 1:N → GradingResult (作为复核人)

StandardAnswer (标准答案)
  │  按 subject + grade + question_key 唯一索引
  │  在批改时通过 subject + grade + question_text 模糊匹配

KnowledgePoint (知识点)
  │  按学科 + 年级组织，含难度系数
```

### 7.2 核心表结构

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
| status | VARCHAR(20) | 状态（PENDING → SUCCESS/FAILED） |
| total_score | DECIMAL(5,2) | 总分 |
| error_message | TEXT | 失败时的错误信息 |

#### `ocr_result` — OCR 识别结果表

| 列 | 类型 | 说明 |
|----|------|------|
| id | BIGINT PK | 自增主键 |
| task_id | VARCHAR(64) FK | 关联任务 |
| question_block_id | BIGINT FK | 关联题目块 |
| question_no | VARCHAR(20) | 题号 |
| question_text | TEXT | 识别出的题干 |
| student_answer | TEXT | 识别出的学生答案 |
| question_type | VARCHAR(50) | 题型（由阿里云 OCR 自动分类） |
| raw_response | JSON | 阿里云原始响应 |

#### `standard_answer` — 标准答案表

| 列 | 类型 | 说明 |
|----|------|------|
| id | BIGINT PK | 自增主键 |
| subject | VARCHAR(20) | 学科 |
| grade | VARCHAR(20) | 年级 |
| question_key | VARCHAR(100) UNIQUE | 题目唯一标识 |
| question_text | TEXT | 题干文本 |
| standard_answer | TEXT | 标准答案 |
| question_type | VARCHAR(50) | 题型 |
| max_score | DECIMAL(5,2) | 满分 |

#### `grading_result` — 批改结果表

| 列 | 类型 | 说明 |
|----|------|------|
| id | BIGINT PK | 自增主键 |
| task_id | VARCHAR(64) FK | 关联任务 |
| question_block_id | BIGINT FK | 关联题目块 |
| question_no | VARCHAR(20) | 题号 |
| score | DECIMAL(5,2) | 得分 |
| max_score | DECIMAL(5,2) | 满分 |
| result | VARCHAR(20) | 正确 / 部分正确 / 错误 |
| comment | TEXT | 评语 |
| analysis | TEXT | 解题分析 |
| confidence | DECIMAL(3,2) | 置信度 |
| is_reviewed | BOOLEAN | 是否已人工复核 |
| reviewed_score | DECIMAL(5,2) | 复核后分数 |
| reviewer_id | BIGINT FK | 复核人 |
| raw_response | JSON | LLM 原始响应 |

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
┌──────────┐    ┌──────────────┐    ┌───────────┐    ┌─────────┐    ┌──────────┐    ┌──────────┐
│  PENDING │───→│ PREPROCESSING │───→│  CUTTING   │───→│  OCRING  │───→│ GRADING  │───→│ SUCCESS  │
└──────────┘    └──────────────┘    └───────────┘    └─────────┘    └──────────┘    └──────────┘
                                                                         │
                                                                         ▼ (异常)
                                                                    ┌──────────┐
                                                                    │  FAILED  │──→ retry (最多3次)
                                                                    └──────────┘
```

**各阶段详解：**

| 阶段 | 操作 | 关键代码 |
|------|------|----------|
| **PREPROCESSING** | EXIF 方向校正 → 灰度化 → CLAHE 对比度增强 → 高斯去噪 → Canny 边缘检测 → 四点透视纠偏 | `ImageService.preprocess_image()` |
| **CUTTING** | 调用阿里云 `RecognizeEduPaperCut` 获取每题坐标，再按坐标裁剪出每题图片 | `AliyunOCRClient.recognize_edu_paper_cut()` + `ImageService.crop_question_blocks()` |
| **OCRING** | 逐题调用阿里云 `RecognizeEduQuestionOcr`，识别题干文本、学生手写答案、题型 | `AliyunOCRClient.recognize_edu_question_ocr()` |
| **GRADING** | 先用规则引擎精确匹配，再用DeepSeek大模型生成评语；无标准答案则标记"待复核" | `RuleEngine` + `LLMService.grade_question()` |

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
| `RecognizeEduPaperCut` | 试卷切题 | 作业图片（BinaryIO 流） | 每题坐标 (x1,y1,x2,y2) + 题号 |
| `RecognizeEduQuestionOcr` | 单题 OCR | 裁剪后的题目图片 | 题干文本 + 学生答案 + 题型 |

**配置项：**

```env
ALIYUN_ACCESS_KEY_ID=your_key
ALIYUN_ACCESS_KEY_SECRET=your_secret
ALIYUN_OCR_ENDPOINT=ocr-api.cn-shanghai.aliyuncs.com
ENABLE_ALIYUN_OCR=true
```

> 当 SDK 未安装或 `ENABLE_ALIYUN_OCR=false` 或密钥为空时，自动降级为 mock 模式，返回固定模拟数据，方便无外部依赖的开发调试。

### 9.2 DeepSeek 大模型

**调用方式：** 通过阿里云百炼平台 DashScope API 调用 DeepSeek 模型。

**SDK：** `dashscope==1.25.17`

| 项目 | 说明 |
|------|------|
| 接口基座 | 阿里云 DashScope（百炼平台） |
| 模型 | `deepseek-v4-pro` / `deepseek-v4-flash` |
| 用途 | 对 OCR 识别出的学生答案进行语义理解和评分 |
| 调用方式 | `dashscope.Generation.call()`，result_format="json" |

**DeepSeek-v4-pro 重要约束：**

> **该模型不支持 `system` 角色。** messages 中只能使用 `user` 和 `assistant` 角色。所有系统提示词（角色设定、输出格式要求等）必须合并到第一条 `user` 消息的 content 开头，不能单独以 `{"role": "system", ...}` 形式发送，否则会返回 400 错误：
> `unknown variant 'system', expected 'user' or 'assistant'`

**正确示例（messages 构造）：**

```python
# ❌ 错误：DeepSeek-v4-pro 不支持 system 角色
messages = [
    {"role": "system", "content": "你是一名批改老师..."},
    {"role": "user", "content": "请批改以下作业..."},
]

# ✅ 正确：系统提示词合并到 user 消息前面
messages = [
    {"role": "user", "content": "你是一名批改老师，输出JSON格式。\n\n请批改以下作业..."},
]
```

**批改策略（双通道）：**

```
OCR 结果
  │
  ├── 题型 = 选择题/判断题/填空题/计算题
  │     │
  │     ├── RuleEngine 精确匹配 → 判定对错
  │     └── LLM 补充评语和分析
  │
  └── 其他题型（解答题/作文等）
        │
        └── 直接调用 DeepSeek LLM 批改
```

**配置项：**

```env
DASHSCOPE_API_KEY=your_api_key
LLM_MODEL=deepseek-v4-pro
ENABLE_LLM=true
LLM_MAX_TOKENS=2048
LLM_TEMPERATURE=0.1
LLM_TIMEOUT=60
```

**熔断保护：** 连续失败 5 次后熔断 30 秒（`pybreaker` 实现）。

### 9.3 规则引擎

`services/rule_engine.py` — 针对结构化题型的精确匹配逻辑：

| 题型 | 匹配策略 |
|------|----------|
| 选择题 | 大写字母精确匹配；学生答案包含在标准答案中给 50% 分 |
| 判断题 | 多值映射（正确/对/T/True ↔ 错误/错/F/False） |
| 填空题 | 严格字符串相等 |
| 计算题 | 正则提取数值，浮点误差 < 1e-9 判定正确，< 1% 判定部分正确 |

---

## 10. 部署与配置

### 10.1 环境要求

| 依赖 | 版本 |
|------|------|
| Python | ≥ 3.11 |
| MySQL | ≥ 8.0 |
| Redis | ≥ 6.0 |
| Node.js | ≥ 18 (前端构建) |

### 10.2 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入数据库连接、阿里云密钥、DeepSeek密钥

# 3. 创建数据库
mysql -u root -p -e "CREATE DATABASE homework_db CHARACTER SET utf8mb4;"

# 4. 启动 Redis（如果未运行）
redis-server

# 5. 启动 FastAPI
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 6. 启动 Celery Worker（另一个终端）
celery -A celery_app worker -Q homework -l info -P solo

# 7. 启动前端（可选）
cd frontend && npm run dev
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

# DeepSeek（通过阿里云百炼 DashScope API 调用）
DASHSCOPE_API_KEY=your_api_key
LLM_MODEL=deepseek-v4-pro
ENABLE_LLM=true

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
| GET | `/` | 无 | 服务信息 |
| GET | `/status` | 无 | 健康检查 |
| POST | `/api/v1/users/register` | 无 | 用户注册 |
| POST | `/api/v1/users/login` | 无 | 用户登录 |
| GET | `/api/v1/users/{user_id}` | 无 | 获取用户信息 |
| PUT | `/api/v1/users/{user_id}/status` | 管理员 | 启用/禁用用户 |
| POST | `/api/v1/homework/upload` | 无 | 上传作业图片 |
| GET | `/api/v1/homework/status/{task_id}` | 无 | 查询任务状态 |
| GET | `/api/v1/homework/result/{task_id}` | 无 | 查询批改结果 |
| GET | `/api/v1/statistics/user/{user_id}` | 无 | 用户统计 |
| GET | `/api/v1/statistics/global` | 无 | 全局统计 |


A. 安全性 — 作业上传不应明文传 user_id

API_DOCS.md 第 5.1 节 的 upload 接口把 user_id 作为表单参数传递，任何知道该 ID 的人都可以冒用身份上传。建议改为从 JWT token 中提取当前用户，upload 接口标记为需要认证。

B. 命名一致性问题

clients/tongyi_client.py 文件名仍带 "tongyi"，但实际调用的是 DeepSeek 模型。建议重命名为 llm_client.py 或 deepseek_client.py，类名 TongyiClient 也一并修改，避免新人误解。

C. config.py 默认模型与文档不一致

config.py:43 默认值是 deepseek-v4-flash，而文档和 .env.example 写的是 deepseek-v4-pro。建议统一，并在文档中说明两个模型的适用场景（v4-flash 更快更便宜，v4-pro 推理能力更强适合复杂批改）。

D. 缺少错误码表

目前文档只有通用响应格式（code=200），没有业务错误码对照表（如 token 过期、文件过大、任务不存在等）。建议在 3.2 节后增加错误码说明，方便前端对接。

E. 缺少 API 版本管理策略

文档标题写了 1.0.0，但 URL 路径是 /api/v1。建议在文档开头说明版本策略：何时递增 v1/v2、向后兼容承诺、废弃通知周期等。