# RAG 聊天系统实施进度

## 已完成的工作

### 第一阶段：数据库模型调整与迁移

#### 1.1 创建会话-文件关联表
- 文件：`backend/app/models/chat_session_files.py`
- 模型：`ChatSessionFile`
- 功能：实现会话与文件的多对多关系
- 特点：
  - 复合唯一索引：`(chat_session_id, file_id)`
  - 包含 `create_time` 记录关联时间
  - 不建立外键约束，保持学习项目灵活性

#### 1.2 调整 User 模型
- 文件：`backend/app/models/users.py`
- 新增字段：`role`（String(20)，默认 "user"）
- 可选值：`user`（普通用户）、`admin`（管理员）
- 功能：区分普通用户和管理员权限

#### 1.3 调整 FileStorage 模型
- 文件：`backend/app/models/file_storage.py`
- 新增字段：`is_public`（Boolean，默认 False）
- 功能：标记公共文件，所有用户都能使用
- 保留：`chat_session_id` 字段，用于快速创建场景

#### 1.4 生成数据库迁移脚本
- 文件：`backend/alembic/versions/20260131_000002_add_role_and_visibility.py`
- 包含操作：
  - 添加 `User.role` 字段
  - 添加 `FileStorage.is_public` 字段
  - 创建 `chat_session_files` 表
  - 添加必要的索引
- 向下兼容：支持 `alembic upgrade head` 和 `alembic downgrade -1`

### 第二阶段：Schema 定义

#### 2.1 会话相关 Schema
- 文件：`backend/app/schemas/chat_session.py`
- 包含模型：
  - `ChatSessionBase`：基础模型
  - `ChatSessionCreate`：创建模型
  - `ChatSessionUpdate`：更新模型
  - `ChatSessionOut`：输出模型
  - `ChatSessionListResponse`：分页响应
  - `ChatSessionWithFiles`：带文件信息的会话

#### 2.2 消息相关 Schema
- 文件：`backend/app/schemas/chat_message.py`
- 包含模型：
  - `ChatMessageBase`：基础模型
  - `ChatMessageCreate`：创建模型
  - `ChatMessageOut`：输出模型
  - `ChatMessageListResponse`：分页响应
  - `ChatMessageIn`：API 输入模型

#### 2.3 文件相关 Schema
- 文件：`backend/app/schemas/file_storage.py`
- 包含模型：
  - `FileStorageBase`：基础模型
  - `FileUploadCreate`：上传模型
  - `FileStorageOut`：输出模型
  - `FileListResponse`：分页响应
  - `FileSessionRelation`：文件与会话关联模型
  - `FileInfoWithSessions`：带会话信息的文件

#### 2.4 Schema 导出
- 文件：`backend/app/schemas/__init__.py`
- 统一导出所有 Schema，便于其他模块引用

### 第三阶段：权限与认证基础

#### 3.1 权限检查依赖
- 文件：`backend/app/core/dependencies.py`
- 包含函数：
  - `get_current_user_optional()`：获取当前用户（可选）
  - `get_current_user()`：获取当前用户（必需）
  - `require_admin()`：要求管理员权限
  - `require_ownership()`：检查资源所有权

#### 3.2 设计说明
- JWT Token 认证（占位符实现，待后续完善）
- 角色权限控制（user/admin）
- 资源所有权检查（用户只能访问自己的资源）

### 第四阶段：CRUD 层实现

#### 4.1 会话 CRUD
- 文件：`backend/app/crud/chat_session_crud.py`
- 包含方法：
  - `create_session()`：创建会话
  - `get_user_sessions()`：查询用户会话列表（分页）
  - `get_session_by_id()`：根据 ID 获取会话
  - `get_user_session()`：获取用户会话（带权限检查）
  - `update_session()`：更新会话
  - `delete_session()`：删除会话
  - `get_session_with_file_count()`：获取会话详情（含文件数量）
  - `link_file_to_session()`：关联文件到会话
  - `unlink_file_from_session()`：取消文件与会话关联
  - `get_session_file_ids()`：获取会话关联的文件 ID
  - `get_session_files()`：获取会话关联的文件详情

