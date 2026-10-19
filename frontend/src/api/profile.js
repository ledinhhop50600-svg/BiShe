import request from './request'

/** 个人中心接口（只操作当前登录用户自己的数据） */
export function getProfile() {
  return request.get('/profile')
}

export function updateProfile(data) {
  return request.put('/profile', data)
}

export function changePassword(data) {
  return request.put('/profile/password', data)
}
