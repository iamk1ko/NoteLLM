import axios from 'axios'

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string) || ''
const apiToken = import.meta.env.VITE_API_TOKEN as string | undefined

const http = axios.create({
  baseURL: apiBaseUrl,
  timeout: 30000,
})

http.interceptors.request.use((config) => {
  if (apiToken) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = apiToken
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(error),
)

export default http
