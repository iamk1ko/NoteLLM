# API接口文档

## 1. 文档概述

本文档详细描述了My-RAG-Demo后端项目的所有API接口设计，包括接口功能、请求方法、参数说明、响应格式、权限要求等信息。文档基于实际代码实现，旨在为前端开发人员和其他相关人员提供清晰的接口使用指南。

## 2. 接口分类

### 2.1 会话管理接口 (chat_sessions)

#### 2.1.1 创建会话

- **功能说明**：创建新的聊天会话
- **请求方法**：POST
- **URL路径**：/sessions
- **请求参数**：
  
  | 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
  |--------|----------|----------|--------|------|
  | title | string | 是 | 无 | 会话标题 |
  | biz_type | string | 是 | 无 | 业务类型，如'ai_chat' |
  | context_id | integer | 否 | null | 上下文ID |
- **响应格式**：
  
  - 成功响应：
    ```json
    {
      "code": 200,
      "message": "success",
      "data": {
        "id": 1,
        "title": "测试会话",
        "biz_type": "ai_chat",
        "context_id": null,
        "user_id": 1,
        "status": 1,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00"
      }
    }
    ```
  - 错误响应：
    ```json
    {
      "code": 401,
      "message": "未授权",
      "data": null
    }
    ```
- **状态码说明**：
  - 200：成功
  - 401：未授权
- **权限要求**：需要登录
- **调用示例**：
  ```bash
  curl -X POST "http://localhost:8000/api/v1/sessions" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"title": "测试会话", "biz_type": "ai_chat"}'
  ```

#### 2.1.2 查询会话列表

- **功能说明**：分页查询会话列表
- **请求方法**：GET
- **URL路径**：/sessions
- **请求参数**：
  | 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
  |--------|----------|----------|--------|------|
  | page | integer | 否 | 1 | 页码，从1开始 |
  | size | integer | 否 | 10 | 每页数量，1-100 |
  | biz_type | string | 否 | null | 业务类型过滤 |
  | user_id | integer | 否 | null | 管理员可指定用户ID |
- **响应格式**：
  - 成功响应：
    ```json
    {
      "code": 200,
      "message": "success",
      "data": {
        "items": [
          {
            "id": 1,
            "title": "测试会话",
            "biz_type": "ai_chat",
            "context_id": null,
            "user_id": 1,
            "status": 1,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
          }
        ],
        "total": 1,
        "page": 1,
        "size": 10
      }
    }
    ```
- **状态码说明**：
  - 200：成功
  - 401：未授权
- **权限要求**：需要登录，普通用户只能查看自己的会话，管理员可查看全部
- **调用示例**：
  ```bash
  curl -X GET "http://localhost:8000/api/v1/sessions?page=1&size=10" \
  -H "Authorization: Bearer {token}"
  ```

#### 2.1.3 获取会话详情

- **功能说明**：获取会话详细信息，包括关联文件ID列表
- **请求方法**：GET
- **URL路径**：/sessions/{session_id}
- **请求参数**：
  | 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
  |--------|----------|----------|--------|------|
  | session_id | integer | 是 | 无 | 会话ID |
- **响应格式**：
  - 成功响应：
    ```json
    {
      "code": 200,
      "message": "success",
      "data": {
        "id": 1,
        "title": "测试会话",
        "biz_type": "ai_chat",
        "context_id": null,
        "user_id": 1,
        "status": 1,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
        "files": [1, 2, 3]
      }
    }
    ```
  - 错误响应：
    ```json
    {
      "code": 404,
      "message": "会话不存在或无权限",
      "data": null
    }
    ```
- **状态码说明**：
  - 200：成功
  - 401：未授权
  - 404：会话不存在或无权限
- **权限要求**：需要登录，普通用户只能查看自己的会话
- **调用示例**：
  ```bash
  curl -X GET "http://localhost:8000/api/v1/sessions/1" \
  -H "Authorization: Bearer {token}"
  ```

#### 2.1.4 删除会话

