package com.zimeiti.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 智能体审核记录，对应 audit_record 表。
 * <p>每次判定留一条（不覆盖）：初判、重新初审、失败记录都在这里，
 * 它既是审核工作台的依据，也是论文里成本、耗时、改判率的数据来源。
 */
@Data
@TableName("audit_record")
public class AuditRecord {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long articleId;

    /** 触发场景：1 发布前预检，2 发布审核，3 举报复审，4 适配预检 */
    private Integer triggerType;

    private Long platformId;

    /** 0 通过 / 1 疑似 / 2 违规 / 3 严重；-1 表示智能体未成功判定 */
    private Integer riskLevel;

    private String reason;

    /** 命中规则编号，逗号分隔，如 AD-003,FB-011 */
    private String hitRuleCodes;

    /** 违规片段的 JSON 数组字符串（fragment / issue / suggestion） */
    private String violationFragments;

    /** 判定时稿件标题+正文的 SHA-256；内容改过则本记录视为过期 */
    private String contentHash;

    private String suggestion;

    private String modelName;

    private Integer promptTokens;

    private Integer completionTokens;

    private Integer durationMs;

    private LocalDateTime createTime;
}
