package com.zimeiti.service;

import com.zimeiti.entity.AuditPlatform;

import java.util.List;

/**
 * 目标平台服务：维护平台清单与各平台的格式约束。
 * <p>这些数据在阶段 5/6 会被智能体用来做"按平台规则审核"和"跨平台适配"，
 * 所以平台标识（platformKey）是稳定契约的一部分，不要随意改。
 */
public interface PlatformService {

    List<AuditPlatform> list();

    void save(AuditPlatform platform);

    void update(AuditPlatform platform);

    void delete(Long id);
}
