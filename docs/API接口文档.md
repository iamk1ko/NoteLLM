# API接口文档

[TOC]

## 1. 文档概述

本文档详细描述了 **NoteLLM** 后端项目的所有API接口设计，包括接口功能、请求方法、参数说明、响应格式、权限要求等信息。文档基于实际代码实现，旨在为前端开发人员和其他相关人员提供清晰的接口使用指南。

## 2. 接口版本与基础信息

- **API版本**: v1
- **接口路径前缀**: `/api/v1/`
- **响应格式**: 统一JSON格式（见本文档第3节）

## 3. 响应格式统一说明

所有API接口返回的响应格式统一为：

```json
{
  "code": 0,          // 业务状态码，0 表示成功
  "message": "OK",    // 提示信息
  "data": {},         // 响应数据
  "timestamp": "2024-01-01T00:00:00"  // 响应时间 (ISO 8601)
}
```

### 错误响应示例

```json
{
  "code": 404,
  "message": "文件不存在",
  "data": null,
  "timestamp": "2024-01-01T00:00:00"
}
```

## 4. 认证与权限说明

### 4.1 认证方式

- 登录成功后服务端下发 Cookie：`session_id`
- 前端后续请求需自动携带该 Cookie
- 退出登录将清理 Cookie 与服务端会话
- session_id 有效期由后端配置（默认 7 天）

### 4.2 权限说明

| 权限类型 | 说明 |
|---------|------|
| 无需登录 | 标记为无需登录的接口可以直接访问 |
| 需要登录 | 标记为需要登录的接口需要携带有效的 session_id Cookie |
| 普通用户权限 | 登录用户只能访问和操作自己的数据 |
| 管理员权限 | 管理员可以访问和操作所有用户的数据 |

## 5. 接口分类

---

### 5.1 认证接口 (auth)

#### 5.1.1 用户注册

- **功能说明**：注册新用户（本地学习阶段，密码明文存储）
- **请求方法**：POST
- **URL路径**：/auth/register
- **是否需要登录**：否
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
|--------|----------|----------|--------|------|
| username | string | 是 | 无 | 用户名 |
| password | string | 是 | 无 | 密码 |
| name | string | 是 | 无 | 姓名 |
| email | string | 否 | null | 邮箱 |

- **参数说明**：
  - username: 支持字母、数字、下划线，长度 1-20
  - password: 本地学习阶段明文传输，长度 1-255
  - name: 用户展示名称
  - email: 可选，若填写需保证唯一

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "id": 1,
      "username": "admin",
      "name": "管理员",
      "role": "user",
      "status": 1,
      "last_login_time": "2024-01-01T00:00:00",
      "gender": 3,
      "phone": "13800000000",
      "email": "admin@example.com",
      "avatar_file_id": 10,
      "bio": "这个人很懒,什么都没写",
      "create_time": "2024-01-01T00:00:00",
      "update_time": "2024-01-01T00:00:00"
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

#### 5.1.2 用户登录

- **功能说明**：用户登录（支持用户名或邮箱）
- **请求方法**：POST
- **URL路径**：/auth/login
- **是否需要登录**：否
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
|--------|----------|----------|--------|------|
| username_or_email | string | 是 | 无 | 用户名或邮箱 |
| password | string | 是 | 无 | 密码 |

- **参数说明**：
  - username_or_email: 支持用户名或邮箱
  - password: 明文比对

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "id": 1,
      "username": "admin",
      "name": "管理员",
      "role": "admin",
      "status": 1,
      "last_login_time": "2024-01-01T00:00:00",
      "gender": 3,
      "phone": "13800000000",
      "email": "admin@example.com",
      "avatar_file_id": 10,
      "bio": "这个人很懒,什么都没写",
      "create_time": "2024-01-01T00:00:00",
      "update_time": "2024-01-01T00:00:00"
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

#### 5.1.3 用户退出登录

- **功能说明**：退出登录并清理会话
- **请求方法**：POST
- **URL路径**：/auth/logout
- **是否需要登录**：是
- **请求参数**：无

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "success": true
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

---

### 5.2 用户管理接口 (users)

#### 5.2.1 获取所有用户列表

