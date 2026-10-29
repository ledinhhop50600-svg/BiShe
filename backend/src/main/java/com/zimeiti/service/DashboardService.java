package com.zimeiti.service;

import java.util.Map;

/**
 * 数据看板：按角色返回可视化所需的聚合数据。
 */
public interface DashboardService {

    /** 看板总览：卡片、趋势、分布、最近动态 */
    Map<String, Object> overview();
}
