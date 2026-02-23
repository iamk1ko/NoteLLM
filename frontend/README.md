# NoteLLM 前端

基于 Vue3 + TypeScript + Vite 构建的 NoteLLM 前端应用，支持文档上传、文件管理、智能问答与问答记录导出。

## 功能模块

- 文件上传：支持 PDF / MD / Word / TXT，显示上传进度与反馈
- 文件列表：展示文件名称、上传时间、大小与向量化状态
- 文件详情：预览、向量化状态、问答记录与检索片段
- 问答中心：按文件提问并查看相关片段
- 问答导出：导出问答记录为 PDF（占位接口）
- 账户模块：预留注册/登录/账户接口占位

## 启动

```bash
npm install
npm run dev
```

## 环境变量

复制 `.env` 并按需修改：

```
VITE_API_BASE_URL=http://localhost:8000/api
```

## API 占位说明

| 模块 | 方法 | 路径 | 说明 |
| --- | --- | --- | --- |
| 文件列表 | GET | /files | 获取文件列表 |
| 文件详情 | GET | /files/:id | 获取文件详情 |
| 上传文件 | POST | /files | 上传文件（multipart/form-data） |
| 删除文件 | DELETE | /files/:id | 删除文件 |
| 问答 | POST | /qa | 提问（fileId 可选） |
| 问答历史 | GET | /qa | 获取问答记录（fileId 可选） |
| 问答导出 | POST | /export/qa | 导出问答记录 PDF |
| 账户注册 | POST | /auth/register | 预留 |
| 账户登录 | POST | /auth/login | 预留 |
| 账户详情 | GET | /auth/profile | 预留 |

## 目录结构

```
src
  components
  views
  store
  router
  services
  utils
  assets
  App.vue
  main.ts
```