- **功能说明**：获取所有用户列表（不分页，适合数据量小场景）
- **请求方法**：GET
- **URL路径**：/users
- **是否需要登录**：是（仅管理员）
- **请求参数**：无

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": [
      {
        "id": 1,
        "username": "admin",
        "name": "管理员",
        "email": "admin@example.com",
        "role": "admin",
        "status": 1,
        "last_login_time": "2024-01-01T00:00:00",
        "gender": 3,
        "phone": "13800000000",
        "avatar_file_id": 10,
        "bio": "这个人很懒,什么都没写",
        "create_time": "2024-01-01T00:00:00",
        "update_time": "2024-01-01T00:00:00"
      }
    ],
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

#### 5.2.2 分页查询用户列表

- **功能说明**：分页查询用户列表，支持关键词搜索
- **请求方法**：GET
- **URL路径**：/users/page
- **是否需要登录**：是（仅管理员）
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
|--------|----------|----------|--------|------|
| page | integer | 否 | 1 | 页码，从1开始 |
| size | integer | 否 | 10 | 每页数量，1-100 |
| keyword | string | 否 | null | 模糊搜索关键词（匹配username/name/phone/email） |

- **参数说明**：
  - keyword: 为空时返回全部

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "items": [
        {
          "id": 1,
          "username": "admin",
          "name": "管理员",
          "email": "admin@example.com",
          "role": "admin",
          "status": 1,
          "last_login_time": "2024-01-01T00:00:00",
          "gender": 3,
          "phone": "13800000000",
          "avatar_file_id": 10,
          "bio": "这个人很懒,什么都没写",
          "create_time": "2024-01-01T00:00:00",
          "update_time": "2024-01-01T00:00:00"
        }
      ],
      "total": 1,
      "page": 1,
      "size": 10
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

#### 5.2.3 获取当前登录用户信息

- **功能说明**：获取当前登录用户的详细信息
- **请求方法**：GET
- **URL路径**：/users/me
- **是否需要登录**：是
- **请求参数**：无

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "id": 1,
      "username": "admin",
      "name": "管理员",
      "role": "admin",
      "status": 1,
      "last_login_time": "2024-01-01T00:00:00",
      "gender": 3,
      "phone": "13800000000",
      "email": "admin@example.com",
      "avatar_file_id": 10,
      "bio": "这个人很懒,什么都没写",
      "create_time": "2024-01-01T00:00:00",
      "update_time": "2024-01-01T00:00:00"
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

#### 5.2.4 获取用户详情

- **功能说明**：获取指定用户的详细信息
- **请求方法**：GET
- **URL路径**：/users/{user_id}
- **是否需要登录**：是
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
|--------|----------|----------|--------|------|
| user_id | integer | 是 | 无 | 用户ID |

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "id": 1,
      "username": "admin",
      "name": "管理员",
      "role": "admin",
      "status": 1,
      "last_login_time": "2024-01-01T00:00:00",
      "gender": 3,
      "phone": "13800000000",
      "email": "admin@example.com",
      "avatar_file_id": 10,
      "bio": "这个人很懒,什么都没写",
      "create_time": "2024-01-01T00:00:00",
      "update_time": "2024-01-01T00:00:00"
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

#### 5.2.5 创建用户

- **功能说明**：创建新用户
- **请求方法**：POST
- **URL路径**：/users
- **是否需要登录**：是（仅管理员）
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
|--------|----------|----------|--------|------|
| username | string | 是 | 无 | 用户名 |
| password | string | 是 | 无 | 密码 |
| name | string | 是 | 无 | 姓名 |
| gender | string | 否 | null | 性别 |
| phone | string | 否 | null | 电话 |
| email | string | 否 | null | 邮箱 |
| avatar_file_id | integer | 否 | null | 头像文件ID |
| bio | string | 否 | null | 个人简介 |

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "id": 1,
      "username": "admin",
      "name": "管理员",
      "role": "user",
      "status": 1,
      "last_login_time": "2024-01-01T00:00:00",
      "gender": 3,
      "phone": "13800000000",
      "email": "admin@example.com",
      "avatar_file_id": 10,
      "bio": "这个人很懒,什么都没写",
      "create_time": "2024-01-01T00:00:00",
      "update_time": "2024-01-01T00:00:00"
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

