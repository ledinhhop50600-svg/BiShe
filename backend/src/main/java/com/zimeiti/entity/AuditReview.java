package com.zimeiti.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 审核复核/改判记录，对应 audit_review 表。
 * <p>action 的取值定义（与前端展示、统计口径保持一致）：
 * <ul>
 *   <li>1 采纳：审核员的最终结论与智能体建议一致</li>
 *   <li>2 改判：结论与智能体建议不一致（必须填原因）</li>
 *   <li>3 人工判定：没有可用的智能体初判（未运行 / 失败 / 内容已修改）</li>
 * </ul>
 * <p>「疑似（1）」视为智能体把决定权交给人工：人工通过或驳回都不算改判，
 * 否则改判率会被"疑似转人工"的正常流程虚高。
 */
@Data
@TableName("audit_review")
public class AuditReview {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long auditRecordId;

    private Long articleId;

    private Long reviewerId;

    private Integer action;

    /** 最终风险等级：0 通过，2 驳回，3 阻断（1 仅用于疑似，人工可落到 0/2/3） */
    private Integer finalLevel;

    private String remark;

    private LocalDateTime createTime;
}
