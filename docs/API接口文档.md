# API接口文档

[TOC]

## 1. 文档概述

本文档详细描述了 **NoteLLM** 后端项目的所有API接口设计，包括接口功能、请求方法、参数说明、响应格式、权限要求等信息。文档基于实际代码实现，旨在为前端开发人员和其他相关人员提供清晰的接口使用指南。

## 2. 接口分类

### 2.1 会话管理接口 (chat_sessions)

#### 2.1.1 创建会话

- **功能说明**：创建新的聊天会话
- **请求方法**：POST
- **URL路径**：/sessions
- **请求参数**：
  
  | 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
  |--------|----------|----------|--------|------|
  | title | string | 否 | null | 会话标题 |
  | biz_type | string | 否 | "ai_chat" | 业务类型，如'ai_chat' |
  | context_id | string | 否 | null | 外部上下文ID，如PDF文档ID |
  | status | integer | 否 | 1 | 会话状态：1-正常，0-删除 |

- **响应格式**：
  
  - 成功响应：
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
        "files": [1, 2, 3]
      },
      "timestamp": "2024-01-01T00:00:00"
    }
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
      "code": 0,
      "message": "OK",
      "data": {
        "success": true
      },
      "timestamp": "2024-01-01T00:00:00"
    }
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
      "code": 0,
      "message": "OK",
      "data": {
        "success": true,
        "count": 2
      },
      "timestamp": "2024-01-01T00:00:00"
    }
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
      "code": 0,
      "message": "OK",
      "data": {
        "success": true,
        "count": 1
      },
      "timestamp": "2024-01-01T00:00:00"
    }
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
  | role | string | 否 | "user" | 消息角色，如user、assistant |
  | model_name | string | 否 | null | 模型名称 |

- **响应格式**：
  - 成功响应：
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

#### 2.2.2 查询消息历史

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

### 2.3 文件管理接口 (files)

#### 2.3.1 简单单文件上传

- **功能说明**：上传单个文件（适合前端直接上传）
- **请求方法**：POST
- **URL路径**：/files
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
          "created_at": "2024-01-01T00:00:00",
          "updated_at": "2024-01-01T00:00:00"
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

#### 2.3.2 分片上传

- **功能说明**：上传文件分片
- **请求方法**：POST
- **URL路径**：/files/upload/chunk
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
        "uploaded": true
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

#### 2.3.3 检查文件是否已存在

- **功能说明**：检查当前用户是否已上传同 MD5 文件
- **请求方法**：GET
- **URL路径**：/files/check
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

#### 2.3.4 检查上传完成状态

- **功能说明**：检查文件是否已经完成上传并合并
- **请求方法**：GET
- **URL路径**：/files/upload/is_complete/{file_id}
- **请求参数**：
  | 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
  |--------|----------|----------|--------|------|
  | file_id | integer | 是 | 无 | 文件ID |

- **响应格式**：
  - 成功响应（返回文件信息）：
    ```json
    {
      "code": 0,
      "message": "OK",
      "data": {
        "id": 1,
        "filename": "test.pdf",
        ...
      },
      "timestamp": "2024-01-01T00:00:00"
    }
    ```

#### 2.3.5 查询文件列表

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
      "code": 0,
      "message": "OK",
      "data": {
        "items": [
          {
            "id": 1,
            "filename": "test.pdf",
            ...
          }
        ],
        "total": 1,
        "page": 1,
        "size": 10
      },
      "timestamp": "2024-01-01T00:00:00"
    }
    ```

#### 2.3.6 获取文件详情

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
      "code": 0,
      "message": "OK",
      "data": {
        "id": 1,
        "filename": "test.pdf",
        ...
      },
      "timestamp": "2024-01-01T00:00:00"
    }
    ```

#### 2.3.7 获取文件预览地址

- **功能说明**：获取文件的临时预览链接（MinIO Presigned URL）
- **请求方法**：GET
- **URL路径**：/files/{file_id}/preview
- **请求参数**：
  | 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
  |--------|----------|----------|--------|------|
  | file_id | integer | 是 | 无 | 文件ID |

- **响应格式**：
  - 成功响应：
    ```json
    {
      "code": 0,
      "message": "OK",
      "data": {
        "url": "http://minio:9000/bucket/file.pdf?..."
      },
      "timestamp": "2024-01-01T00:00:00"
    }
    ```

#### 2.3.8 查询公共文件列表

