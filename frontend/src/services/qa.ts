import http from "@/services/http";
import type { ApiResponse, PaginatedResponse, SessionItem, MessageItem, CreateSessionParams } from "@/services/types";

/**
 * QA Service
 * Handles chat sessions and messages
 */

// --- Session Operations ---

/**
 * Create a new chat session
 * POST /sessions
 */
export const createSession = async (params: CreateSessionParams): Promise<SessionItem> => {
  const { data } = await http.post<ApiResponse<SessionItem>>("/sessions", params);
  return data.data;
};

/**
 * Get session list (paginated)
 * GET /sessions
 */
export const fetchSessions = async (params: {
  page?: number;
  size?: number;
  biz_type?: string;
} = {}): Promise<PaginatedResponse<SessionItem>> => {
  const { data } = await http.get<ApiResponse<PaginatedResponse<SessionItem>>>("/sessions", { params });
  return data.data;
};

/**
 * Get session detail by ID
 * GET /sessions/{id}
 */
export const fetchSessionDetail = async (id: number | string): Promise<SessionItem> => {
  const { data } = await http.get<ApiResponse<SessionItem>>(`/sessions/${id}`);
  return data.data;
};

/**
 * Delete a session
 * DELETE /sessions/{id}
 */
export const deleteSession = async (id: number | string): Promise<void> => {
  await http.delete(`/sessions/${id}`);
};

/**
 * Associate files to a session
 * POST /sessions/{id}/files
 */
export const addFilesToSession = async (sessionId: number | string, fileIds: number[]): Promise<void> => {
  await http.post(`/sessions/${sessionId}/files`, { file_ids: fileIds });
};

// --- Message Operations ---

/**
 * Send a message (non-streaming)
 * POST /sessions/{id}/messages
 */
export const sendMessage = async (sessionId: number | string, content: string): Promise<MessageItem> => {
  const { data } = await http.post<ApiResponse<MessageItem>>(`/sessions/${sessionId}/messages`, {
    session_id: sessionId,
    content,
    role: "user"
  });
  return data.data;
};

/**
 * Send a message with streaming response (SSE)
 * POST /sessions/{id}/messages/stream
 * 
 * @param sessionId - Session ID
 * @param content - Message content
 * @param onChunk - Callback for each chunk of AI response
 * @param onDone - Callback when stream is done
 * @param onError - Callback on error
 */
export const sendMessageStream = async (
  sessionId: number | string,
  content: string,
  onChunk?: (content: string) => void,
  onDone?: () => void,
  onError?: (error: string) => void
): Promise<void> => {
  const baseURL = import.meta.env.VITE_API_BASE_URL || "";
  const url = `${baseURL}/sessions/${sessionId}/messages/stream`;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      // IMPORTANT: Include credentials (cookies) for authentication
      credentials: "include",
      body: JSON.stringify({
        session_id: sessionId,
        content,
        role: "user",
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error("Response body is null");
    }

    const decoder = new TextDecoder("utf-8");

    // eslint-disable-next-line no-constant-condition
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        break;
      }

      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split("\n");

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6);

          try {
            const parsed = JSON.parse(data);

            if (parsed.error) {
              onError?.(parsed.error);
              return;
            }

            if (parsed.done) {
              onDone?.();
              return;
            }

            if (parsed.content) {
              onChunk?.(parsed.content);
            }
          } catch {
            // Ignore parse errors for incomplete JSON
          }
        }
      }
    }

    onDone?.();
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    onError?.(errorMessage);
    throw error;
  }
};

/**
 * Get message history for a session
 * GET /sessions/{id}/messages
 */
export const fetchMessages = async (
  sessionId: number | string,
  params: { page?: number; size?: number } = {}
): Promise<PaginatedResponse<MessageItem>> => {
  const { data } = await http.get<ApiResponse<PaginatedResponse<MessageItem>>>(
    `/sessions/${sessionId}/messages`,
    { params }
  );
  return data.data;
};