#### 5.2.6 更新用户

- **功能说明**：更新用户信息
- **请求方法**：PUT
- **URL路径**：/users/{user_id}
- **是否需要登录**：是
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
|--------|----------|----------|--------|------|
| user_id | integer | 是 | 无 | 用户ID |
| name | string | 否 | null | 姓名 |
| gender | string | 否 | null | 性别 |
| phone | string | 否 | null | 电话 |
| email | string | 否 | null | 邮箱 |
| avatar_file_id | integer | 否 | null | 头像文件ID |
| bio | string | 否 | null | 个人简介 |

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "id": 1,
      "username": "admin",
      "name": "管理员",
      "role": "user",
      "status": 1,
      "last_login_time": "2024-01-01T00:00:00",
      "gender": 3,
      "phone": "13800000000",
      "email": "admin@example.com",
      "avatar_file_id": 10,
      "bio": "这个人很懒,什么都没写",
      "create_time": "2024-01-01T00:00:00",
      "update_time": "2024-01-01T00:00:00"
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

#### 5.2.7 删除用户

- **功能说明**：删除指定用户
- **请求方法**：DELETE
- **URL路径**：/users/{user_id}
- **是否需要登录**：是（仅管理员）
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
|--------|----------|----------|--------|------|
| user_id | integer | 是 | 无 | 用户ID |

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "success": true
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

---

### 5.3 会话管理接口 (chat_sessions)

#### 5.3.1 创建会话

- **功能说明**：创建新的聊天会话
- **请求方法**：POST
- **URL路径**：/sessions
- **是否需要登录**：是
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
|--------|----------|----------|--------|------|
| title | string | 否 | null | 会话标题 |
| biz_type | string | 否 | "ai_chat" | 业务类型，如'ai_chat' |
| context_id | string | 否 | null | 外部上下文ID，如PDF文档ID |
| status | integer | 否 | 1 | 会话状态：1-正常，0-删除 |

- **参数说明**：
  - biz_type: ai_chat / pdf_qa / customer_service
  - status: 1-正常，0-删除

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "title": "测试会话",
      "biz_type": "ai_chat",
      "context_id": null,
      "status": 1,
      "id": 1,
      "user_id": 1,
      "create_time": "2024-01-01T00:00:00",
      "update_time": "2024-01-01T00:00:00",
      "file_count": null
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

#### 5.3.2 查询会话列表

- **功能说明**：分页查询会话列表
- **请求方法**：GET
- **URL路径**：/sessions
- **是否需要登录**：是
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
|--------|----------|----------|--------|------|
| page | integer | 否 | 1 | 页码，从1开始 |
| size | integer | 否 | 10 | 每页数量，1-100 |
| biz_type | string | 否 | null | 业务类型过滤 |
| user_id | integer | 否 | null | 管理员可指定用户ID |

- **参数说明**：
  - biz_type: 为空返回全部
  - user_id: 仅管理员生效

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "items": [
        {
          "id": 1,
          "title": "测试会话",
          "biz_type": "ai_chat",
          "context_id": null,
          "user_id": 1,
          "status": 1,
          "create_time": "2024-01-01T00:00:00",
          "update_time": "2024-01-01T00:00:00",
          "file_count": 2
        }
      ],
      "total": 1,
      "page": 1,
      "size": 10
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

#### 5.3.3 获取会话详情

- **功能说明**：获取会话详细信息，包括关联文件ID列表
- **请求方法**：GET
- **URL路径**：/sessions/{session_id}
- **是否需要登录**：是
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
|--------|----------|----------|--------|------|
| session_id | integer | 是 | 无 | 会话ID |

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "id": 1,
      "title": "测试会话",
      "biz_type": "ai_chat",
      "context_id": null,
      "user_id": 1,
      "status": 1,
      "create_time": "2024-01-01T00:00:00",
      "update_time": "2024-01-01T00:00:00",
      "file_count": 2,
      "files": [1, 2, 3]
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

#### 5.3.4 删除会话

- **功能说明**：删除指定会话
- **请求方法**：DELETE
- **URL路径**：/sessions/{session_id}
- **是否需要登录**：是
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
|--------|----------|----------|--------|------|
| session_id | integer | 是 | 无 | 会话ID |

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "success": true
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

