# 智能语音助手后端系统

一个使用FastAPI构建的高性能、模块化、可扩展的智能语音助手后端系统。该系统通过WebSocket接口处理语音、文本输入，使用集成的ASR、LLM、TTS服务处理用户请求，并生成相应的语音或文本响应。

## 核心功能

- 基于WebSocket的实时流式处理
- ASR(自动语音识别)、LLM(大语言模型)、TTS(语音合成)服务集成
- 用户认证与授权
- 会话管理
- 设备管理
- 数据库集成(PostgreSQL)

## 技术栈

- **后端框架**: FastAPI
- **数据库**: PostgreSQL, SQLAlchemy ORM
- **认证**: JWT
- **容器化**: Docker, Docker Compose
- **流式处理**: WebSockets
- **服务集成**: 模块化服务注册机制

## 开发要求

- Python 3.11或更高
- Docker和Docker Compose (可选，但推荐)
- PostgreSQL数据库 (如果不使用Docker)
- Node.js 14.0.0或更高 (用于任务管理工具)

## 快速开始

### 使用Docker (推荐)

1. 克隆仓库
   ```bash
   git clone https://github.com/hongjiayang920127/voice-assistant-backend-fastapi-2025.git
   cd voice-assistant-backend-fastapi-2025
   ```

2. 创建环境变量文件
   ```bash
   cp .env.example .env
   # 编辑.env文件设置必要的环境变量
   ```

3. 启动服务
   ```bash
   docker-compose up --build
   ```

4. 访问API文档: http://localhost:8000/docs

### 不使用Docker的设置

1. 克隆仓库
   ```bash
   git clone https://github.com/hongjiayang920127/voice-assistant-backend-fastapi-2025.git
   cd voice-assistant-backend-fastapi-2025
   ```

2. 创建虚拟环境
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或
   venv\Scripts\activate  # Windows
   ```

3. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

4. 设置环境变量
   ```bash
   cp .env.example .env
   # 编辑.env文件设置必要的环境变量
   ```

5. 运行数据库迁移
   ```bash
   alembic upgrade head
   ```

6. 运行开发服务器
   ```bash
   uvicorn app.main:app --reload
   ```

7. 访问API文档: http://localhost:8000/docs

## 项目结构

```
app/
├── api/               # REST API端点
├── core/              # 核心功能模块
│   ├── auth/          # 认证相关
│   ├── device_manager/ # 设备管理
│   ├── processing_pipeline/ # 语音处理管道
│   ├── service_registry/ # 服务注册
│   └── session_manager/ # 会话管理
├── db/                # 数据库模型和仓库
├── services/          # 服务实现
│   ├── asr/           # 语音识别服务
│   ├── llm/           # 大语言模型服务
│   ├── tts/           # 语音合成服务
│   ├── embedding/     # 向量嵌入服务
│   └── vision/        # 视觉处理服务
├── websocket/         # WebSocket处理
├── config.py          # 配置管理
└── main.py            # 应用入口点
```

## 许可证

MIT