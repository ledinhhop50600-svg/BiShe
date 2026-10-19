import request from './request'

/**
 * 认证相关接口。
 * <p>这一层只负责"调哪个地址、传什么参数"，不掺业务逻辑 ——
 * 业务逻辑都在 Pinia store 里，页面只跟 store 打交道。
 */

/** 登录：返回 { tokenName, tokenValue, userInfo } */
export function login(data) {
  return request.post('/auth/login', data)
}

/** 获取注册验证码：返回 { captchaId, question } */
export function getCaptcha() {
  return request.get('/auth/captcha')
}

/** 自主注册：成功后直接返回登录态（固定创作者角色） */
export function register(data) {
  return request.post('/auth/register', data)
}

/** 登出：让当前令牌失效 */
export function logout() {
  return request.post('/auth/logout')
}

/** 获取当前登录用户信息（角色、权限、菜单） */
export function getCurrentUser() {
  return request.get('/auth/me')
}
