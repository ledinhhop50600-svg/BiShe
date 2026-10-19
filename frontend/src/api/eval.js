import request from './request'

/** 评测中心接口（管理员） */
export function getEvalResults() {
  return request.get('/eval/results')
}

/**
 * 运行演示评测。
 * <p>首次约 2-3 分钟（12 个适配 × 两次模型调用）；之后固定 run-id 会复用回放缓存，通常几十秒。
 * 结果写入 docs/eval/demo，不覆盖论文数据。超时放宽到 15 分钟。
 */
export function runAdaptationEval() {
  return request.post('/eval/run-adaptation', null, { timeout: 900000 })
}
