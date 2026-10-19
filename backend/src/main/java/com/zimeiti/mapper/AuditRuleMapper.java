package com.zimeiti.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.zimeiti.entity.AuditRule;
import org.apache.ibatis.annotations.Mapper;

/** 审核规则数据访问 */
@Mapper
public interface AuditRuleMapper extends BaseMapper<AuditRule> {
}
