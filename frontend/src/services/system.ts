import http from './http'
import type { ApiResponse } from './types'

export const checkHealth = async () => {
  const { data } = await http.get<ApiResponse<{ status: string }>>('/health')
  return data.data
}

export const getInfraDemo = async () => {
  const { data } = await http.get<
    ApiResponse<{
      redis: boolean
      minio_temp_bucket_exists: boolean
      rabbitmq_queue: string
    }>
  >('/infra/demo')
  return data.data
}
