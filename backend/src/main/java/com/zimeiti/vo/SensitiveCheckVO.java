package com.zimeiti.vo;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

/**
 * 敏感词检测结果（传统关键词匹配基线的输出）。
 * <p>这个结果之所以要单独成一个对象，是因为它是**论文对比实验的基线输出**：
 * 阶段 8 会把"关键词匹配"与"智能体审核"在同一批样本上的结果放在一起比较 ——
 * 关键词匹配只能给出"命中了哪些词"，给不出语境判断、判定理由和修改建议。
 */
@Data
public class SensitiveCheckVO {

    /** 命中的敏感词 */
    private List<String> matched = new ArrayList<>();

    /** 命中词的最高等级：0 未命中，1 疑似，2 违规，3 严重 */
    private Integer maxLevel = 0;

    /** 命中词所属类别（去重） */
    private List<String> categories = new ArrayList<>();

    /** 结论：true 表示未命中任何敏感词 */
    private Boolean passed;

    /** 给使用者看的说明文字 */
    private String message;
}