- **功能说明**：分页查询公共文件列表
- **请求方法**：GET
- **URL路径**：/files/public
- **请求参数**：
  | 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
  |--------|----------|----------|--------|------|
  | page | integer | 否 | 1 | 页码，从1开始 |
  | size | integer | 否 | 10 | 每页数量，1-100 |

#### 2.3.8 删除文件

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
      "code": 0,
      "message": "OK",
      "data": {
        "success": true
      },
      "timestamp": "2024-01-01T00:00:00"
    }
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
      "code": 0,
      "message": "OK",
      "data": [
        {
          "id": 1,
          "username": "admin",
          "name": "管理员",
          "email": "admin@example.com",
          "role": "admin",
          ...
        }
      ],
      "timestamp": "2024-01-01T00:00:00"
    }
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
      "code": 0,
      "message": "OK",
      "data": {
        "items": [...],
        "total": 1,
        "page": 1,
        "size": 10
      },
      "timestamp": "2024-01-01T00:00:00"
    }
    ```

#### 2.4.3 获取用户详情

- **功能说明**：获取指定用户的详细信息
- **请求方法**：GET
- **URL路径**：/users/{user_id}
- **请求参数**：
  | 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
  |--------|----------|----------|--------|------|
  | user_id | integer | 是 | 无 | 用户ID |

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

#### 2.4.6 删除用户

- **功能说明**：删除指定用户
- **请求方法**：DELETE
- **URL路径**：/users/{user_id}
- **请求参数**：
  | 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
  |--------|----------|----------|--------|------|
  | user_id | integer | 是 | 无 | 用户ID |

#### 2.4.7 获取当前登录用户信息

- **功能说明**：获取当前登录用户的详细信息
- **请求方法**：GET
- **URL路径**：/users/me
- **请求参数**：无

- **响应格式**：
  - 成功响应：
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
        "email": "admin@example.com",
        "create_time": "2024-01-01T00:00:00",
        "update_time": "2024-01-01T00:00:00",
        "quota": {
           "total_bytes": 1073741824, // 1GB
           "used_bytes": 52428800,    // 50MB
           "file_count": 12
        }
      },
      "timestamp": "2024-01-01T00:00:00"
    }
    ```

### 2.5 认证接口 (auth)

#### 2.5.1 用户注册

- **功能说明**：注册新用户（本地学习阶段，密码明文存储）
- **请求方法**：POST
- **URL路径**：/auth/register
- **请求参数**：
  | 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
  |--------|----------|----------|--------|------|
  | username | string | 是 | 无 | 用户名 |
  | password | string | 是 | 无 | 密码 |
  | name | string | 是 | 无 | 姓名 |
  | email | string | 否 | null | 邮箱 |

- **响应格式**：
  - 成功响应：
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
        "email": "admin@example.com",
        "create_time": "2024-01-01T00:00:00",
        "update_time": "2024-01-01T00:00:00"
      },
      "timestamp": "2024-01-01T00:00:00"
    }
    ```

#### 2.5.4 说明

- 登录态使用 Cookie 的 session_id 维护，不返回 Token
- session_id 有效期由后端配置（本地学习阶段默认 7 天）

#### 2.5.2 用户登录

- **功能说明**：用户登录（用户名或邮箱）
- **请求方法**：POST
- **URL路径**：/auth/login
- **请求参数**：
  | 参数名 | 数据类型 | 是否必填 | 默认值 | 说明 |
  |--------|----------|----------|--------|------|
  | username_or_email | string | 是 | 无 | 用户名或邮箱 |
  | password | string | 是 | 无 | 密码 |

- **响应格式**：
  - 成功响应：
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
        "email": "admin@example.com",
        "create_time": "2024-01-01T00:00:00",
        "update_time": "2024-01-01T00:00:00"
      },
      "timestamp": "2024-01-01T00:00:00"
    }
    ```

#### 2.5.3 用户退出登录

- **功能说明**：退出登录并清理会话
- **请求方法**：POST
- **URL路径**：/auth/logout
- **请求参数**：无

- **响应格式**：
  - 成功响应：
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

## 3. 响应格式统一说明

所有API接口返回的响应格式统一为：

```json
{
  "code": 0,          // 业务状态码，0 表示成功
  "message": "OK",    // 提示信息
  "data": {},         // 响应数据
  "timestamp": "..."  // 响应时间 (ISO 8601)
}
```

## 4. 权限说明

- **无需登录**：标记为无需登录的接口可以直接访问
- **需要登录**：标记为需要登录的接口需要在请求头中携带有效的Authorization token
- **普通用户权限**：登录用户只能访问和操作自己的数据
- **管理员权限**：管理员可以访问和操作所有用户的数据

