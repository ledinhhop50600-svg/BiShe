import request from './request'

/** 审核规则库（只读） */
export function listRules() {
  return request.get('/rule/list')
}

/** 规则管理（管理员）：含停用规则 */
export function listAllRules() {
  return request.get('/rule/all')
}

export function createRule(data) {
  return request.post('/rule', data)
}

export function updateRule(data) {
  return request.put('/rule', data)
}

export function deleteRule(id) {
  return request.delete(`/rule/${id}`)
}
