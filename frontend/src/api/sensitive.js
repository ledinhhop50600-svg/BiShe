import request from './request'

/** 敏感词接口 */
export function pageWords(params) {
  return request.get('/sensitive/page', { params })
}

export function createWord(data) {
  return request.post('/sensitive', data)
}

export function updateWord(data) {
  return request.put('/sensitive', data)
}

export function deleteWord(id) {
  return request.delete(`/sensitive/${id}`)
}

/** 文本检测（敏感词基线），返回命中词与最高等级 */
export function checkText(text) {
  return request.post('/sensitive/check', { text })
}
