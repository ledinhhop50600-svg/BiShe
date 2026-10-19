package com.zimeiti.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 跨平台适配记录，对应 audit_adaptation 表。
 * <p>每生成一次适配就落一行（同一稿件、同一平台按 version 递增），
 * 这样创作者能回看"上次给小红书生成的是什么版本"，答辩时也能证明记录留存不是摆设。
 */
@Data
@TableName("audit_adaptation")
public class AuditAdaptation {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long articleId;

    private Long platformId;

    private String adaptedTitle;

    private String adaptedContent;

    /** 话题标签，空格分隔（标签本身不含空格，格式自检会拦下含空格的标签） */
    private String adaptedTags;

    /** 格式自检结果（人可读的一行摘要） */
    private String formatCheck;

    /** 该平台的合规预检结论（人可读的一行摘要） */
    private String complianceCheck;

    /** 同一稿件的第几次适配（同一平台每生成一次 +1） */
    private Integer version;

    private Long adaptedBy;

    private LocalDateTime createTime;
}
