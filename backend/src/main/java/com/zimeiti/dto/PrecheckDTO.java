package com.zimeiti.dto;

import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 发布前预检请求：只传标题与正文，不需要稿件已保存。
 * <p>预检结论不落库，仅用于给创作者修改建议。
 */
@Data
public class PrecheckDTO {

    @Size(max = 200, message = "标题最长 200 个字符")
    private String title;

    @Size(max = 50000, message = "正文过长")
    private String content;
}
