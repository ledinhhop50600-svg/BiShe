/**
 * 稿件状态与风险等级的显示字典。
 * <p>多个页面都要显示"状态"和"风险等级"。如果每个页面各写一份映射，
 * 一旦调整措辞就会不一致 —— 所以集中在这里维护，只改一处。
 */
export const ARTICLE_STATUS = {
  0: { text: '草稿', type: 'info' },
  1: { text: '待审核', type: 'warning' },
  2: { text: '已发布', type: 'success' },
  3: { text: '已驳回', type: 'danger' },
  4: { text: '已阻断', type: 'danger' },
  5: { text: '已下架', type: 'info' },
}

export const RISK_LEVEL = {
  '-1': { text: '未判定', type: 'info' },
  0: { text: '通过', type: 'success' },
  1: { text: '疑似', type: 'warning' },
  2: { text: '违规', type: 'danger' },
  3: { text: '严重', type: 'danger' },
}

export function statusText(status) {
  return ARTICLE_STATUS[status]?.text || '未知'
}

export function statusType(status) {
  return ARTICLE_STATUS[status]?.type || 'info'
}

export function riskText(level) {
  return RISK_LEVEL[level]?.text || '未判定'
}

export function riskType(level) {
  return RISK_LEVEL[level]?.type || 'info'
}
