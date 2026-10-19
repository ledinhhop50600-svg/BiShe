package com.zimeiti.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.zimeiti.entity.AuditSensitiveWord;
import org.apache.ibatis.annotations.Mapper;

/** 敏感词数据访问 */
@Mapper
public interface AuditSensitiveWordMapper extends BaseMapper<AuditSensitiveWord> {
}
