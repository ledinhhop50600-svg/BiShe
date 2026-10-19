package com.zimeiti.vo;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 智能体审核记录返回对象。
 * <p>工作台的"智能体判定"面板与审核记录页共用；`review*` 字段只有已处理的记录才有。
 */
@Data
public class AuditRecordVO {

    private Long id;

    private Long articleId;

    private String articleTitle;

    private String authorName;

    private Integer triggerType;

    private String triggerText;

    private Integer riskLevel;

    private String riskLevelText;

    private String reason;

    private String hitRuleCodes;

    private List<ViolationVO> violations;

    private String suggestion;

    private String modelName;

    private Integer promptTokens;

    private Integer completionTokens;

    private Integer durationMs;

    private LocalDateTime createTime;

    /**
     * 记录是否早于稿件最后一次修改。
     * <p>为 true 时说明稿件在初审后被改过（例如驳回后重提），这条结论已经不对应当前内容，
     * 不能用于"采纳/改判"，需要重新运行初审。
     */
    private Boolean stale;

    private LocalDateTime articleUpdateTime;

    // ---- 审核员的处理（已处理时才有）----
    private Integer reviewAction;

    private String reviewActionText;

    private Integer finalLevel;

    private String finalLevelText;

    private String reviewRemark;

    private String reviewerName;

    private LocalDateTime reviewTime;
}
