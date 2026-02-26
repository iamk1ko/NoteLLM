# Services 开发规范

本文档定义了 `frontend/src/services/` 目录下 API 服务模块的开发规范，旨在保持代码风格一致性和可维护性。

## 1. 文件命名规范

- 使用小写字母 + 驼峰命名法 (camelCase)
- 名称应清晰表达业务功能
- 示例：`auth.ts`, `files.ts`, `qa.ts`, `community.ts`

## 2. 代码结构规范

### 2.1 导入顺序

按以下顺序组织导入：

1. **第三方库** (如 axios, vue-router)
2. **内部模块** (如 `@/services/http`, `@/services/types`)
3. **类型定义** (从 `@/services/types` 导入)

```typescript
// 1. 第三方库
import axios from "axios";

// 2. 内部模块
import http from "@/services/http";
import type { ApiResponse, User } from "@/services/types";
```

### 2.2 类型定义

- **必须**将所有类型定义放在 `src/services/types.ts` 中
- **避免**在单个 service 文件中定义接口/类型
- 如果是当前 service 专用的参数类型，可以在文件顶部定义，但建议复用 types.ts 中的类型

```typescript
// Good: 使用 types.ts 中已定义的类型
import type { ApiResponse, User } from "@/services/types";

export const getUser = async (): Promise<User> => {
  const { data } = await http.get<ApiResponse<User>>("/users/me");
  return data.data;
};

// Good: 在文件顶部定义专用参数类型
export interface LoginParams {
  username_or_email: string;
  password: string;
}

export const login = async (params: LoginParams): Promise<User> => {
  // ...
};
```

### 2.3 导出函数命名

- 使用**动词 + 名词**或**动词**命名
- 使用小驼峰 (camelCase)
- 必须包含 JSDoc 注释，说明接口路径和功能

```typescript
/**
 * Get user information
 * GET /users/me
 */
export const getCurrentUser = async (): Promise<User> => {
  const { data } = await http.get<ApiResponse<User>>("/users/me");
  return data.data;
};
```

## 3. API 请求规范

### 3.1 使用统一的 HTTP 实例

**必须**使用 `http` 实例 (`@/services/http`) 发起请求，**禁止**直接使用 axios 或 fetch（流式请求除外）。

```typescript
// Good
import http from "@/services/http";

export const fetchUsers = async () => {
  const { data } = await http.get("/users");
  return data;
};

// Exception: SSE 流式请求需要使用 fetch
export const streamChat = async (onChunk: (text: string) => void) => {
  const response = await fetch("/api/stream");
  // ...
};
```

### 3.2 响应类型定义

**必须**为每个 API 函数定义明确的返回类型，使用 `ApiResponse<T>` 包装。

```typescript
// Good: 明确指定返回类型
export const getUser = async (): Promise<User> => {
  const { data } = await http.get<ApiResponse<User>>("/users/me");
  return data.data;
};

// Good: 分页响应
export const fetchUsers = async (params: { page: number; size: number }) => {
  const { data } = await http.get<ApiResponse<PaginatedResponse<User>>>("/users", { params });
  return data.data;
};
```

### 3.3 请求参数类型

- 使用接口定义请求参数
- 参数使用小驼峰命名

```typescript
// Good
export interface FetchFilesParams {
  page?: number;
  size?: number;
  keyword?: string;
}

export const fetchFiles = async (params: FetchFilesParams = {}) => {
  // ...
};
```

## 4. 流式请求 (SSE) 规范

如果需要使用 Server-Sent Events (SSE) 进行流式响应：

### 4.1 必须包含认证凭证

**必须**设置 `credentials: 'include'`，以确保 Cookie 被发送到后端进行身份验证。

```typescript
export const streamChat = async (sessionId: string, content: string) => {
  const baseURL = import.meta.env.VITE_API_BASE_URL;
  
  const response = await fetch(`${baseURL}/sessions/${sessionId}/messages/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    // 必须包含凭证
    credentials: "include",
    body: JSON.stringify({ session_id: sessionId, content }),
  });

  // 处理响应...
};
```

### 4.2 错误处理

流式请求需要处理非 200 状态码的错误。

```typescript
if (!response.ok) {
  const errorText = await response.text();
  throw new Error(`HTTP ${response.status}: ${errorText}`);
}
```

## 5. 代码风格

### 5.1 缩进与空格

- 使用 2 空格缩进
- 在操作符前后加空格：`const a = b + c`
- 在对象字面量的冒号后加空格：`{ key: value }`

### 5.2 引号

- JSON 数据和字符串优先使用双引号 `"string"`
- TypeScript 类型定义使用单引号 `'type'`

### 5.3 分号

- **必须**使用分号结束语句
- 接口定义和方法签名除外

### 5.4 注释

- 使用 JSDoc 注释描述每个导出的函数
- 内部注释应简洁明了

```typescript
/**
 * User login
 * POST /auth/login
 * 
 * @param params - Login credentials
 * @returns User object
 */
export const login = async (params: LoginParams): Promise<User> => {
  // ...
};
```

## 6. 禁止事项

1. **禁止**在 service 文件中直接操作 DOM 或使用 DOM API
2. **禁止**在 service 文件中直接使用 `localStorage` 或 `sessionStorage`（认证逻辑应由 store 处理）
3. **禁止**硬编码 API Base URL，应使用环境变量 `import.meta.env.VITE_API_BASE_URL`
4. **禁止**忽略 Promise 返回类型推断（除非明确返回 `any`）

## 7. 示例

完整的 Service 文件示例：

```typescript
import http from "@/services/http";
import type { ApiResponse, User, PaginatedResponse } from "@/services/types";

/**
 * User Service
 * Handles user authentication and profile management
 */

// --- Types ---

export interface LoginParams {
  username_or_email: string;
  password: string;
}

// --- Auth ---

/**
 * User login
 * POST /auth/login
 */
export const login = async (params: LoginParams): Promise<User> => {
  const { data } = await http.post<ApiResponse<User>>("/auth/login", params);
  return data.data;
};

/**
 * User logout
 * POST /auth/logout
 */
export const logout = async (): Promise<void> => {
  await http.post("/auth/logout");
};

/**
 * Get current user info
 * GET /users/me
 */
export const getCurrentUser = async (): Promise<User> => {
  const { data } = await http.get<ApiResponse<User>>("/users/me");
  return data.data;
};

// --- Profile ---

export interface UpdateProfileParams {
  name?: string;
  email?: string;
  bio?: string;
}

/**
 * Update user profile
 * PUT /users/{id}
 */
export const updateProfile = async (id: number, params: UpdateProfileParams): Promise<User> => {
  const { data } = await http.put<ApiResponse<User>>(`/users/${id}`, params);
  return data.data;
};
```

## 8. 附录：环境变量

项目使用以下环境变量：

| 变量名 | 说明 | 示例 |
|--------|------|------|
| VITE_API_BASE_URL | API 基础地址 | http://localhost:8000/api/v1 |

访问方式：`import.meta.env.VITE_API_BASE_URL`
