package com.zimeiti.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * 稿件审核的请求参数。
 * <p>action 取值：
 *  - approve 通过（稿件变为已发布）
 *  - reject  驳回（稿件变为已驳回，必须填写原因，创作者据此修改后重提）
 *  - block   阻断（严重违规，稿件变为已阻断）
 * <p>阶段 3 的审核由人工完成；阶段 7 会在这里加上智能体的分级初判与改判记录。
 */
@Data
public class ArticleReviewDTO {

    @NotBlank(message = "请选择审核动作")
    private String action;

    /** 审核意见 / 驳回原因（驳回与阻断时必填），会直接展示给创作者 */
    private String reason;
}