- **功能说明**：删除指定会话
- **请求方法**：DELETE
- **URL路径**：/sessions/{session_id}
- **请求参数**：
  | 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
  |--------|----------|----------|--------|------|
  | session_id | integer | 是 | 无 | 会话ID |
- **响应格式**：
  - 成功响应：
    ```json
    {
      "code": 200,
      "message": "success",
      "data": {
        "success": true
      }
    }
    ```
  - 错误响应：
    ```json
    {
      "code": 404,
      "message": "会话不存在或无权限",
      "data": null
    }
    ```
- **状态码说明**：
  - 200：成功
  - 401：未授权
  - 404：会话不存在或无权限
- **权限要求**：需要登录，普通用户只能删除自己的会话
- **调用示例**：
  ```bash
  curl -X DELETE "http://localhost:8000/api/v1/sessions/1" \
  -H "Authorization: Bearer {token}"
  ```

#### 2.1.5 关联文件到会话

- **功能说明**：将文件关联到指定会话
- **请求方法**：POST
- **URL路径**：/sessions/{session_id}/files
- **请求参数**：
  | 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
  |--------|----------|----------|--------|------|
  | session_id | integer | 是 | 无 | 会话ID |
  | file_ids | array[integer] | 是 | 无 | 文件ID列表，至少一个 |
- **响应格式**：
  - 成功响应：
    ```json
    {
      "code": 200,
      "message": "success",
      "data": {
        "success": true,
        "count": 2
      }
    }
    ```
- **状态码说明**：
  - 200：成功
  - 401：未授权
- **权限要求**：需要登录，普通用户只能关联自己的或公共文件
- **调用示例**：
  ```bash
  curl -X POST "http://localhost:8000/api/v1/sessions/1/files" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"file_ids": [1, 2]}'
  ```

#### 2.1.6 取消文件与会话关联

- **功能说明**：取消文件与会话的关联
- **请求方法**：DELETE
- **URL路径**：/sessions/{session_id}/files
- **请求参数**：
  | 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
  |--------|----------|----------|--------|------|
  | session_id | integer | 是 | 无 | 会话ID |
  | file_ids | array[integer] | 是 | 无 | 文件ID列表，至少一个 |
- **响应格式**：
  - 成功响应：
    ```json
    {
      "code": 200,
      "message": "success",
      "data": {
        "success": true,
        "count": 1
      }
    }
    ```
- **状态码说明**：
  - 200：成功
  - 401：未授权
- **权限要求**：需要登录，普通用户只能操作自己的会话
- **调用示例**：
  ```bash
  curl -X DELETE "http://localhost:8000/api/v1/sessions/1/files" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"file_ids": [1]}'
  ```

### 2.2 消息管理接口 (chat_messages)

#### 2.2.1 发送消息

- **功能说明**：在指定会话中发送消息
- **请求方法**：POST
- **URL路径**：/sessions/{session_id}/messages
- **请求参数**：
  | 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
  |--------|----------|----------|--------|------|
  | session_id | integer | 是 | 无 | 会话ID |
  | content | string | 是 | 无 | 消息内容 |
  | role | string | 否 | user | 消息角色，如user、assistant |
  | model_name | string | 否 | null | 模型名称 |
- **响应格式**：
  - 成功响应：
    ```json
    {
      "code": 200,
      "message": "success",
      "data": {
        "id": 1,
        "session_id": 1,
        "user_id": 1,
        "content": "你好",
        "role": "user",
        "model_name": null,
        "created_at": "2024-01-01T00:00:00"
      }
    }
    ```
  - 错误响应：
    ```json
    {
      "code": 404,
      "message": "会话不存在或无权限",
      "data": null
    }
    ```
- **状态码说明**：
  - 200：成功
  - 401：未授权
  - 404：会话不存在或无权限
- **权限要求**：需要登录，普通用户只能在自己的会话中发送消息
- **调用示例**：
  ```bash
  curl -X POST "http://localhost:8000/api/v1/sessions/1/messages" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"content": "你好"}'
  ```

#### 2.2.2 获取消息历史