#### 5.3.5 关联文件到会话

- **功能说明**：将文件关联到指定会话
- **请求方法**：POST
- **URL路径**：/sessions/{session_id}/files
- **是否需要登录**：是
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
|--------|----------|----------|--------|------|
| session_id | integer | 是 | 无 | 会话ID |
| file_ids | array[integer] | 是 | 无 | 文件ID列表，至少一个 |

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "success": true,
      "count": 2
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

#### 5.3.6 取消文件与会话关联

- **功能说明**：取消文件与会话的关联
- **请求方法**：DELETE
- **URL路径**：/sessions/{session_id}/files
- **是否需要登录**：是
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
|--------|----------|----------|--------|------|
| session_id | integer | 是 | 无 | 会话ID |
| file_ids | array[integer] | 是 | 无 | 文件ID列表，至少一个 |

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "success": true,
      "count": 1
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

#### 5.3.7 生成会话总结笔记

- **功能说明**：触发AI根据当前会话的历史记录，生成一份结构化的Markdown总结笔记
- **请求方法**：POST
- **URL路径**：/sessions/{session_id}/summary
- **是否需要登录**：是
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 说明 |
|--------|----------|----------|------|
| session_id | integer | 是 | 会话ID |
| focus_topics | array[string] | 否 | 指定总结的关注点/主题 |

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "summary_content": "# 笔记总结\n\n## 核心结论\n- 结论1\n- 结论2\n\n## 行动建议\n- 建议1\n- 建议2",
      "created_at": "2024-01-01T00:00:00"
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

---

### 5.4 消息管理接口 (chat_messages)

#### 5.4.1 发送消息

- **功能说明**：在指定会话中发送消息
- **请求方法**：POST
- **URL路径**：/sessions/{session_id}/messages
- **是否需要登录**：是
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
|--------|----------|----------|--------|------|
| session_id | integer | 是 | 无 | 会话ID |
| content | string | 是 | 无 | 消息内容 |
| role | string | 否 | "user" | 消息角色，如user、assistant |
| model_name | string | 否 | null | 模型名称 |

- **参数说明**：
  - role: user / assistant / system / tool

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "id": 1,
      "session_id": 1,
      "user_id": 1,
      "role": "user",
      "content": "你好",
      "model_name": null,
      "token_count": null,
      "create_time": "2024-01-01T00:00:00"
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

#### 5.4.2 查询消息历史

- **功能说明**：获取指定会话的消息历史记录
- **请求方法**：GET
- **URL路径**：/sessions/{session_id}/messages
- **是否需要登录**：是
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
|--------|----------|----------|--------|------|
| session_id | integer | 是 | 无 | 会话ID |
| page | integer | 否 | 1 | 页码，从1开始 |
| size | integer | 否 | 20 | 每页数量，1-200 |

- **参数说明**：
  - page: 从 1 开始
  - size: 最大 200

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "items": [
        {
          "id": 1,
          "session_id": 1,
          "user_id": 1,
          "role": "user",
          "content": "你好",
          "model_name": null,
          "token_count": null,
          "create_time": "2024-01-01T00:00:00"
        }
      ],
      "total": 1,
      "page": 1,
      "size": 20
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

---

### 5.5 文件管理接口 (files)

#### 5.5.1 简单单文件上传

- **功能说明**：上传单个文件（适合前端直接上传）
- **请求方法**：POST
- **URL路径**：/files
- **是否需要登录**：是
- **请求参数**：multipart/form-data

| 参数名 | 类型 | 是否必填 | 说明 |
|--------|------|----------|------|
| file | file | 是 | 上传的文件 |

- **去重说明**：
  - 同一用户上传相同 MD5 文件时返回 exists=true
  - status=FAILED 时允许重新上传
  - status=UPLOADING 时允许继续分片上传（断点续传）

