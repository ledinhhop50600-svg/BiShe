package com.zimeiti.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 敏感词，对应 audit_sensitive_word 表。
 * <p>这是**传统关键词匹配方案**的数据来源 —— 它在系统里的两个用途：
 *  1. 给创作者和审核员一个"最低成本的初筛"（命中词直接标出来）；
 *  2. 作为论文对比实验的**基线方案**（关键词规则 vs 纯大模型 vs RAG+大模型）。
 * <p>注意：关键词匹配无法理解语境，例如作品名《最好的我们》会被误判 ——
 * 这正是引入智能体的动机，也是对比实验要展示的差距。
 */
@Data
@TableName("audit_sensitive_word")
public class AuditSensitiveWord {

    @TableId(type = IdType.AUTO)
    private Long id;

    @NotBlank(message = "敏感词不能为空")
    @Size(max = 100, message = "敏感词最长 100 个字符")
    private String word;

    /** 所属类别：与审核规则的类别保持一致，便于对比 */
    @NotBlank(message = "请选择类别")
    @Size(max = 30, message = "类别最长 30 个字符")
    private String category;

    /** 命中后的处理等级：1 疑似，2 违规，3 严重 */
    @NotNull(message = "请选择等级")
    private Integer level;

    /** 是否启用：1 启用，0 停用 */
    private Integer enabled;

    private LocalDateTime createTime;
}