#### 4.2 消息 CRUD
- 文件：`backend/app/crud/chat_message_crud.py`
- 包含方法：
  - `create_message()`：创建消息
  - `get_session_messages()`：查询会话消息列表（分页）
  - `get_recent_messages()`：获取最近 N 条消息（用于 AI 上下文）
  - `get_messages_after()`：获取某条消息之后的消息（增量拉取）
  - `get_message_by_id()`：根据 ID 获取消息
  - `get_user_session_messages()`：获取用户会话消息（带权限检查）
  - `delete_session_messages()`：删除会话的所有消息

#### 4.3 文件 CRUD
- 文件：`backend/app/crud/file_storage_crud.py`
- 包含方法：
  - `create_file()`：创建文件记录
  - `get_user_files()`：查询用户文件列表（含公共文件，分页）
  - `get_file_by_id()`：根据 ID 获取文件
  - `get_user_file()`：获取用户文件（带权限检查）
  - `get_public_files()`：查询公共文件列表（分页）
  - `update_file_status()`：更新文件状态
  - `delete_file()`：删除文件（硬删除）
  - `get_session_files()`：获取会话关联的文件
  - `get_file_usage_count()`：获取文件被多少个会话使用

#### 4.4 会话-文件关联 CRUD
- 文件：`backend/app/crud/chat_session_file_crud.py`
- 包含方法：
  - `add_file_to_session()`：为会话添加文件
  - `add_files_to_session()`：批量添加文件到会话
  - `remove_file_from_session()`：从会话中移除文件
  - `remove_files_from_session()`：批量移除文件
  - `get_session_file_ids()`：获取会话关联的所有文件 ID
  - `get_file_session_ids()`：获取文件被哪些会话使用
  - `check_file_in_session()`：检查文件是否在会话中
  - `remove_all_files_from_session()`：移除会话的所有文件关联

---

## 技术栈确认

- **认证方式**：JWT Token
- **文件分块策略**：混合策略（固定大小 + 语义分块 + 重叠）
- **AI 模型**：混合模式
  - 本地测试：langchain-ollama 调用本地 qwen2.5:0.6b
  - 可扩展：支持其他模型（OpenAI GPT-4o、阿里通义千问等）
- **会话消息历史**：固定数量（10 条消息）
- **向量数据库**：本地配置的 Milvus（已预留接口，未实现具体代码）

---

## 待完成的工作

### 第三阶段：Service 层实现（待实现）

#### 5.1 会话服务
- 文件：`backend/app/services/chat_session_service.py`（已有框架，需完善）
- 需要实现：
  - `create_session()`：创建会话
  - `list_sessions()`：查询会话列表
  - `get_session_detail()`：获取会话详情
  - `delete_session()`：删除会话
  - `attach_files()`：关联文件到会话
  - `detach_files()`：取消文件与会话关联

#### 5.2 消息服务
- 文件：`backend/app/services/chat_message_service.py`（待创建）
- 需要实现：
  - `send_message()`：发送消息
  - `get_message_history()`：获取消息历史
  - `generate_ai_response()`：调用 LangChain 生成 AI 回复（预留接口）

#### 5.3 文件服务
- 文件：`backend/app/services/file_storage_service.py`（待创建）
- 需要实现：
  - `upload_file()`：上传文件
  - `process_file_chunks()`：文件分块处理（预留接口）

### 第四阶段：API 接口实现（待实现）

#### 6.1 会话接口
- 文件：`backend/app/api/v1/endpoints/chat_sessions.py`（待创建）
- 需要实现的接口：
  - `POST /api/v1/sessions`：创建会话
  - `GET /api/v1/sessions`：查询会话列表（分页）
  - `GET /api/v1/sessions/{id}`：获取会话详情
  - `DELETE /api/v1/sessions/{id}`：删除会话
  - `POST /api/v1/sessions/{id}/files`：关联文件到会话
  - `DELETE /api/v1/sessions/{id}/files`：取消文件与会话关联

#### 6.2 消息接口
- 文件：`backend/app/api/v1/endpoints/chat_messages.py`（待创建）
- 需要实现的接口：
  - `POST /api/v1/sessions/{session_id}/messages`：发送消息
  - `GET /api/v1/sessions/{session_id}/messages`：查询消息历史（分页）

