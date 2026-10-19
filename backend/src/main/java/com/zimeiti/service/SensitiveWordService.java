package com.zimeiti.service;

import com.zimeiti.common.PageResult;
import com.zimeiti.entity.AuditSensitiveWord;
import com.zimeiti.vo.SensitiveCheckVO;

/**
 * 敏感词服务（传统关键词匹配方案）。
 * <p>这个模块在系统里承担两个角色：
 *  1. 实际的初筛工具：命中词直接标出来，给人一个最低成本的参考；
 *  2. **论文对比实验的基线**：阶段 8 会把它的结果与智能体的审核结果放在同一批样本上比较。
 */
public interface SensitiveWordService {

    PageResult<AuditSensitiveWord> page(long current, long size, String word, String category);

    void save(AuditSensitiveWord word);

    void update(AuditSensitiveWord word);

    void delete(Long id);

    /** 对一段文本做敏感词检测（朴素子串匹配），返回命中词与最高等级 */
    SensitiveCheckVO check(String text);
}
