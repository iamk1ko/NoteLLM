import http from './http'
import type { ApiResponse } from './types'

export type FileStorage = {
  id: number
  user_id: number
  filename: string
  content_type: string
  file_size: number
  bucket_name: string
  object_name: string
  etag: string
  is_public: boolean
  status: number
  created_at: string
  updated_at: string
}

export type FileListResponse = {
  items: FileStorage[]
  total: number
  page: number
  size: number
}

export type UploadChunkPayload = {
  file_md5: string
  chunk_index: number
  total_chunks: number
  chunk_size: number
  total_size: number
  file_name: string
  content_type: string
  is_public: boolean
  file_chunk: File
}

export type UploadChunkResult = {
  file_md5: string
  chunk_md5: string | null
  chunk_index: number
  uploaded: boolean
  retry_count?: number
  error?: string
}

export const uploadChunk = async (payload: UploadChunkPayload) => {
  const formData = new FormData()
  formData.append('file_md5', payload.file_md5)
  formData.append('chunk_index', String(payload.chunk_index))
  formData.append('total_chunks', String(payload.total_chunks))
  formData.append('chunk_size', String(payload.chunk_size))
  formData.append('total_size', String(payload.total_size))
  formData.append('file_name', payload.file_name)
  formData.append('content_type', payload.content_type)
  formData.append('is_public', String(payload.is_public))
  formData.append('file_chunk', payload.file_chunk)

  const { data } = await http.post<ApiResponse<UploadChunkResult>>(
    '/files/upload/chunk',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    },
  )
  return data.data
}

export const getUploadComplete = async (fileId: number) => {
  const { data } = await http.get<ApiResponse<FileStorage>>(`/files/upload/is_complete/${fileId}`)
  return data.data
}

export const listFiles = async (page = 1, size = 10, includePublic = true) => {
  const { data } = await http.get<ApiResponse<FileListResponse>>('/files', {
    params: { page, size, include_public: includePublic },
  })
  return data.data
}

export const getFileDetail = async (fileId: number) => {
  const { data } = await http.get<ApiResponse<FileStorage>>(`/files/${fileId}`)
  return data.data
}

export const listPublicFiles = async (page = 1, size = 10) => {
  const { data } = await http.get<ApiResponse<FileListResponse>>('/files/public', {
    params: { page, size },
  })
  return data.data
}

export const deleteFile = async (fileId: number) => {
  const { data } = await http.delete<ApiResponse<{ success: boolean }>>(`/files/${fileId}`)
  return data.data
}
