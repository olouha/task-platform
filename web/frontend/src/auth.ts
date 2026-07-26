/**
 * 登录态管理 - 对接后端API
 * 支持账号密码验证、会话管理、同一账号多人同时在线
 */

import axios from 'axios'

const AUTH_SESSION_KEY = 'taskplatform_session_id'
const AUTH_ACCOUNT_KEY = 'taskplatform_auth_account'
const REMEMBER_KEY = 'taskplatform_remember_account'
const AUTH_IS_ADMIN_KEY = 'taskplatform_is_admin'
const AUTH_POSITION_KEY = 'taskplatform_position'

const api = axios.create({
  baseURL: '/api/auth',
  timeout: 15000,
})

// 请求拦截器 - 添加调试日志
api.interceptors.request.use(
  (config) => {
    console.log(`[API Request] ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`)
    return config
  },
  (error) => {
    console.error('[API Request Error]', error)
    return Promise.reject(error)
  }
)

// 响应拦截器 - 添加调试日志
api.interceptors.response.use(
  (response) => {
    console.log(`[API Response] ${response.status} ${response.config.url}`)
    return response
  },
  (error) => {
    console.error('[API Response Error]', error.response?.status, error.response?.data)
    return Promise.reject(error)
  }
)

/** 登录 */
export async function login(account: string, password: string): Promise<{
  session_id: string
  account: string
  position: string
  permissions: string
  is_admin: boolean
  online_count: number
}> {
  const response = await api.post('/login', { account, password })
  const data = response.data

  // 保存会话ID和账号
  localStorage.setItem(AUTH_SESSION_KEY, data.session_id)
  localStorage.setItem(AUTH_ACCOUNT_KEY, data.account)
  // 保存登录时判定的管理员标记与职位（getUserInfo 失败时的降级值）
  localStorage.setItem(AUTH_IS_ADMIN_KEY, String(!!data.is_admin))
  localStorage.setItem(AUTH_POSITION_KEY, data.position || '')

  return data
}

/** 登出 */
export async function logout(): Promise<void> {
  const session_id = localStorage.getItem(AUTH_SESSION_KEY)
  if (session_id) {
    try {
      await api.post('/logout', {}, {
        headers: { 'X-Session-ID': session_id }
      })
    } catch (e) {
      // 忽略错误
    }
  }
  localStorage.removeItem(AUTH_SESSION_KEY)
  localStorage.removeItem(AUTH_ACCOUNT_KEY)
  localStorage.removeItem(AUTH_IS_ADMIN_KEY)
  localStorage.removeItem(AUTH_POSITION_KEY)
}

/** 是否已登录 */
export function isAuthenticated(): boolean {
  return !!localStorage.getItem(AUTH_SESSION_KEY)
}

/** 获取当前登录账号 */
export function getAccount(): string | null {
  return localStorage.getItem(AUTH_ACCOUNT_KEY)
}

/** 获取登录时记录的是否管理员（getUserInfo 失败时的降级值） */
export function getStoredIsAdmin(): boolean {
  return localStorage.getItem(AUTH_IS_ADMIN_KEY) === 'true'
}

/** 获取登录时记录的职位 */
export function getStoredPosition(): string {
  return localStorage.getItem(AUTH_POSITION_KEY) || ''
}

/** 获取当前会话ID */
export function getSessionId(): string | null {
  return localStorage.getItem(AUTH_SESSION_KEY)
}

/** 获取用户信息 */
export async function getUserInfo(): Promise<{
  account: string
  position: string
  permissions: string
  is_admin: boolean
  online_count: number
}> {
  const session_id = localStorage.getItem(AUTH_SESSION_KEY)
  if (!session_id) {
    throw new Error('未登录')
  }

  const response = await api.get('/user-info', {
    headers: { 'X-Session-ID': session_id }
  })
  return response.data
}

/** 修改密码 */
export async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
  const session_id = localStorage.getItem(AUTH_SESSION_KEY)
  if (!session_id) {
    throw new Error('未登录')
  }

  await api.post('/change-password', {
    old_password: oldPassword,
    new_password: newPassword
  }, {
    headers: { 'X-Session-ID': session_id }
  })
}

/** 记住账号 */
export function saveRememberedAccount(account: string): void {
  localStorage.setItem(REMEMBER_KEY, account)
}

/** 清除记住的账号 */
export function clearRememberedAccount(): void {
  localStorage.removeItem(REMEMBER_KEY)
}

/** 获取记住的账号 */
export function getRememberedAccount(): string {
  return localStorage.getItem(REMEMBER_KEY) || ''
}

/** API请求封装 - 自动携带会话ID */
export async function apiRequest<T>(
  method: 'get' | 'post' | 'put' | 'delete',
  url: string,
  data?: any
): Promise<T> {
  const session_id = localStorage.getItem(AUTH_SESSION_KEY)

  const response = await api({
    method,
    url,
    data,
    headers: session_id ? { 'X-Session-ID': session_id } : {}
  })
  return response.data
}

/** 获取所有用户（含密码，仅管理员） */
export async function getAllUsersWithPassword(): Promise<Array<{
  account: string
  password: string
  position: string
  permissions: string
}>> {
  const session_id = localStorage.getItem(AUTH_SESSION_KEY)
  if (!session_id) throw new Error('未登录')

  const response = await api.get('/users-with-password', {
    headers: { 'X-Session-ID': session_id }
  })
  return response.data
}

/** 新增用户 */
export async function addUser(account: string, password: string, position: string, permissions: string): Promise<void> {
  const session_id = localStorage.getItem(AUTH_SESSION_KEY)
  if (!session_id) throw new Error('未登录')

  await api.post('/users', {
    account, password, position, permissions
  }, {
    headers: { 'X-Session-ID': session_id }
  })
}

/** 管理员修改用户密码 */
export async function adminChangePassword(targetAccount: string, newPassword: string): Promise<void> {
  const session_id = localStorage.getItem(AUTH_SESSION_KEY)
  if (!session_id) throw new Error('未登录')

  await api.put(`/users/${targetAccount}/password`, newPassword, {
    headers: { 'X-Session-ID': session_id }
  })
}

/** 删除用户 */
export async function deleteUser(targetAccount: string): Promise<void> {
  const session_id = localStorage.getItem(AUTH_SESSION_KEY)
  if (!session_id) throw new Error('未登录')

  await api.delete(`/users/${targetAccount}`, {
    headers: { 'X-Session-ID': session_id }
  })
}
