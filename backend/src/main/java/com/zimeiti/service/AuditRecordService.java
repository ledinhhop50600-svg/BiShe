package com.zimeiti.service;

import com.zimeiti.common.PageResult;
import com.zimeiti.entity.AuditRecord;
import com.zimeiti.vo.AuditRecordVO;

import java.util.Map;

/**
 * 智能体审核记录的持久化、查询与统计。
 */
public interface AuditRecordService {

    /**
     * 保存一次智能体判定。
     * <p>失败也要保存（riskLevel=-1，modelName=agent-failed）：审核员需要看到"这次没判成"，
     * 统计可用率与失败率也需要它。
     *
     * @return 新记录 id
     */
    Long saveAgentResult(Long articleId, String triggerType, Long platformId,
                         String contentHash, Map<String, Object> result, boolean failed, String error);

    /** 工作台/创作者反馈：最新一条智能体记录 + 对应的人工处理 */
    Map<String, Object> feedback(Long articleId);

    /** 审核记录分页（审核记录页） */
    PageResult<AuditRecordVO> page(long pageNum, long pageSize,
                                   Integer triggerType, Integer riskLevel, Boolean onlyOverride);

    /** 智能体审核统计（看板）：判定分布、失败数、改判率 */
    Map<String, Object> stats();

    /** 某篇稿件的最新一条记录（审核落库时用） */
    AuditRecord latest(Long articleId);
}
