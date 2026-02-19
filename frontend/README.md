# RAG 前端验证台

快速验证后端 API 业务流程的 Vue3 前端项目。

## 技术栈

- Vue3 + TypeScript
- Vite
- Element Plus
- Pinia
- Vue Router
- ESLint + Prettier

## 环境配置

复制 `.env` 并根据实际后端地址调整：

```
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_API_TOKEN=Bearer dev-token
```

## 启动项目

```
npm install
npm run dev
```

## 页面说明

- 文件上传：分片上传、MD5 计算、实时进度
- 文件列表：查看文件状态（上传中/已上传/已向量化/失败）
- 检索验证：创建会话、发送消息、查看消息历史

## 关键接口

- `POST /files/upload/chunk`
- `GET /files/upload/is_complete/{file_id}`
- `GET /files`
- `DELETE /files/{file_id}`
- `POST /sessions`
- `GET /sessions`
- `POST /sessions/{session_id}/messages`
- `GET /sessions/{session_id}/messages`
- `GET /health`
- `GET /infra/demo`

## 注意事项

- 后端接口默认需要 Authorization，请在 `.env` 中提供固定 Token。
- 上传与向量化状态依赖后端任务队列与存储服务运行状态。