#### 6.3 文件接口
- 文件：`backend/app/api/v1/endpoints/files.py`（待创建）
- 需要实现的接口：
  - `POST /api/v1/files/upload`：上传文件
  - `GET /api/v1/files`：查询知识库文件列表（分页）
  - `GET /api/v1/files/{id}`：获取文件详情
  - `DELETE /api/v1/files/{id}`：删除文件
  - `GET /api/v1/files/public`：查询公共文件

#### 6.4 更新路由
- 文件：`backend/app/api/v1/router.py`（已有框架，需完善）
- 需要操作：
  - 注册新的路由模块

### 第五阶段：外部集成（仅思路，不实现具体代码）

#### 7.1 JWT 认证实现
- 实现 JWT Token 生成和验证
- 实现用户登录接口
- 实现 Token 刷新机制（可选）

#### 7.2 MinIO 集成
- 文件上传/下载
- 生成预签名 URL
- 文件删除

#### 7.3 Milvus 集成
- 创建集合（Collection）
- 插入向量数据
- 向量检索
- 删除向量

#### 7.4 LangChain 集成
- 构建 RAG Chain
- 从 Milvus 获取相关文档片段
- 结合用户消息历史生成回复
- 支持流式输出（WebSocket 或 SSE）

#### 7.5 Redis/RabbitMQ 集成
- 缓存用户会话列表
- 缓存文件元数据
- 异步处理文件分块任务
- 异步生成 embedding
- 异步写入 Milvus

---

## 注意事项

### 权限控制策略
1. **用户隔离**：普通用户只能访问自己的聊天会话和私有文件
2. **公共文件**：所有用户都可以访问公共文件，无需权限检查
3. **管理员权限**：管理员可以访问所有用户的会话，上传公共文件
4. **资源所有权**：所有 CRUD 操作都需要检查用户是否有权限访问该资源

### 性能优化建议
1. **分页查询**：所有列表接口都支持分页，避免大数据量查询
2. **索引优化**：已为常用查询条件添加索引
3. **缓存策略**：后续可引入 Redis 缓存热点数据
4. **异步处理**：文件分块和向量化等耗时操作建议异步处理

### 安全建议
1. **密码哈希**：用户密码必须存储哈希值，不可明文存储
2. **JWT 过期**：Token 应设置合理的过期时间
3. **权限校验**：所有接口都必须进行权限检查
4. **输入验证**：所有用户输入都应进行验证和清洗
5. **SQL 注入防护**：使用 ORM 参数化查询，避免拼接 SQL

---

## 下一步计划

1. ✅ **运行数据库迁移**：执行 `alembic upgrade head`
2. ⏳ **实现 Service 层**：完善会话、消息、文件服务
3. ⏳ **实现 API 接口**：创建会话、消息、文件接口
4. ⏳ **实现 JWT 认证**：完成用户登录和 Token 验证
5. ⏳ **实现文件上传**：集成 MinIO 对象存储
6. ⏳ **实现 LangChain RAG**：完成 AI 对话功能
7. ⏳ **实现文件分块和向量化**：集成 Milvus 向量数据库
8. ⏳ **添加 Redis 缓存和 RabbitMQ 异步任务**

---

## 代码特点

### 详细中文注释
- 所有模块、类、函数都包含详细的中文注释
- 注释包含说明、使用示例、参数说明、注意事项
- 便于后期开发人员学习和维护

### 规范的代码结构
- 严格分层：Models → Schemas → CRUD → Service → API
- 单一职责：每个模块只负责自己的功能
- 低耦合：模块之间通过清晰的接口交互

### 企业级开发实践
- 统一的响应格式（ApiResponse）
- 统一的异常处理
- 统一的日志记录
- 统一的权限控制
- 支持分页查询
- 支持软删除（通过 status 字段）

---

## 总结

已完成第一阶段和第二阶段的所有任务，为后续的 Service 层和 API 接口实现奠定了坚实的基础。所有代码都包含了详细的中文注释和使用示例，方便学习和维护。
