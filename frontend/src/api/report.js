import request from './request'

/** 举报接口 */
export function pageReports(params) {
  return request.get('/report/page', { params })
}

/** 举报一篇已发布稿件 */
export function createReport(articleId, reason) {
  return request.post('/report', null, { params: { articleId, reason } })
}

/** 处理举报：{ status: 1 成立 | 2 不成立, remark } */
export function handleReport(id, data) {
  return request.put(`/report/${id}/handle`, data)
}
