// frontend/src/services/types.ts

// 1. Common API Response Wrapper
export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
  timestamp: string;
}

// 2. Pagination Wrapper
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

// 3. File Models
export interface FileItem {
  id: number;
  user_id: number;
  filename: string;
  file_size: number;
  content_type: string;
  bucket_name: string;
  object_name: string;
  etag: string;
  is_public: boolean;
  status: number; // 1: normal? need to clarify status codes
  created_at: string;
  updated_at: string;
}

// For frontend compatibility (if we need to map to old structure, or update frontend to use new structure)
// Let's stick to the API structure for now and update components.

// 4. Session Models
export interface SessionItem {
  id: number;
  title: string | null;
  biz_type: string;
  context_id: string | null;
  user_id: number;
  status: number;
  create_time: string;
  update_time: string;
  files?: number[]; // IDs of associated files
}

export interface CreateSessionParams {
  title?: string;
  biz_type?: string;
  context_id?: string;
  status?: number;
}

// 5. Message Models
export interface MessageItem {
  id: number;
  session_id: number;
  user_id: number;
  role: string; // "user" | "assistant"
  content: string;
  model_name: string | null;
  token_count: number | null;
  create_time: string;
  sources?: Array<{ // This is not in the API doc for messages, but implied by RAG. 
    // Checking doc again: 2.2.1 response doesn't show sources. 
    // Wait, usually RAG returns sources. 
    // If the API doc doesn't show sources in message response, maybe they are appended to content or returned in a separate field not documented?
    // For now, I'll add it as optional, but I should probably ask or check if it's in `content`.
    // The current frontend expects `sources`.
    title?: string; 
    snippet: string; 
    score: number; 
  }>; 
}

// 6. User Models
export interface Quota {
  total_bytes: number;
  used_bytes: number;
  file_count: number;
}

export interface User {
  id: number;
  username: string;
  name: string;
  email: string | null;
  role: string;
  gender: string | null;
  phone: string | null;
  avatar_file_id: number | null;
  bio: string | null;
  created_at?: string;
  quota?: Quota;
}

// Deprecated: UserItem (keeping for backward compatibility if needed, but User is preferred)
export type UserItem = User;

// 7. Upload Progress (Frontend only)
export interface UploadProgress {
  loaded: number;
  total?: number;
  percent: number;
}

// 8. Chunk Upload Response
export interface ChunkUploadResponse {
  file_md5: string;
  chunk_md5: string;
  chunk_index: number;
  uploaded: boolean;
  file_id?: number; // Optional, might be returned in some implementations or inferred
}