- **响应格式**：
  - 成功响应：
    ```json
    {
      "code": 0,
      "message": "OK",
      "data": {
        "exists": false,
        "file": {
          "id": 1,
          "user_id": 1,
          "filename": "test.pdf",
          "file_size": 1024,
          "content_type": "application/pdf",
          "bucket_name": "rag-files",
          "object_name": "abc12345/test.pdf",
          "etag": "abc12345",
          "is_public": false,
          "status": 1,
          "upload_time": "2024-01-01T00:00:00",
          "update_time": "2024-01-01T00:00:00",
          "uploader_name": "管理员"
        }
      },
      "timestamp": "2024-01-01T00:00:00"
    }
    ```

  - 重复上传响应（用户内重复）：
    ```json
    {
      "code": 0,
      "message": "OK",
      "data": {
        "exists": true,
        "file_id": 1,
        "filename": "test.pdf",
        "status": 2,
        "upload_time": "2024-01-01T00:00:00"
      },
      "timestamp": "2024-01-01T00:00:00"
    }
    ```

#### 5.5.2 分片上传

- **功能说明**：上传文件分片（支持断点续传）
- **请求方法**：POST
- **URL路径**：/files/upload/chunk
- **是否需要登录**：是
- **请求参数**：multipart/form-data

| 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
|--------|----------|----------|--------|------|
| file_md5 | string | 是 | 无 | 文件MD5 |
| chunk_index | integer | 是 | 无 | 分片索引，从0开始 |
| total_chunks | integer | 是 | 无 | 总分片数 |
| chunk_size | integer | 是 | 无 | 当前分片大小（字节） |
| total_size | integer | 是 | 无 | 文件总大小（字节） |
| file_name | string | 是 | 无 | 文件名称 |
| content_type | string | 是 | 无 | 文件MIME类型 |
| is_public | boolean | 否 | false | 是否为公共文件 |
| file_chunk | file | 是 | 无 | 分片文件本体 |

- **参数说明**：
  - chunk_index: 从 0 开始
  - total_chunks: 分片总数
  - total_size: 文件总大小

- **去重说明**：
  - 同一用户上传相同 MD5 文件时返回 exists=true
  - status=FAILED 时允许重新上传

- **响应格式**：
  - 成功响应：
    ```json
    {
      "code": 0,
      "message": "OK",
      "data": {
        "file_md5": "abc12345",
        "chunk_md5": "def67890",
        "chunk_index": 0,
        "uploaded": true,
        "file_id": 1
      },
      "timestamp": "2024-01-01T00:00:00"
    }
    ```

  - 重复上传响应（用户内重复）：
    ```json
    {
      "code": 0,
      "message": "OK",
      "data": {
        "exists": true,
        "file_id": 1,
        "status": 2
      },
      "timestamp": "2024-01-01T00:00:00"
    }
    ```

#### 5.5.3 检查文件是否已存在

- **功能说明**：检查当前用户是否已上传同MD5文件
- **请求方法**：GET
- **URL路径**：/files/check
- **是否需要登录**：是
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
|--------|----------|----------|--------|------|
| file_md5 | string | 是 | 无 | 文件MD5 |

- **去重说明**：
  - status=FAILED 时返回 exists=false，允许重新上传

- **响应格式**：
  - 文件已存在：
    ```json
    {
      "code": 0,
      "message": "OK",
      "data": {
        "exists": true,
        "file_id": 1,
        "filename": "test.pdf",
        "status": 2,
        "upload_time": "2024-01-01T00:00:00"
      },
      "timestamp": "2024-01-01T00:00:00"
    }
    ```
  - 文件不存在或允许重传：
    ```json
    {
      "code": 0,
      "message": "OK",
      "data": {
        "exists": false,
        "file_id": null,
        "filename": null,
        "status": null,
        "upload_time": null
      },
      "timestamp": "2024-01-01T00:00:00"
    }
    ```

#### 5.5.4 检查上传完成状态

- **功能说明**：检查文件是否已经完成上传并合并
- **请求方法**：GET
- **URL路径**：/files/upload/is_complete/{file_id}
- **是否需要登录**：是
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
|--------|----------|----------|--------|------|
| file_id | integer | 是 | 无 | 文件ID |

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "id": 1,
      "user_id": 1,
      "filename": "test.pdf",
      "file_size": 1024,
      "content_type": "application/pdf",
      "bucket_name": "rag-files",
      "object_name": "abc12345/test.pdf",
      "etag": "abc12345",
      "is_public": false,
      "status": 1,
      "upload_time": "2024-01-01T00:00:00",
      "update_time": "2024-01-01T00:00:00",
      "uploader_name": "管理员"
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

