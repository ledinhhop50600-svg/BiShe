package com.zimeiti.vo;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * 举报返回对象：带上稿件标题与举报人/处理人昵称，便于列表直接展示。
 */
@Data
public class ReportVO {

    private Long id;

    private Long articleId;

    private String articleTitle;

    private Long reporterId;

    private String reporterName;

    private String reason;

    /** 0 待处理，1 成立，2 不成立 */
    private Integer status;

    private Long handlerId;

    private String handlerName;

    private String handleRemark;

    private LocalDateTime handleTime;

    private LocalDateTime createTime;
}
