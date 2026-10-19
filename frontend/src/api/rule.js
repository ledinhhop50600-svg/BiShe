import request from './request'

/** 审核规则库（只读） */
export function listRules() {
  return request.get('/rule/list')
}
