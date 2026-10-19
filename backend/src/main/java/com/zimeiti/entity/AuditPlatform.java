package com.zimeiti.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 目标平台与格式约束，对应 audit_platform 表。
 * <p>这是"跨平台内容适配"和"按平台规则审核"的依据：每个平台有自己的标题/正文字数上限、
 * 话题标签规则与内容风格要求。
 * <p>重要说明：约束数值应以各平台公开的创作规范为准。种子数据里的是常用参考值，
 * 在阶段 5/6 正式做适配前需要逐个核对并更新 —— 不能自己编数字。
 */
@Data
@TableName("audit_platform")
public class AuditPlatform {

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 平台标识（英文，程序用）：wechat / xiaohongshu / weibo / bilibili / douyin */
    @NotBlank(message = "平台标识不能为空")
    private String platformKey;

    /** 平台名称（显示用） */
    @NotBlank(message = "平台名称不能为空")
    private String platformName;

    /** 标题字数上限 */
    private Integer titleMaxLen;

    /** 正文字数上限 */
    private Integer contentMaxLen;

    /** 话题标签规则描述 */
    private String tagRule;

    /** 内容风格要求 */
    private String styleDesc;

    private Integer sort;

    /** 状态：1 启用，0 停用 */
    private Integer status;

    private LocalDateTime createTime;
}
