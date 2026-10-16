package com.zimeiti.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.zimeiti.entity.BizArticle;
import org.apache.ibatis.annotations.Mapper;

/**
 * 稿件数据访问接口。
 * <p>阶段 2 只用于统计（稿件总数、待审数量），阶段 3 会在此基础上实现完整的稿件管理。
 */
@Mapper
public interface BizArticleMapper extends BaseMapper<BizArticle> {
}
