package com.zimeiti.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 稿件实体，对应 biz_article 表。
 * <p>这是整个系统的核心业务对象，也是智能体的审核对象。
 * <p>阶段 2 只用它做数据看板的统计（稿件总数、待审数量），
 * 完整的增删改查在阶段 3 实现。
 */
@Data
@TableName("biz_article")
public class BizArticle {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String title;

    /** 正文内容（智能体审核的就是这个字段） */
    private String content;

    private String summary;

    private String coverImage;

    private Long categoryId;

    /** 作者（创作者）用户 id */
    private Long authorId;

    /** 稿件状态：0 草稿，1 待审核，2 已发布，3 已驳回，4 已阻断，5 已下架 */
    private Integer status;

    /** 当前风险等级：-1 未判定，0 通过，1 疑似，2 违规，3 严重 */
    private Integer riskLevel;

    /** 驳回/阻断原因（含违规片段与修改建议，展示给创作者） */
    private String rejectReason;

    private LocalDateTime publishTime;

    private Integer viewCount;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;
}
