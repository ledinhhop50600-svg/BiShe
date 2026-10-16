import request from './request'

/** 数据看板接口 */
export function getDashboardStats() {
  return request.get('/dashboard/stats')
}
