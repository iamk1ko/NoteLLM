import http from './http'
import type { ApiResponse } from './types'

export type ChatSession = {
  id: number
  title: string
  biz_type: string
  context_id: number | null
  user_id: number
  status: number
  created_at: string
  updated_at: string
}

export type ChatSessionWithFiles = ChatSession & {
  files: number[]
}

export type SessionListResponse = {
  items: ChatSession[]
  total: number
  page: number
  size: number
}

export type SessionCreatePayload = {
  title: string
  biz_type: string
  context_id?: number | null
}

export const createSession = async (payload: SessionCreatePayload) => {
  const { data } = await http.post<ApiResponse<ChatSession>>('/sessions', payload)
  return data.data
}

export const listSessions = async (page = 1, size = 10, bizType?: string) => {
  const { data } = await http.get<ApiResponse<SessionListResponse>>('/sessions', {
    params: { page, size, biz_type: bizType },
  })
  return data.data
}

export const getSessionDetail = async (sessionId: number) => {
  const { data } = await http.get<ApiResponse<ChatSessionWithFiles>>(`/sessions/${sessionId}`)
  return data.data
}

export const attachFiles = async (sessionId: number, fileIds: number[]) => {
  const { data } = await http.post<ApiResponse<{ success: boolean; count: number }>>(
    `/sessions/${sessionId}/files`,
    { file_ids: fileIds },
  )
  return data.data
}

export const detachFiles = async (sessionId: number, fileIds: number[]) => {
  const { data } = await http.delete<ApiResponse<{ success: boolean; count: number }>>(
    `/sessions/${sessionId}/files`,
    { data: { file_ids: fileIds } },
  )
  return data.data
}
