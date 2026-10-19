package com.zimeiti.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 稿件分类，对应 biz_category 表。
 * <p>分类由管理员维护（分类与标签管理页），创作者投稿时从中选择。
 */
@Data
@TableName("biz_category")
public class BizCategory {

    @TableId(type = IdType.AUTO)
    private Long id;

    @NotBlank(message = "分类名称不能为空")
    private String name;

    @NotNull(message = "请填写排序号")
    private Integer sort;

    /** 状态：1 启用，0 停用 */
    private Integer status;

    private LocalDateTime createTime;
}
