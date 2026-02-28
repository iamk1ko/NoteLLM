# NoteLLM

一款面向个人知识库与对话协作的 LLM 应用，覆盖“文件上传-向量化-对话检索-社区分享”的完整闭环。后端接口已完整文档化，前端可直接对接。

## 核心亮点

- 流式对话与历史管理：支持 SSE 流式响应、会话分页与消息查询
- 文件分片上传与去重：支持断点续传、MD5 去重、失败重传与状态查询
- RAG 向量化链路：文件入库后自动向量化，支持重试与状态追踪
- 社区分享与互动：分享文件/会话、浏览、点赞与排序
- 完整 API 文档：接口字段与响应结构齐全，便于前端快速接入

## 界面预览

登录/注册
![用户登录界面](docs/asset/用户登录界面.png)
![用户注册界面](docs/asset/用户注册界面.png)

个人文档库与上传
![个人文档库界面](docs/asset/个人文档库界面.png)
![文件上传界面](docs/asset/文件上传界面.png)
![上传文件预览界面](docs/asset/上传文件预览界面.png)

对话与社区
![聊天助手界面](docs/asset/聊天助手界面.png)
![社区广场界面](docs/asset/社区广场界面.png)

用户中心
![用户中心界面](docs/asset/用户中心界面.png)

## 功能一览

| 模块 | 主要能力 |
| --- | --- |
| 认证 | 注册/登录/退出、Cookie 会话认证 |
| 文件 | 分片上传、MD5 去重、状态查询、重试向量化 |
| 对话 | 流式对话、会话管理、消息历史 |
| RAG | 文件向量化、检索、会话上下文 |
| 社区 | 分享、浏览、点赞、排序 |

## 核心流程图

### 文件上传与向量化流程

```mermaid
flowchart TD
    A[用户上传文件] --> B[分片上传]
    B --> C{是否已存在?}
    C -->|是| D[返回 exists=true]
    C -->|否| E[合并分片]
    E --> F[写入文件记录]
    F --> G[触发向量化任务]
    G --> H{向量化成功?}
    H -->|是| I[状态变更为 EMBEDDED]
    H -->|否| J[状态 FAILED 可重试]
```

### LLM 流式对话流程

```mermaid
sequenceDiagram
    participant U as User
    participant API as FastAPI
    participant LLM as LLM API
    participant DB as MySQL
    participant R as Redis

    U->>API: 发送消息 (SSE)
    API->>DB: 保存用户消息
    API->>R: 载入历史消息
    API->>LLM: 发起流式请求
    LLM-->>API: 流式 Token
    API-->>U: SSE 推送
    API->>DB: 保存 AI 回复
```

## 技术架构

- 后端：FastAPI + SQLAlchemy (Async)
- 数据库：MySQL
- 缓存：Redis
- 向量库：Milvus
- 文件存储：MinIO
- 消息队列：RabbitMQ
- LLM：API 接入

## 快速开始（Docker）

```bash
docker compose -f docs/docker/docker-compose.yaml up -d
```

服务端口（默认）：
- MySQL: 3306
- Redis: 6379
- RabbitMQ: 5672 / 15672
- MinIO: 9000 / 9001
- Milvus: 19530 / 9091

### 后端启动

#### 1. 环境变量配置

在 `backend/.env` 中配置以下关键变量（参考 `backend/.env.dev` 示例）：

| 变量名 | 说明 | 示例值 |
| --- | --- | --- |
| `APP_ENV` | 运行环境 | `dev` |
| `DB_HOST` | MySQL 地址 | `127.0.0.1` |
| `DB_PORT` | MySQL 端口 | `3306` |
| `DB_NAME` | 数据库名 | `pai_school` |
| `DB_USER` | MySQL 用户名 | `root` |
| `DB_PASSWORD` | MySQL 密码 | `root` |
| `REDIS_URL` | Redis 连接串 | `redis://127.0.0.1:6379/0` |
| `MINIO_ENDPOINT` | MinIO 地址 | `127.0.0.1:9000` |
| `MINIO_ACCESS_KEY` | MinIO AK | `minioadmin` |
| `MINIO_SECRET_KEY` | MinIO SK | `minioadmin` |
| `RABBITMQ_URL` | RabbitMQ 连接串 | `amqp://admin:admin@127.0.0.1:5672/admin_vhost` |
| `MILVUS_HOST` | Milvus 地址 | `127.0.0.1` |
| `MILVUS_PORT` | Milvus 端口 | `19530` |
| `BLSC_API_KEY` | LLM API Key | `sk-xxx` |
| `BLSC_BASE_URL` | LLM API 地址 | `https://llmapi.blsc.cn` |

#### 2. 启动后端服务

```bash
cd backend

# 创建虚拟环境（首次）
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py
```

后端默认访问地址：http://localhost:8000

API 文档（Swagger UI）：http://localhost:8000/docs

### 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务
npm run dev
```

前端默认访问地址：http://localhost:5173

> 注意：前端默认连接 `http://localhost:8000/api/v1`，如需修改请编辑 `frontend/.env` 中的 `VITE_API_BASE_URL`。

## API 文档

详见：`docs/API接口文档.md`

## 目录结构（简）

```
backend/           后端服务
docs/              文档与部署
docs/asset/        界面截图
docs/docker/       docker-compose
```
