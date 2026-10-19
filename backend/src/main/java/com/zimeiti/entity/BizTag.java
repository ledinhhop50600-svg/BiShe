package com.zimeiti.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 稿件标签，对应 biz_tag 表。
 * <p>一篇稿件可以打多个标签；投稿时从已有标签中选择，管理员可在分类与标签管理页维护。
 */
@Data
@TableName("biz_tag")
public class BizTag {

    @TableId(type = IdType.AUTO)
    private Long id;

    @NotBlank(message = "标签名不能为空")
    private String name;

    private LocalDateTime createTime;
}