- **功能说明**：获取指定会话的消息历史记录
- **请求方法**：GET
- **URL路径**：/sessions/{session_id}/messages
- **请求参数**：
  | 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
  |--------|----------|----------|--------|------|
  | session_id | integer | 是 | 无 | 会话ID |
  | page | integer | 否 | 1 | 页码，从1开始 |
  | size | integer | 否 | 20 | 每页数量，1-200 |
- **响应格式**：
  - 成功响应：
    ```json
    {
      "code": 200,
      "message": "success",
      "data": {
        "items": [
          {
            "id": 1,
            "session_id": 1,
            "user_id": 1,
            "content": "你好",
            "role": "user",
            "model_name": null,
            "created_at": "2024-01-01T00:00:00"
          }
        ],
        "total": 1,
        "page": 1,
        "size": 20
      }
    }
    ```
- **状态码说明**：
  - 200：成功
  - 401：未授权
- **权限要求**：需要登录，普通用户只能查看自己的会话消息
- **调用示例**：
  ```bash
  curl -X GET "http://localhost:8000/api/v1/sessions/1/messages?page=1&size=20" \
  -H "Authorization: Bearer {token}"
  ```

### 2.3 文件管理接口 (files)

#### 2.3.1 分片上传

- **功能说明**：上传文件分片
- **请求方法**：POST
- **URL路径**：/files/upload/chunk
- **请求参数**：
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
- **响应格式**：
  - 成功响应：
    ```json
    {
      "code": 200,
      "message": "success",
      "data": {
        "file_md5": "abc123",
        "chunk_md5": "def456",
        "chunk_index": 0,
        "uploaded": true
      }
    }
    ```
  - 失败响应：
    ```json
    {
      "code": 200,
      "message": "success",
      "data": {
        "file_md5": "abc123",
        "chunk_md5": null,
        "chunk_index": 0,
        "uploaded": false,
        "error": "chunk upload failed after retries"
      }
    }
    ```
- **状态码说明**：
  - 200：成功
  - 401：未授权
- **权限要求**：需要登录
- **调用示例**：
  ```bash
  curl -X POST "http://localhost:8000/api/v1/files/upload/chunk" \
  -H "Authorization: Bearer {token}" \
  -F "file_md5=abc123" \
  -F "chunk_index=0" \
  -F "total_chunks=3" \
  -F "chunk_size=1048576" \
  -F "total_size=3145728" \
  -F "file_name=test.pdf" \
  -F "content_type=application/pdf" \
  -F "is_public=false" \
  -F "file_chunk=@chunk0.bin"
  ```

#### 2.3.2 检查上传完成状态

- **功能说明**：检查文件是否已经完成上传并合并
- **请求方法**：GET
- **URL路径**：/files/upload/is_complete/{file_id}
- **请求参数**：
  | 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
  |--------|----------|----------|--------|------|
  | file_id | integer | 是 | 无 | 文件ID |
- **响应格式**：
  - 成功响应：
    ```json
    {
      "code": 200,
      "message": "success",
      "data": {
        "id": 1,
        "user_id": 1,
        "filename": "test.pdf",
        "content_type": "application/pdf",
        "file_size": 3145728,
        "bucket_name": "final",
        "object_name": "abc123/test.pdf",
        "etag": "abc123",
        "is_public": false,
        "status": 1,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00"
      }
    }
    ```
- **状态码说明**：
  - 200：成功
  - 401：未授权
- **权限要求**：需要登录
- **调用示例**：
  ```bash
  curl -X GET "http://localhost:8000/api/v1/files/upload/is_complete/1" \
  -H "Authorization: Bearer {token}"
  ```

#### 2.3.3 查询文件列表

- **功能说明**：分页查询用户文件列表
- **请求方法**：GET
- **URL路径**：/files
- **请求参数**：
  | 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
  |--------|----------|----------|--------|------|
  | page | integer | 否 | 1 | 页码，从1开始 |
  | size | integer | 否 | 10 | 每页数量，1-100 |
  | include_public | boolean | 否 | true | 是否包含公共文件 |
