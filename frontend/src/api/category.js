import request from './request'

/** 分类接口 */
export function listCategories() {
  return request.get('/category/list')
}

export function createCategory(data) {
  return request.post('/category', data)
}

export function updateCategory(data) {
  return request.put('/category', data)
}

export function deleteCategory(id) {
  return request.delete(`/category/${id}`)
}

/** 标签接口 */
export function listTags() {
  return request.get('/tag/list')
}

export function createTag(data) {
  return request.post('/tag', data)
}

export function updateTag(data) {
  return request.put('/tag', data)
}

export function deleteTag(id) {
  return request.delete(`/tag/${id}`)
}
