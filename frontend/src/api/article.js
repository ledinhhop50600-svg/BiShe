import request from './request'

/** 稿件接口 */
export function pageArticles(params) {
  return request.get('/article/page', { params })
}

export function getMyArticles(params) {
  return request.get('/article/my', { params })
}

/** 内容广场：他人已发布的稿件 */
export function plazaArticles(params) {
  return request.get('/article/plaza', { params })
}

export function getArticle(id) {
  return request.get(`/article/${id}`)
}

export function createArticle(data) {
  return request.post('/article', data)
}

export function updateArticle(data) {
  return request.put('/article', data)
}

export function deleteArticle(id) {
  return request.delete(`/article/${id}`)
}

/** 提交发布申请 */
export function submitArticle(id) {
  return request.post(`/article/${id}/submit`)
}

/** 撤回申请 */
export function withdrawArticle(id) {
  return request.post(`/article/${id}/withdraw`)
}

/** 审核：{ action: 'approve' | 'reject' | 'block', reason } */
export function reviewArticle(id, data) {
  return request.put(`/article/${id}/review`, data)
}

/** 下架已发布稿件 */
export function offlineArticle(id) {
  return request.put(`/article/${id}/offline`)
}
