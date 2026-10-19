package com.zimeiti.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

/**
 * 稿件-标签关联，对应 biz_article_tag 表（多对多）。
 */
@Data
@TableName("biz_article_tag")
public class BizArticleTag {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long articleId;

    private Long tagId;

    public BizArticleTag() {
    }

    public BizArticleTag(Long articleId, Long tagId) {
        this.articleId = articleId;
        this.tagId = tagId;
    }
}
