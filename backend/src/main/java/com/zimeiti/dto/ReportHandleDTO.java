package com.zimeiti.dto;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 举报处理的请求参数。
 * <p>status：1 举报成立（稿件下架），2 举报不成立。
 */
@Data
public class ReportHandleDTO {

    @NotNull(message = "请选择处理结果")
    private Integer status;

    @Size(max = 500, message = "处理意见最长 500 个字符")
    private String remark;
}
