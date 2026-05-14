# 贡献指南

欢迎参与本项目的开发！请阅读以下指南，确保你的贡献符合项目规范。

## 开发环境

### 前置依赖

- Python 3.9+
- Git

### 安装步骤

1. **克隆仓库**

```bash
git clone https://github.com/yourusername/homework-grading-system.git
cd homework-grading-system
```

2. **创建虚拟环境**

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

3. **安装依赖**

```bash
pip install -r requirements.txt
```

4. **配置环境变量**

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置数据库连接等信息。

5. **启动服务**

```bash
# 开发模式
python main.py

# 或使用uvicorn
uvicorn main:app --reload --port 8000
```

## 代码规范

### Python代码规范

- 遵循 [PEP 8](https://peps.python.org/pep-0008/) 规范
- 使用 `black` 进行代码格式化
- 使用 `isort` 进行导入排序
- 使用 `flake8` 进行代码检查

### 格式化命令

```bash
# 格式化代码
black .

# 排序导入
isort .

# 代码检查
flake8 .
```

## Git工作流程

### 分支管理

- `main`: 主分支，稳定版本
- `develop`: 开发分支，包含最新功能
- `feature/*`: 功能分支，用于开发新功能
- `bugfix/*`: 修复分支，用于修复bug

### 提交规范

提交信息遵循以下格式：

```
<类型>: <描述>

[可选的详细描述]
```

**类型说明：**

| 类型 | 描述 |
|------|------|
| feat | 新增功能 |
| fix | 修复bug |
| docs | 更新文档 |
| style | 代码格式（不影响功能） |
| refactor | 代码重构 |
| test | 添加测试 |
| chore | 构建/工具相关 |

**示例：**

```
feat: 添加作业上传功能

- 实现文件上传接口
- 添加文件类型验证
- 支持图片和PDF格式
```

### Pull Request流程

1. Fork 仓库
2. 创建功能分支：`git checkout -b feature/your-feature`
3. 提交代码
4. 推送到你的仓库：`git push origin feature/your-feature`
5. 创建 Pull Request

## 项目结构

```
homework-grading-system/
├── app/                    # FastAPI应用
│   └── v1/                 # API路由
├── clients/                # 外部服务客户端
├── models/                 # SQLAlchemy模型
├── schemas/                # Pydantic数据模型
├── services/               # 业务逻辑服务
├── tasks/                  # Celery异步任务
├── utils/                  # 工具函数
├── celery_app.py           # Celery配置
├── config.py               # 配置管理
└── main.py                 # FastAPI入口
```

## API开发规范

### 路由命名

- 使用小写字母和连字符
- 版本号放在API路径中：`/api/v1/`

### 响应格式

所有API响应统一使用以下格式：

```json
{
    "code": 200,
    "message": "success",
    "data": {...}
}
```

### 错误处理

- 使用HTTP状态码表示错误类型
- 在响应体中提供详细的错误信息

## 测试

### 运行测试

```bash
# 安装测试依赖
pip install pytest pytest-asyncio

# 运行测试
pytest tests/
```

### 测试规范

- 单元测试放在 `tests/` 目录下
- 测试文件名使用 `test_*.py` 格式
- 每个功能模块应有对应的测试

## 文档

### API文档

启动服务后自动生成：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 更新文档

- 更新 `README.md` 描述项目功能
- 更新 `docs/` 目录下的详细文档

## 许可证

本项目使用 MIT 许可证。贡献代码即表示同意遵守该许可证。

## 联系方式

如有问题或建议，欢迎创建 Issue 或联系维护者。