- **响应格式**：
  - 成功响应：
    ```json
    {
      "code": 200,
      "message": "success",
      "data": {
        "items": [
          {
            "id": 1,
            "user_id": 1,
            "filename": "test.pdf",
            "content_type": "application/pdf",
            "file_size": 3145728,
            "bucket_name": "final",
            "object_name": "abc123/test.pdf",
            "etag": "abc123",
            "is_public": false,
            "status": 1,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
          }
        ],
        "total": 1,
        "page": 1,
        "size": 10
      }
    }
    ```
- **状态码说明**：
  - 200：成功
  - 401：未授权
- **权限要求**：需要登录
- **调用示例**：
  ```bash
  curl -X GET "http://localhost:8000/api/v1/files?page=1&size=10" \
  -H "Authorization: Bearer {token}"
  ```

#### 2.3.4 获取文件详情

- **功能说明**：获取文件详细信息
- **请求方法**：GET
- **URL路径**：/files/{file_id}
- **请求参数**：
  | 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
  |--------|----------|----------|--------|------|
  | file_id | integer | 是 | 无 | 文件ID |
- **响应格式**：
  - 成功响应：
    ```json
    {
      "code": 200,
      "message": "success",
      "data": {
        "id": 1,
        "user_id": 1,
        "filename": "test.pdf",
        "content_type": "application/pdf",
        "file_size": 3145728,
        "bucket_name": "final",
        "object_name": "abc123/test.pdf",
        "etag": "abc123",
        "is_public": false,
        "status": 1,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00"
      }
    }
    ```
  - 错误响应：
    ```json
    {
      "code": 404,
      "message": "文件不存在或无权限",
      "data": null
    }
    ```
- **状态码说明**：
  - 200：成功
  - 401：未授权
  - 404：文件不存在或无权限
- **权限要求**：需要登录，普通用户只能查看自己的或公共文件
- **调用示例**：
  ```bash
  curl -X GET "http://localhost:8000/api/v1/files/1" \
  -H "Authorization: Bearer {token}"
  ```

#### 2.3.5 查询公共文件列表

- **功能说明**：分页查询公共文件列表
- **请求方法**：GET
- **URL路径**：/files/public
- **请求参数**：
  | 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
  |--------|----------|----------|--------|------|
  | page | integer | 否 | 1 | 页码，从1开始 |
  | size | integer | 否 | 10 | 每页数量，1-100 |
- **响应格式**：
  - 成功响应：
    ```json
    {
      "code": 200,
      "message": "success",
      "data": {
        "items": [
          {
            "id": 2,
            "user_id": 1,
            "filename": "public.pdf",
            "content_type": "application/pdf",
            "file_size": 1024000,
            "bucket_name": "final",
            "object_name": "def789/public.pdf",
            "etag": "def789",
            "is_public": true,
            "status": 1,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
          }
        ],
        "total": 1,
        "page": 1,
        "size": 10
      }
    }
    ```
- **状态码说明**：
  - 200：成功
- **权限要求**：无需登录
- **调用示例**：
  ```bash
  curl -X GET "http://localhost:8000/api/v1/files/public?page=1&size=10"
  ```

#### 2.3.6 删除文件

- **功能说明**：删除指定文件
- **请求方法**：DELETE
- **URL路径**：/files/{file_id}
- **请求参数**：
  | 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
  |--------|----------|----------|--------|------|
  | file_id | integer | 是 | 无 | 文件ID |
- **响应格式**：
  - 成功响应：
    ```json
    {
      "code": 200,
      "message": "success",
      "data": {
        "success": true
      }
    }
    ```
  - 错误响应：
    ```json
    {
      "code": 404,
      "message": "文件不存在",
      "data": null
    }
    ```
- **状态码说明**：
  - 200：成功
  - 401：未授权
  - 404：文件不存在
  - 403：无权删除该文件
- **权限要求**：需要登录，普通用户只能删除自己的文件
- **调用示例**：
  ```bash
  curl -X DELETE "http://localhost:8000/api/v1/files/1" \
  -H "Authorization: Bearer {token}"
  ```

### 2.4 用户管理接口 (users)

#### 2.4.1 获取所有用户列表

