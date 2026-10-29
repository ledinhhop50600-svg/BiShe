package com.zimeiti.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 审核规则，对应 audit_rule 表。
 * <p>规则由主系统维护、在调用智能体时**随请求下发**（智能体不连数据库），
 * 所以这里是"规则的唯一数据源"。
 * <p>platformId 为空表示通用规则（所有平台适用）；有值表示某平台的专属规则。
 */
@Data
@TableName("audit_rule")
public class AuditRule {

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 规则编号，如 AD-003（判定理由里会引用它，便于溯源） */
    @NotBlank(message = "规则编号不能为空")
    @Size(max = 30, message = "规则编号最长 30 个字符")
    private String ruleCode;

    @NotBlank(message = "规则名称不能为空")
    @Size(max = 100, message = "规则名称最长 100 个字符")
    private String ruleName;

    /** 类别：广告法 / 虚假宣传 / 低俗擦边 / 引流诱导 / 违禁品 / 侵权 */
    @NotBlank(message = "规则类别不能为空")
    @Size(max = 30, message = "规则类别最长 30 个字符")
    private String category;

    /** 适用平台 id；为空表示通用规则 */
    private Long platformId;

    /** 规则内容描述（下发给智能体的规则文本） */
    @NotBlank(message = "规则内容不能为空")
    @Size(max = 1000, message = "规则内容最长 1000 个字符")
    private String ruleContent;

    /** 来源：法规或规范名称与条款 */
    @Size(max = 300, message = "依据来源最长 300 个字符")
    private String source;

    /** 命中后建议的风险等级：0 通过，1 疑似，2 违规，3 严重 */
    private Integer suggestedLevel;

    private Integer enabled;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}
