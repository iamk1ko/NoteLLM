import http from "@/services/http";
import type { ApiResponse, PaginatedResponse, SessionItem, MessageItem, CreateSessionParams } from "@/services/types";

// QA Service matching API Documentation 2.1 & 2.2

// --- Sessions ---

/**
 * Create Chat Session
 * POST /sessions
 */
export const createSession = async (params: CreateSessionParams): Promise<SessionItem> => {
  const { data } = await http.post<ApiResponse<SessionItem>>("/sessions", params);
  return data.data;
};

/**
 * Get Session List
 * GET /sessions
 */
export const fetchSessions = async (params: { page?: number; size?: number; biz_type?: string } = {}): Promise<PaginatedResponse<SessionItem>> => {
  const { data } = await http.get<ApiResponse<PaginatedResponse<SessionItem>>>("/sessions", { params });
  return data.data;
};

/**
 * Get Session Detail
 * GET /sessions/{id}
 */
export const fetchSessionDetail = async (id: number | string): Promise<SessionItem> => {
  const { data } = await http.get<ApiResponse<SessionItem>>(`/sessions/${id}`);
  return data.data;
};

/**
 * Delete Session
 * DELETE /sessions/{id}
 */
export const deleteSession = async (id: number | string): Promise<void> => {
  await http.delete(`/sessions/${id}`);
};

/**
 * Associate Files to Session
 * POST /sessions/{id}/files
 */
export const addFilesToSession = async (sessionId: number | string, fileIds: number[]): Promise<void> => {
  await http.post(`/sessions/${sessionId}/files`, { file_ids: fileIds });
};

// --- Messages ---

/**
 * Send Message
 * POST /sessions/{id}/messages
 */
export const sendMessage = async (sessionId: number | string, content: string): Promise<MessageItem> => {
  const { data } = await http.post<ApiResponse<MessageItem>>(`/sessions/${sessionId}/messages`, {
    session_id: sessionId, // redundant in body based on path? API doc says body has session_id too.
    content,
    role: "user" 
  });
  return data.data;
};

/**
 * Get Message History
 * GET /sessions/{id}/messages
 */
export const fetchMessages = async (sessionId: number | string, params: { page?: number; size?: number } = {}): Promise<PaginatedResponse<MessageItem>> => {
  const { data } = await http.get<ApiResponse<PaginatedResponse<MessageItem>>>(`/sessions/${sessionId}/messages`, { params });
  return data.data;
};
