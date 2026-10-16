import request from './request'

/** 菜单管理接口 */
export function getMenuTree() {
  return request.get('/menu/tree')
}

export function createMenu(data) {
  return request.post('/menu', data)
}

export function updateMenu(data) {
  return request.put('/menu', data)
}

export function deleteMenu(id) {
  return request.delete(`/menu/${id}`)
}
