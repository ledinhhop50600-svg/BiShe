import request from './request'

/** 角色管理接口 */
export function pageRoles(params) {
  return request.get('/role/page', { params })
}

/** 全部启用角色（用户管理的角色下拉框用） */
export function listRoles() {
  return request.get('/role/list')
}

/** 某角色已勾选的菜单 id */
export function getRoleMenuIds(id) {
  return request.get(`/role/${id}/menuIds`)
}

export function createRole(data) {
  return request.post('/role', data)
}

export function updateRole(data) {
  return request.put('/role', data)
}

export function deleteRole(id) {
  return request.delete(`/role/${id}`)
}
