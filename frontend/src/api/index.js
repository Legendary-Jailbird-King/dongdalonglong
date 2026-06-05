import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import router from '../router'

// ── 创建 Axios 实例 ──────────────────────────────────────
const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

// ── 请求拦截器：自动附带 JWT Token ─────────────────────
api.interceptors.request.use(
  (config) => {
    const auth = useAuthStore()
    if (auth.token) {
      config.headers.Authorization = `Bearer ${auth.token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// ── 响应拦截器：统一错误处理 + 401 自动跳转登录 ───────
api.interceptors.response.use(
  (response) => {
    const data = response.data
    if (data.code && data.code !== 200) {
      ElMessage.error(data.message || '请求失败')
      return Promise.reject(new Error(data.message))
    }
    return data
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      if (status === 401) {
        const auth = useAuthStore()
        auth.logout()
        router.push('/')
        ElMessage.error('登录已过期，请重新登录')
      } else if (status === 403) {
        ElMessage.error(data.detail || '权限不足')
      } else {
        ElMessage.error(data.detail || '服务器错误')
      }
    } else {
      ElMessage.error('网络连接失败')
    }
    return Promise.reject(error)
  }
)

export default api
