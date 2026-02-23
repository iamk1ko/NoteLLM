import axios from "axios";

/**
 * 全局 HTTP 请求实例 (Global Axios Instance)
 * 统一处理请求头、BaseURL 和 响应拦截
 */
const http = axios.create({
  // 从环境变量读取API地址 (VITE_API_BASE_URL)
  baseURL: import.meta.env.VITE_API_BASE_URL,
  // 默认超时时间 20秒
  timeout: 20000
});

/**
 * 响应拦截器 (Response Interceptor)
 * 处理统一错误，或提取 data 层级
 */
http.interceptors.response.use(
  (response) => {
    // 成功响应直接返回
    return response;
  },
  (error) => {
    // 处理网络错误或业务异常
    console.error("API Error:", error);
    // TODO: 可以集成 ElementPlus 的 ElMessage.error() 进行全局提示
    return Promise.reject(error);
  }
);

export default http;