#### 5.5.5 查询文件列表

- **功能说明**：分页查询用户文件列表
- **请求方法**：GET
- **URL路径**：/files
- **是否需要登录**：是
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
|--------|----------|----------|--------|------|
| page | integer | 否 | 1 | 页码，从1开始 |
| size | integer | 否 | 10 | 每页数量，1-100 |
  | include_public | boolean | 否 | true | 是否包含公共文件 |
  | keyword | string | 否 | null | 文件名搜索关键词 |
  | status | integer | 否 | null | 文件状态 |
  | content_type | string | 否 | null | 文件MIME类型 |

- **参数说明**：
  - status 支持：0-上传中，1-已上传，2-已向量化，3-失败
  - content_type 示例：application/pdf、text/markdown

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "items": [
        {
          "id": 1,
          "user_id": 1,
          "filename": "test.pdf",
          "file_size": 1024,
          "content_type": "application/pdf",
          "bucket_name": "rag-files",
          "object_name": "abc12345/test.pdf",
          "etag": "abc12345",
          "is_public": false,
          "status": 2,
          "upload_time": "2024-01-01T00:00:00",
          "update_time": "2024-01-01T00:00:00",
          "uploader_name": "管理员"
        }
      ],
      "total": 1,
      "page": 1,
      "size": 10
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

#### 5.5.6 获取文件详情

