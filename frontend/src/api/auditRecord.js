import request from './request'

/** 审核记录接口（审核记录页 / 看板统计） */
export function pageAuditRecords(params) {
  return request.get('/audit-record/page', { params })
}

export function getAuditStats() {
  return request.get('/audit-record/stats')
}
