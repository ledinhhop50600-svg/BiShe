import request from './request'

/** 数据看板接口 */
export function getDashboardStats() {
  return request.get('/dashboard/stats')
}

/** 可视化看板：卡片、趋势、分布、最近动态 */
export function getDashboardOverview() {
  return request.get('/dashboard/overview')
}