- **功能说明**：获取文件详细信息
- **请求方法**：GET
- **URL路径**：/files/{file_id}
- **是否需要登录**：是
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
|--------|----------|----------|--------|------|
| file_id | integer | 是 | 无 | 文件ID |

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "file": {
        "id": 1,
        "user_id": 1,
        "filename": "test.pdf",
        "file_size": 1024,
        "content_type": "application/pdf",
        "bucket_name": "rag-files",
        "object_name": "abc12345/test.pdf",
        "etag": "abc12345",
        "is_public": false,
        "status": 0,
        "upload_time": "2024-01-01T00:00:00",
        "update_time": "2024-01-01T00:00:00",
        "uploader_name": "管理员"
      },
      "progress": {
        "uploaded_chunks": 3,
        "total_chunks": 10
      }
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```
  - 说明：仅当 status=UPLOADING 且存在 file_md5 时返回 progress

#### 5.5.7 获取文件预览地址

- **功能说明**：获取文件的临时预览链接（MinIO Presigned URL）
- **请求方法**：GET
- **URL路径**：/files/{file_id}/preview
- **是否需要登录**：是
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
|--------|----------|----------|--------|------|
| file_id | integer | 是 | 无 | 文件ID |

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "url": "http://minio:9000/bucket/file.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=test%2F20240101%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20240101T000000Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=abcdef123456"
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

#### 5.5.8 查询公共文件列表

- **功能说明**：分页查询公共文件列表
- **请求方法**：GET
- **URL路径**：/files/public
- **是否需要登录**：否
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
|--------|----------|----------|--------|------|
| page | integer | 否 | 1 | 页码，从1开始 |
| size | integer | 否 | 10 | 每页数量，1-100 |

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "items": [
        {
          "id": 1,
          "user_id": 2,
          "filename": "public.pdf",
          "file_size": 2048,
          "content_type": "application/pdf",
          "bucket_name": "rag-public",
          "object_name": "def67890/public.pdf",
          "etag": "def67890",
          "is_public": true,
          "status": 2,
          "upload_time": "2024-01-01T00:00:00",
          "update_time": "2024-01-01T00:00:00",
          "uploader_name": "用户A"
        }
      ],
      "total": 1,
      "page": 1,
      "size": 10
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

#### 5.5.9 删除文件

- **功能说明**：删除指定文件（硬删除：MinIO/Redis/Milvus/MySQL）
- **请求方法**：DELETE
- **URL路径**：/files/{file_id}
- **是否需要登录**：是
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
|--------|----------|----------|--------|------|
| file_id | integer | 是 | 无 | 文件ID |

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "success": true
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

> **注意**：删除文件时，系统会自动删除与该文件关联的所有聊天会话。

#### 5.5.10 文件状态查询

- **功能说明**：获取文件状态与上传进度
- **请求方法**：GET
- **URL路径**：/files/{file_id}/status
- **是否需要登录**：是
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
|--------|----------|----------|--------|------|
| file_id | integer | 是 | 无 | 文件ID |

- **参数说明**：
  - progress: 仅上传中返回，其他状态为 null

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "file_id": 1,
      "status": 0,
      "upload_time": "2024-01-01T00:00:00",
      "update_time": "2024-01-01T00:00:00",
      "progress": {
        "uploaded_chunks": 3,
        "total_chunks": 10
      }
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

#### 5.5.11 重新向量化文件

- **功能说明**：重新触发文件的向量化任务（仅当文件状态为失败时可用）
- **请求方法**：POST
- **URL路径**：/files/{file_id}/retry
- **是否需要登录**：是
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
|--------|----------|----------|--------|------|
| file_id | integer | 是 | 无 | 文件ID |

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "success": true,
      "message": "向量化任务已重新发布"
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

 - **错误响应**（文件状态不是失败时）：
  ```json
  {
    "code": 400,
    "message": "只有失败状态的文件可以重新向量化，当前状态: 3",
    "data": null,
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

---

### 5.6 社区分享接口 (community)

#### 5.6.1 发布分享

- **功能说明**：将个人会话及关联文档发布到社区广场
- **请求方法**：POST
- **URL路径**：/shares
- **是否需要登录**：是
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 说明 |
|--------|----------|----------|------|
| source_file_id | integer | 是 | 原始文件ID |
| session_id | integer | 是 | 关联会话ID (包含问答记录) |
| title | string | 是 | 分享标题 |
| description | string | 否 | 分享描述/推荐语 |
| tags | array[string] | 否 | 标签列表，如 ["Python", "学习笔记"] |
| is_public_source | boolean | 否 | 是否公开原始文件下载 (默认false，仅分享问答) |

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "share_id": 101,
      "publish_time": "2024-01-01T00:00:00"
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

#### 5.6.2 获取社区列表

- **功能说明**：分页获取社区分享列表
- **请求方法**：GET
- **URL路径**：/shares
- **是否需要登录**：是
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
|--------|----------|----------|--------|------|
| page | integer | 否 | 1 | 页码，默认1 |
| size | integer | 否 | 10 | 每页数量，默认10 |
| sort | string | 否 | "latest" | 排序方式: "latest"(最新), "popular"(最热) |
| tag | string | 否 | null | 按标签筛选 |

- **参数说明**：
  - sort: latest / popular
  - tag: 单个标签过滤

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "items": [
        {
          "id": 101,
          "title": "Python面试题",
          "description": "整理了常见面试题并提供简要答案",
          "tags": ["Python", "面试"],
          "user_id": 1,
          "user_name": "TechGuru",
          "view_count": 1240,
          "like_count": 45,
          "fork_count": 12,
          "create_time": "2024-02-20T10:00:00",
          "is_liked": false
        }
      ],
      "total": 1,
      "page": 1,
      "size": 10
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

#### 5.6.3 转存/Fork分享

- **功能说明**：将他人的分享内容（文档副本+会话副本）保存到自己的空间
- **请求方法**：POST
- **URL路径**：/shares/{share_id}/fork
- **是否需要登录**：是
- **请求参数**：无

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "new_file_id": 205,
      "new_session_id": 302
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

#### 5.6.4 社区点赞

- **功能说明**：对某个分享进行点赞或取消点赞
- **请求方法**：POST
- **URL路径**：/shares/{share_id}/like
- **是否需要登录**：是
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 说明 |
|--------|----------|----------|------|
| action | string | 是 | "like" 或 "unlike" |

- **参数说明**：
  - action: like / unlike

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "success": true,
      "like_count": 46
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

---

### 5.7 健康检查接口 (health)

#### 5.7.1 健康检查

- **功能说明**：用于探活与快速验证服务可用性
- **请求方法**：GET
- **URL路径**：/health
- **是否需要登录**：否
- **请求参数**：无

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "status": "ok"
    },
    "timestamp": "2024-01-01T00:00:00"
  }
  ```

---

## 6. 注意事项

1. 所有需要登录的接口都需要在请求中携带有效的 session_id Cookie
2. 文件上传接口需要使用 multipart/form-data 格式提交
3. 分页查询接口的 page 参数从 1 开始
4. 所有时间字段返回格式为 ISO 8601 格式
5. 错误响应的 code 字段与 HTTP 状态码一致，或为特定业务错误码
6. 基础设施客户端（Redis/MinIO/RabbitMQ/Milvus）统一在应用启动时初始化，并通过依赖注入获取实例

---

## 7. 字段字典

### 7.1 文件状态 (file.status)

| 值 | 含义 |
|----|------|
| 0 | 上传中 |
| 1 | 已上传 |
| 2 | 已向量化 |
| 3 | 失败 |

### 7.2 会话状态 (session.status)

| 值 | 含义 |
|----|------|
| 1 | 正常 |
| 0 | 删除 |

### 7.3 会话业务类型 (session.biz_type)

| 值 | 含义 |
|----|------|
| ai_chat | 通用对话 |
| pdf_qa | 文档问答 |
| customer_service | 客服场景 |

### 7.4 消息角色 (message.role)

| 值 | 含义 |
|----|------|
| user | 用户输入 |
| assistant | AI 回复 |
| system | 系统提示 |
| tool | 工具调用 |

### 7.5 社区列表排序 (community.sort)

| 值 | 含义 |
|----|------|
| latest | 最新 |
| popular | 最热 |

### 7.6 点赞动作 (community.action)

| 值 | 含义 |
|----|------|
| like | 点赞 |
| unlike | 取消点赞 |

---

## 8. 待实现接口 (Feature Wishlist)

以下接口为前端已实现但后端尚未支持的功能，标记为"待实现"。

### 8.1 重新生成回答 (Regenerate Response)

- **功能说明**：重新生成AI回答（当用户对回答不满意时）
- **请求方法**：POST
- **URL路径**：/sessions/{session_id}/messages/regenerate
- **是否需要登录**：是
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 说明 |
|--------|----------|----------|------|
| session_id | integer | 是 | 会话ID |
| message_id | integer | 否 | 需要重新生成的消息ID（默认最后一条） |

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "message": {
        "id": 123,
        "session_id": 1,
        "content": "这是重新生成的回答...",
        "role": "assistant",
        "create_time": "2024-01-01T12:00:00"
      }
    },
    "timestamp": "2024-01-01T12:00:00"
  }
  ```

