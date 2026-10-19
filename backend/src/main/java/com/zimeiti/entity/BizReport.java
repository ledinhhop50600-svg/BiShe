package com.zimeiti.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 举报记录，对应 biz_report 表。
 * <p>创作者可举报已发布的稿件；审核员处理后，举报成立则稿件下架。
 */
@Data
@TableName("biz_report")
public class BizReport {

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 被举报的稿件 id */
    private Long articleId;

    /** 举报人用户 id */
    private Long reporterId;

    /** 举报理由 */
    private String reason;

    /** 处理状态：0 待处理，1 举报成立，2 举报不成立 */
    private Integer status;

    /** 处理人（审核员）用户 id */
    private Long handlerId;

    private String handleRemark;

    private LocalDateTime handleTime;

    private LocalDateTime createTime;
}
