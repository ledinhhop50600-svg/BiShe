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

/**
 * 发布前预检（智能体）：只传标题/正文，不需要已保存，不落库。
 * <p>后端审核客户端 30 秒、失败重试一次，这里放宽到 90 秒。
 */
export function precheckArticle(title, content) {
  return request.post('/article/precheck', { title, content }, { timeout: 90000 })
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

/**
 * 运行智能体审核。
 * <p>单独放宽超时：后端审核客户端是 30 秒、失败还会重试一次，用全局的 30 秒
 * 会在后端仍在判定时先报"网络异常"。
 * <p>triggerType：POST_AUDIT（正式审核，会落库）或 PRE_CHECK（预检，不落库）。
 */
export function agentAudit(id, triggerType = 'POST_AUDIT') {
  return request.post(`/article/${id}/agent-audit`, null, {
    params: { triggerType },
    timeout: 90000,
  })
}

/** 审核反馈：最新智能体初判 + 审核员处理意见 */
export function getAuditFeedback(id) {
  return request.get(`/article/${id}/audit-feedback`)
}