- **功能说明**：获取所有用户列表（不分页）
- **请求方法**：GET
- **URL路径**：/users
- **请求参数**：无
- **响应格式**：
  - 成功响应：
    ```json
    {
      "code": 200,
      "message": "success",
      "data": [
        {
          "id": 1,
          "username": "admin",
          "name": "管理员",
          "gender": "male",
          "phone": "13800138000",
          "email": "admin@example.com",
          "avatar_file_id": null,
          "bio": "系统管理员",
          "role": "admin",
          "created_at": "2024-01-01T00:00:00",
          "updated_at": "2024-01-01T00:00:00"
        }
      ]
    }
    ```
- **状态码说明**：
  - 200：成功
- **权限要求**：无需登录
- **调用示例**：
  ```bash
  curl -X GET "http://localhost:8000/api/v1/users"
  ```

#### 2.4.2 分页查询用户列表

- **功能说明**：分页查询用户列表
- **请求方法**：GET
- **URL路径**：/users/page
- **请求参数**：
  | 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
  |--------|----------|----------|--------|------|
  | page | integer | 否 | 1 | 页码，从1开始 |
  | size | integer | 否 | 10 | 每页数量，1-100 |
  | keyword | string | 否 | null | 模糊搜索关键词 |
- **响应格式**：
  - 成功响应：
    ```json
    {
      "code": 200,
      "message": "success",
      "data": {
        "items": [
          {
            "id": 1,
            "username": "admin",
            "name": "管理员",
            "gender": "male",
            "phone": "13800138000",
            "email": "admin@example.com",
            "avatar_file_id": null,
            "bio": "系统管理员",
            "role": "admin",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
          }
        ],
        "total": 1,
        "page": 1,
        "size": 10
      }
    }
    ```
- **状态码说明**：
  - 200：成功
- **权限要求**：无需登录
- **调用示例**：
  ```bash
  curl -X GET "http://localhost:8000/api/v1/users/page?page=1&size=10&keyword=admin"
  ```

#### 2.4.3 获取用户详情

- **功能说明**：获取指定用户的详细信息
- **请求方法**：GET
- **URL路径**：/users/{user_id}
- **请求参数**：
  | 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
  |--------|----------|----------|--------|------|
  | user_id | integer | 是 | 无 | 用户ID |
- **响应格式**：
  - 成功响应：
    ```json
    {
      "code": 200,
      "message": "success",
      "data": {
        "id": 1,
        "username": "admin",
        "name": "管理员",
        "gender": "male",
        "phone": "13800138000",
        "email": "admin@example.com",
        "avatar_file_id": null,
        "bio": "系统管理员",
        "role": "admin",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00"
      }
    }
    ```
  - 错误响应：
    ```json
    {
      "code": 404,
      "message": "用户不存在",
      "data": null
    }
    ```
- **状态码说明**：
  - 200：成功
  - 404：用户不存在
- **权限要求**：无需登录
- **调用示例**：
  ```bash
  curl -X GET "http://localhost:8000/api/v1/users/1"
  ```

#### 2.4.4 创建用户

- **功能说明**：创建新用户
- **请求方法**：POST
- **URL路径**：/users
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
  - 成功响应：
    ```json
    {
      "code": 200,
      "message": "success",
      "data": {
        "id": 2,
        "username": "user1",
        "name": "用户1",
        "gender": "male",
        "phone": "13900139000",
        "email": "user1@example.com",
        "avatar_file_id": null,
        "bio": "普通用户",
        "role": "user",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00"
      }
    }
    ```
- **状态码说明**：
  - 200：成功
- **权限要求**：无需登录
- **调用示例**：
  ```bash
  curl -X POST "http://localhost:8000/api/v1/users" \
  -H "Content-Type: application/json" \
  -d '{"username": "user1", "password": "123456", "name": "用户1"}'
  ```

#### 2.4.5 更新用户

