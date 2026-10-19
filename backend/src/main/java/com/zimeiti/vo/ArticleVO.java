package com.zimeiti.vo;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 稿件返回对象。
 * <p>比实体多带了几个"显示用"的字段：分类名、作者名、标签 —— 前端表格直接显示，
 * 不用再发一堆请求去翻译 id。
 */
@Data
public class ArticleVO {

    private Long id;

    private String title;

    private String content;

    private String summary;

    private String coverImage;

    private Long categoryId;

    /** 分类名称（显示用） */
    private String categoryName;

    private Long authorId;

    /** 作者昵称（显示用） */
    private String authorName;

    /** 稿件状态：0 草稿，1 待审核，2 已发布，3 已驳回，4 已阻断，5 已下架 */
    private Integer status;

    /** 当前风险等级：-1 未判定，0 通过，1 疑似，2 违规，3 严重 */
    private Integer riskLevel;

    /** 驳回/阻断原因 */
    private String rejectReason;

    private LocalDateTime publishTime;

    private Integer viewCount;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;

    /** 标签 id 列表（编辑时回填） */
    private List<Long> tagIds;

    /** 标签名称列表（显示用） */
    private List<String> tagNames;
}