### 8.2 消息反馈 (Message Feedback)

- **功能说明**：用户对AI回答进行评价（点赞/踩）
- **请求方法**：POST
- **URL路径**：/sessions/{session_id}/messages/{message_id}/feedback
- **是否需要登录**：是
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 说明 |
|--------|----------|----------|------|
| feedback_type | string | 是 | 反馈类型： thumbs_up (点赞) / thumbs_down (踩) |
| feedback_reason | string | 否 | 反馈原因（可选） |

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "success": true
    },
    "timestamp": "2024-01-01T12:00:00"
  }
  ```

### 8.3 获取对话Token统计 (Token Usage Stats)

- **功能说明**：获取当前会话的Token使用统计
- **请求方法**：GET
- **URL路径**：/sessions/{session_id}/usage
- **是否需要登录**：是
- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "total_tokens": 1500,
      "prompt_tokens": 500,
      "completion_tokens": 1000,
      "cost": 0.005
    },
    "timestamp": "2024-01-01T12:00:00"
  }
  ```

### 8.4 编辑消息 (Edit Message)

- **功能说明**：用户编辑已发送的消息并重新获取AI回答
- **请求方法**：PUT
- **URL路径**：/sessions/{session_id}/messages/{message_id}
- **是否需要登录**：是
- **请求参数**：

| 参数名 | 数据类型 | 是否必填 | 说明 |
|--------|----------|----------|------|
| content | string | 是 | 新的消息内容 |

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "message": {
        "id": 123,
        "session_id": 1,
        "content": "这是编辑后的内容及新的AI回复...",
        "role": "assistant",
        "create_time": "2024-01-01T12:00:00"
      }
    },
    "timestamp": "2024-01-01T12:00:00"
  }
  ```
