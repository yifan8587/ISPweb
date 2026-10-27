import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { useAuthStore } from '@/store/auth'
import { expireSession, isIdleExpired, shouldReportActivity } from '@/utils/idleSession'
import { applyUrlGuard } from '@/utils/urlguard'

const request = axios.create({
  baseURL: '/api',
  timeout: 20000,
})

// 请求拦截：附加 Bearer Token
function isIdleResponse(data) {
  if (!data) return false
  if (data.code === 'idle_timeout') return true
  const text = `${data.message || ''} ${typeof data.detail === 'string' ? data.detail : ''}`
  return text.includes('登录已超时')
}

request.interceptors.request.use(async (config) => {
  if (isIdleExpired()) {
    expireSession()
    return Promise.reject(new axios.Cancel('登录已超时'))
  }
  const auth = useAuthStore()
  if (auth.accessToken) {
    config.headers.Authorization = `Bearer ${auth.accessToken}`
  }
  if (shouldReportActivity()) {
    config.headers['X-User-Activity'] = '1'
  }
  await applyUrlGuard(config)
  return config
})

let refreshing = null

// 响应拦截：统一错误 + 401 自动刷新一次
request.interceptors.response.use(
  (resp) => resp.data,
  async (error) => {
    if (axios.isCancel(error)) return Promise.reject(error)
    const { response, config } = error
    const auth = useAuthStore()

    if (response && response.status === 401 && isIdleResponse(response.data)) {
      expireSession()
      return Promise.reject(error)
    }

    if (response && response.status === 401 && !config._retry && auth.refreshToken) {
      config._retry = true
      try {
        if (!refreshing) {
          const refreshConfig = await applyUrlGuard({
            method: 'post',
            baseURL: '',
            url: '/api/auth/token/refresh/',
            data: { refresh: auth.refreshToken },
            headers: {},
          })
          refreshing = axios.post(refreshConfig.url, refreshConfig.data, {
            headers: refreshConfig.headers,
            timeout: 20000,
          })
        }
        const r = await refreshing
        refreshing = null
        const newAccess = r.data?.access
        if (newAccess) {
          auth.setAccess(newAccess)
          config.headers.Authorization = `Bearer ${newAccess}`
          return request(config)
        }
      } catch (e) {
        refreshing = null
        if (isIdleResponse(e?.response?.data)) {
          expireSession()
          return Promise.reject(error)
        }
      }
      auth.logout()
      router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
      return Promise.reject(error)
    }

    const data = response?.data
    const timedOut = error.code === 'ECONNABORTED' || /timeout/i.test(error.message || '')
    const upstreamDown = response?.status === 502 || response?.status === 504
    const msg = data?.message || data?.detail || (timedOut ? '请求超时，请稍后重试' : upstreamDown ? '暂时无法连接管理端，请稍后重试' : error.message) || '请求失败'
    if (response?.status !== 401) {
      ElMessage.error(typeof msg === 'string' ? msg : '请求失败')
    }
    return Promise.reject(error)
  },
)

export default request