- **功能说明**：更新用户信息
- **请求方法**：PUT
- **URL路径**：/users/{user_id}
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
  - 成功响应：
    ```json
    {
      "code": 200,
      "message": "success",
      "data": {
        "id": 2,
        "username": "user1",
        "name": "用户1更新",
        "gender": "male",
        "phone": "13900139000",
        "email": "user1@example.com",
        "avatar_file_id": null,
        "bio": "普通用户",
        "role": "user",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00"
      }
    }
    ```
  - 错误响应：
    ```json
    {
      "code": 404,
      "message": "用户不存在",
      "data": null
    }
    ```
- **状态码说明**：
  - 200：成功
  - 404：用户不存在
- **权限要求**：无需登录
- **调用示例**：
  ```bash
  curl -X PUT "http://localhost:8000/api/v1/users/2" \
  -H "Content-Type: application/json" \
  -d '{"name": "用户1更新"}'
  ```

#### 2.4.6 删除用户

- **功能说明**：删除指定用户
- **请求方法**：DELETE
- **URL路径**：/users/{user_id}
- **请求参数**：
  | 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
  |--------|----------|----------|--------|------|
  | user_id | integer | 是 | 无 | 用户ID |
- **响应格式**：
  - 成功响应：
    ```json
    {
      "code": 200,
      "message": "success",
      "data": {
        "success": true
      }
    }
    ```
  - 错误响应：
    ```json
    {
      "code": 404,
      "message": "用户不存在",
      "data": null
    }
    ```
- **状态码说明**：
  - 200：成功
  - 404：用户不存在
- **权限要求**：无需登录
- **调用示例**：
  ```bash
  curl -X DELETE "http://localhost:8000/api/v1/users/2"
  ```

### 2.5 健康检查接口 (health)

#### 2.5.1 健康检查

- **功能说明**：检查服务是否正常运行
- **请求方法**：GET
- **URL路径**：/health
- **请求参数**：无
- **响应格式**：
  - 成功响应：
    ```json
    {
      "code": 200,
      "message": "success",
      "data": {
        "status": "ok"
      }
    }
    ```
- **状态码说明**：
  - 200：成功
- **权限要求**：无需登录
- **调用示例**：
  ```bash
  curl -X GET "http://localhost:8000/api/v1/health"
  ```

### 2.6 基础设施演示接口 (infra_demo)

#### 2.6.1 基础设施依赖注入演示

- **功能说明**：演示Redis、MinIO、RabbitMQ的依赖注入方式
- **请求方法**：GET
- **URL路径**：/infra/demo
- **请求参数**：无
- **响应格式**：
  - 成功响应：
    ```json
    {
      "code": 200,
      "message": "success",
      "data": {
        "redis": true,
        "minio_temp_bucket_exists": true,
        "rabbitmq_queue": "file_tasks"
      }
    }
    ```
- **状态码说明**：
  - 200：成功
- **权限要求**：无需登录
- **调用示例**：
  ```bash
  curl -X GET "http://localhost:8000/api/v1/infra/demo"
  ```

## 3. 响应格式统一说明

所有API接口返回的响应格式统一为：

```json
{
  "code": 200,        // 状态码
  "message": "success", // 响应消息
  "data": {}          // 响应数据
}
```

- **code**：HTTP状态码，200表示成功，其他表示错误
- **message**：响应消息，成功时为"success"，错误时为错误信息
- **data**：响应数据，根据接口不同返回不同的数据结构

## 4. 权限说明

- **无需登录**：标记为无需登录的接口可以直接访问
- **需要登录**：标记为需要登录的接口需要在请求头中携带有效的Authorization token
- **普通用户权限**：登录用户只能访问和操作自己的数据
- **管理员权限**：管理员可以访问和操作所有用户的数据

## 5. 接口版本管理

当前API版本为v1，所有接口路径前缀为`/api/v1/`。后续版本升级将通过修改路径前缀实现，如`/api/v2/`。

## 6. 注意事项

1. 所有需要登录的接口都需要在请求头中携带有效的Authorization token
2. 文件上传接口需要使用multipart/form-data格式提交
3. 分页查询接口的page参数从1开始
4. 所有时间字段返回格式为ISO 8601格式
5. 错误响应的code字段与HTTP状态码一致