## 4.1 认证说明

- 登录成功后服务端下发 Cookie：`session_id`
- 前端后续请求需自动携带该 Cookie
- 退出登录将清理 Cookie 与服务端会话

## 5. 接口版本管理

当前API版本为v1，所有接口路径前缀为`/api/v1/`。

## 6. 注意事项

1. 所有需要登录的接口都需要在请求头中携带有效的Authorization token
2. 文件上传接口需要使用multipart/form-data格式提交
3. 分页查询接口的page参数从1开始
4. 所有时间字段返回格式为ISO 8601格式
5. 错误响应的code字段与HTTP状态码一致，或为特定业务错误码
6. 基础设施客户端（Redis/MinIO/RabbitMQ/Milvus）统一在应用启动时初始化，并通过依赖注入获取实例

## 7. 待实现功能接口 (To Be Implemented)

### 7.1 社区分享接口 (community) `[待实现]`

#### 7.1.1 发布分享 (Publish Share)
- **功能说明**：将个人会话及关联文档发布到社区广场
- **请求方法**：POST
- **URL路径**：/community/shares
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
    "data": {
      "share_id": 101,
      "publish_time": "..."
    }
  }
  ```

#### 7.1.2 获取社区列表 (Get Community Feed)
- **功能说明**：分页获取社区分享列表
- **请求方法**：GET
- **URL路径**：/community/shares
- **请求参数**：
  | 参数名 | 数据类型 | 是否必填 | 说明 |
  |--------|----------|----------|------|
  | page | integer | 否 | 页码，默认1 |
  | size | integer | 否 | 每页数量，默认10 |
  | sort | string | 否 | 排序方式: "latest"(最新), "popular"(最热) |
  | tag | string | 否 | 按标签筛选 |

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
          "description": "整理了常见面试题...",
          "tags": ["Python", "面试"],
          "user_id": 1,
          "user_name": "TechGuru",
          "view_count": 1240,
          "like_count": 45,
          "fork_count": 12,
          "create_time": "2024-02-20T10:00:00",
          "is_liked": false  // 当前用户是否已点赞
        }
      ],
      "total": 1,
      "page": 1,
      "size": 10
    }
  }
  ```

#### 7.1.3 转存/Fork 分享 (Fork Share)
- **功能说明**：将他人的分享内容（文档副本+会话副本）保存到自己的空间
- **请求方法**：POST
- **URL路径**：/community/shares/{share_id}/fork
- **请求参数**：无
- **响应格式**：
  ```json
  {
    "code": 0,
    "data": {
      "new_file_id": 205,    // 转存后的新文件ID
      "new_session_id": 302  // 转存后的新会话ID
    }
  }
  ```

#### 7.1.4 社区点赞 (Like Share)
- **功能说明**：对某个分享进行点赞或取消点赞
- **请求方法**：POST
- **URL路径**：/community/shares/{share_id}/like
- **请求参数**：
  | 参数名 | 数据类型 | 是否必填 | 说明 |
  |--------|----------|----------|------|
  | action | string | 是 | "like" 或 "unlike" |

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "success": true,
      "like_count": 46  // 返回最新的点赞数
    }
  }
  ```

### 7.2 智能笔记接口 (notes) `[待实现]`

#### 7.2.1 生成结构化笔记 (Auto Summary)
- **功能说明**：触发AI根据当前会话的历史记录，生成一份结构化的Markdown总结笔记
- **请求方法**：POST
- **URL路径**：/sessions/{session_id}/summary
- **请求参数**：
  | 参数名 | 数据类型 | 是否必填 | 说明 |
  |--------|----------|----------|------|
  | focus_topics | array[string] | 否 | 指定总结的关注点/主题 |

- **响应格式**：
  ```json
  {
    "code": 0,
    "data": {
      "summary_content": "# 笔记总结\n\n## 核心结论...", // Markdown内容
      "created_at": "..."
    }
  }
  ```

### 7.3 其他扩展 (extensions) `[待实现]`

#### 7.3.1 更新文件标签 (Update File Tags)
- **功能说明**：为现有文件添加或修改标签
- **请求方法**：PUT
- **URL路径**：/files/{file_id}/tags
- **请求参数**：
  | 参数名 | 数据类型 | 是否必填 | 说明 |
  |--------|----------|----------|------|
  | tags | array[string] | 是 | 标签列表 |

- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": {
      "id": 101,
      "tags": ["Python", "面试"]
    }
  }
  ```
