package com.zimeiti.vo;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * 审核员的处理记录（给创作者看反馈、给工作台判断是否已处理）。
 */
@Data
public class AuditReviewVO {

    private Long id;

    private Long auditRecordId;

    private Integer action;

    private String actionText;

    private Integer finalLevel;

    private String finalLevelText;

    private String remark;

    private String reviewerName;

    private LocalDateTime createTime;
}
