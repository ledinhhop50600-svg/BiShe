import axios from 'axios'
import { ElMessage } from 'element-plus'

/**
 * 统一的 HTTP 请求实例。
 * <p>作用有两个，都由拦截器实现：
 *  1. 请求拦截器：自动把登录令牌放进请求头，页面里不用每次都手动带；
 *  2. 响应拦截器：把后端统一的 Result 结构拆开，业务代码直接拿到 data，
 *     并统一处理"登录失效（401）"与"业务失败"两种情况。
 */
const request = axios.create({
  // 前端所有请求都以 /api 开头，由 Vite 代理转发到后端，浏览器看来始终是同源请求
  baseURL: '/api',
  timeout: 30000,
})

const TOKEN_KEY = 'zimeiti_token'
const TOKEN_NAME_KEY = 'zimeiti_token_name'

/** 保存登录令牌到本地，刷新页面后仍然保持登录状态 */
export function saveToken(tokenName, tokenValue) {
  localStorage.setItem(TOKEN_NAME_KEY, tokenName)
  localStorage.setItem(TOKEN_KEY, tokenValue)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(TOKEN_NAME_KEY)
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

// 请求拦截器：带上令牌
request.interceptors.request.use((config) => {
  const token = getToken()
  const tokenName = localStorage.getItem(TOKEN_NAME_KEY) || 'satoken'
  if (token) {
    config.headers[tokenName] = token
  }
  return config
})

// 响应拦截器：拆包 + 统一错误处理
request.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code === 200) {
      // 业务成功：只把 data 交给调用方，页面里不用再写 res.data.data
      return res.data
    }
    if (res.code === 401) {
      // 登录状态失效：清掉本地令牌并回到登录页
      clearToken()
      ElMessage.error(res.msg || '登录状态已失效，请重新登录')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
      return Promise.reject(new Error(res.msg || '未登录'))
    }
    ElMessage.error(res.msg || '请求失败')
    return Promise.reject(new Error(res.msg || '请求失败'))
  },
  (error) => {
    ElMessage.error('网络异常：' + (error.message || '请求失败'))
    return Promise.reject(error)
  }
)

export default request
