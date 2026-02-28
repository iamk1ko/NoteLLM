# 🌟 NoteLLM

<p align="center">
  <img src="docs/asset/聊天助手界面.png" alt="NoteLLM Demo" width="600"/>
</p>

> 🎓 一款面向个人知识库与对话协作的 LLM 应用，覆盖「文件上传 → 向量化 → 对话检索 → 社区分享」完整闭环。后端接口已完整文档化，前端可直接对接 👉 [API 文档](docs/API接口文档.md)

---

## ✨ 核心亮点

| 亮点 | 说明 |
| --- | --- |
| 🔄 **流式对话** | 支持 SSE 流式响应实时返回 AI 回复，会话分页与消息历史查询 |
| 📦 **文件分片上传** | 断点续传、MD5 去重、失败重传、状态查询全链路支持 |
| 🧠 **RAG 向量化** | 文件自动向量化入库 Milvus，支持重试与状态追踪 |
| 👥 **社区分享** | 分享文件/会话、浏览、点赞、多种排序方式 |
| 📚 **完整 API** | 接口字段与响应结构齐全，前端零障碍接入 |

---

## 🖼️ 界面预览

### 登录 / 注册
![用户登录界面](docs/asset/用户登录界面.png)
![用户注册界面](docs/asset/用户注册界面.png)

### 个人文档库与上传
![个人文档库界面](docs/asset/个人文档库界面.png)
![文件上传界面](docs/asset/文件上传界面.png)
![上传文件预览界面](docs/asset/上传文件预览界面.png)

### 对话与社区
![聊天助手界面](docs/asset/聊天助手界面.png)
![社区广场界面](docs/asset/社区广场界面.png)

### 用户中心
![用户中心界面](docs/asset/用户中心界面.png)

---

## 🛠️ 功能一览

| 模块 | 主要能力 |
| --- | --- |
| 🔐 **认证** | 注册 / 登录 / 退出、Cookie 会话认证 |
| 📁 **文件** | 分片上传、MD5 去重、状态查询、重试向量化 |
| 💬 **对话** | 流式对话、会话管理、消息历史 |
| 🧠 **RAG** | 文件向量化、语义检索、会话上下文记忆 |
| 🌐 **社区** | 分享、浏览、点赞、热门/最新排序 |

---

## 🔄 核心流程图

### 1️⃣ 文件上传与向量化流程

```mermaid
flowchart TD
    subgraph 上传阶段
        A[👤 用户选择文件] --> B[📱 前端计算文件 MD5]
        B --> C{🔍 检查文件是否已存在?}
        C -->|已存在| D[✅ 返回 exists=true, 跳过上传]
        C -->|不存在| E[📤 分片上传到 MinIO 临时桶]
        E --> F[💾 写入文件元数据到 MySQL]
        F --> G[📝 写入分片记录到 MySQL]
        G --> H{📦 所有分片上传完成?}
    end

    H -->|否| E
    H -->|是| I[🔀 合并分片到正式桶]

    subgraph 向量化阶段
        I --> J[📨 发送向量化任务到 RabbitMQ]
        J --> K[⚙️ 向量化消费者取出任务]
        K --> L[📥 从 MinIO 下载文件]
        L --> M[📖 解析文档内容]
        M --> N[✂️ 文本分块]
        N --> O[🔢 向量化 embedding]
        O --> P[💾 写入 Milvus 向量库]
        P --> Q[✅ 更新文件状态为 EMBEDDED]
    end

    J -->|失败| R[❌ 标记状态为 FAILED]
    R --> S[🔄 可手动重试向量化]
```

### 2️⃣ LLM 流式对话流程

```mermaid
sequenceDiagram
    participant U as 👤 用户
    participant API as 🌐 FastAPI
    participant DB as 🗄️ MySQL
    participant R as ⚡ Redis
    participant V as 🧠 Milvus
    participant LLM as 🤖 LLM API

    Note over U,LLM: 1. 用户发送消息
    U->>API: POST /sessions/{id}/messages/stream<br/>Content: "什么是 RAG?"
    
    Note over API,DB: 2. 保存用户消息
    API->>DB: INSERT chat_message (role=user)
    
    Note over API,R: 3. 写入 Redis 缓存
    API->>R: RPUSH 消息到会话列表
    
    Note over API,R: 4. 加载历史上下文
    R->>API: 返回历史消息列表
    
    Note over API,V: 5. RAG 检索（如有关联文件）
    API->>V: similarity_search(用户问题)
    V-->>API: 返回相关文档片段
    
    Note over API,LLM: 6. 调用 LLM 生成回复
    API->>LLM: POST /v1/chat/completions<br/>+ system_prompt + 历史 + RAG 片段
    
    Note over LLM,API: 7. 流式返回 Token
    LLM-->>API: SSE stream tokens
    
    Note over API,U: 8. 实时推送流式响应
    API-->>U: data: {"content":"R", "done":false}<br/>data: {"content":"AG", "done":false}<br/>data: {"content":"是...", "done":true}
    
    Note over API,DB: 9. 保存 AI 回复
    API->>DB: INSERT chat_message (role=assistant)
    
    Note over API,R: 10. 更新 Redis 缓存
    API->>R: RPUSH AI 回复
```

