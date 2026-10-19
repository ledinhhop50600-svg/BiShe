import request from './request'

/**
 * 跨平台适配接口。
 * <p>超时单独放宽到 180 秒：一次最多 5 个平台、每个平台两次模型调用，
 * 用全局的 30 秒会误判为"网络异常"（后端其实还在生成）。
 */
export function adaptArticle(id, platformKeys) {
  return request.post(`/article/${id}/adapt`, { platformKeys }, { timeout: 180000 })
}

/** 某篇稿件的适配历史 */
export function listAdaptations(id) {
  return request.get(`/article/${id}/adaptations`)
}
