package com.zimeiti.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.util.List;

/**
 * 稿件新增/修改的请求参数。
 * <p>注意这里**没有 status 字段**：稿件的状态不由前端直接设置，而是通过"提交、撤回、审核"等
 * 动作接口流转 —— 否则前端可以绕过流程把稿件直接设成"已发布"。这是状态机设计的基本要求。
 */
@Data
public class ArticleSaveDTO {

    private Long id;

    @NotBlank(message = "标题不能为空")
    @Size(max = 200, message = "标题最长 200 个字符")
    private String title;

    @NotBlank(message = "正文不能为空")
    private String content;

    @Size(max = 500, message = "摘要最长 500 个字符")
    private String summary;

    private String coverImage;

    private Long categoryId;

    /** 标签 id 列表 */
    private List<Long> tagIds;
}
