import request from './request'

/** 用户管理接口 */
export function pageUsers(params) {
  return request.get('/user/page', { params })
}

export function getUser(id) {
  return request.get(`/user/${id}`)
}

export function createUser(data) {
  return request.post('/user', data)
}

export function updateUser(data) {
  return request.put('/user', data)
}

export function updateUserStatus(id, status) {
  return request.put(`/user/${id}/status`, null, { params: { status } })
}

export function resetUserPassword(id, password) {
  return request.put(`/user/${id}/password`, null, { params: { password } })
}

export function deleteUser(id) {
  return request.delete(`/user/${id}`)
}
