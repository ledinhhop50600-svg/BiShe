import request from './request'

/** 目标平台接口 */
export function listPlatforms() {
  return request.get('/platform/list')
}

export function createPlatform(data) {
  return request.post('/platform', data)
}

export function updatePlatform(data) {
  return request.put('/platform', data)
}

export function deletePlatform(id) {
  return request.delete(`/platform/${id}`)
}
