import http from './http'
import type { ApiResponse } from './types'

export type ChatMessage = {
  id: number
  session_id: number
  user_id: number
  content: string
  role: string
  model_name: string | null
  created_at: string
}

export type MessageListResponse = {
  items: ChatMessage[]
  total: number
  page: number
  size: number
}

export type MessageCreatePayload = {
  content: string
  role?: string
  model_name?: string | null
}

export const sendMessage = async (sessionId: number, payload: MessageCreatePayload) => {
  const { data } = await http.post<ApiResponse<ChatMessage>>(
    `/sessions/${sessionId}/messages`,
    payload,
  )
  return data.data
}

export const listMessages = async (sessionId: number, page = 1, size = 20) => {
  const { data } = await http.get<ApiResponse<MessageListResponse>>(
    `/sessions/${sessionId}/messages`,
    { params: { page, size } },
  )
  return data.data
}