### 3️⃣ 社区分享流程

```mermaid
flowchart LR
    subgraph 分享者
        A[👤 用户] --> B[📤 分享会话/文件]
        B --> C[📝 填写标题、描述、标签]
        C --> D[💾 写入 community_shares 表]
    end

    subgraph 访问者
        D --> E[🌐 访问社区广场]
        E --> F[🔍 浏览/搜索/排序]
        F --> G[👍 点赞/👁️ 浏览]
        G --> H[🍴  Fork 会话到自己的空间]
    end
```

---

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                        🌐 前端 (Vue 3 + Element Plus)       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    🌐 FastAPI 后端 (Python)                │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐    │
│  │  Auth   │  │  Files  │  │  Chat   │  │Community│    │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘    │
└─────────────────────────────────────────────────────────────┘
          │            │            │            │
    ┌─────┴─────┐  ┌───┴───┐  ┌───┴───┐  ┌───┴───┐
    ▼           ▼       ▼       ▼       ▼
┌────────┐  ┌──────┐ ┌──────┐ ┌───────┐ ┌──────┐
│ MySQL │  │Redis │ │MinIO │ │RabbitMQ│ │Milvus│
│  8.0  │  │      │ │      │ │       │ │      │
└────────┘  └──────┘ └──────┘ └───────┘ └──────┘
                                              │
                                              ▼
                                      ┌────────────┐
                                      │   LLM API  │
                                      │ (DeepSeek) │
                                      └────────────┘
```

| 组件 | 技术选型 | 用途 |
| --- | --- | --- |
| 🌐 后端 | FastAPI + SQLAlchemy (Async) | API 服务 |
| 🗄️ 数据库 | MySQL 8 | 持久化存储 |
| ⚡ 缓存 | Redis | 会话缓存、消息历史 |
| 📦 对象存储 | MinIO | 文件分片存储 |
| 🧠 向量库 | Milvus | 语义检索 |
| 📨 消息队列 | RabbitMQ | 异步向量化任务 |
| 🤖 LLM | API 接入 (DeepSeek/BLSC) | 对话生成 |

---

## 🚀 快速开始（Docker）

```bash
# 克隆项目
git clone https://github.com/iamk1ko/NoteLLM.git
cd NoteLLM

# 启动所有依赖服务
docker compose -f docs/docker/docker-compose.yaml up -d
```

### 📡 服务端口

| 服务 | 端口 | 说明 |
| --- | --- | --- |
| MySQL | 3306 | 数据库 |
| Redis | 6379 | 缓存 |
| RabbitMQ | 5672 / 15672 | 消息队列 / 管理后台 |
| MinIO | 9000 / 9001 | 对象存储 / 控制台 |
| Milvus | 19530 / 9091 | 向量库 / 控制台 |

---

### 💻 后端启动

#### 1️⃣ 环境变量配置

在 `backend/.env` 中配置以下关键变量（参考 `backend/.env.dev`）：

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

#### 2️⃣ 启动后端

```bash
cd backend

# 使用 uv 创建虚拟环境并安装依赖（首次）
uv venv
uv sync

# 激活虚拟环境（可选，uv run 可直接运行）
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

# 启动服务
uv run python main.py
# 或者直接
python main.py
```

- 🌐 后端地址：http://localhost:8000
- 📚 API 文档（Swagger UI）：http://localhost:8000/docs

---

### 🎨 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务
npm run dev
```

- 🎯 前端地址：http://localhost:5173

> 💡 前端默认连接 `http://localhost:8000/api/v1`，如需修改请编辑 `frontend/.env` 中的 `VITE_API_BASE_URL`。

---

## 📖 API 文档

详见：[docs/API接口文档.md](docs/API接口文档.md)

---

## 📁 项目结构

```
NoteLLM/
├── 📂 backend/               # 🌐 FastAPI 后端
│   ├── 📂 app/
│   │   ├── 📂 api/         # API 路由
│   │   ├── 📂 crud/        # 数据库操作
│   │   ├── 📂 models/     # 数据模型
│   │   ├── 📂 schemas/    # Pydantic Schema
│   │   ├── 📂 services/    # 业务逻辑
│   │   └── 📂 consumers/  # RabbitMQ 消费者
│   └── main.py             # 入口文件
│
├── 📂 frontend/             # 🎨 Vue 3 前端
│   ├── src/
│   │   ├── 📂 views/       # 页面视图
│   │   ├── 📂 components/ # 组件
│   │   └── 📂 services/   # API 调用
│   └── package.json
│
├── 📂 docs/                 # 📚 文档
│   ├── 📂 asset/           # 🖼️ 界面截图
│   ├── 📂 docker/          # 🐳 Docker 配置
│   └── API接口文档.md       # 📖 接口文档
│
└── README.md                # 📌 项目 README
```

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！🐛

---

## 📄 License

MIT License © 2024 NoteLLM
