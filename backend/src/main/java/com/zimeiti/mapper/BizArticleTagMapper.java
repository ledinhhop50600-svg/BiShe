package com.zimeiti.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.zimeiti.entity.BizArticleTag;
import org.apache.ibatis.annotations.Mapper;

/** 稿件-标签关联数据访问 */
@Mapper
public interface BizArticleTagMapper extends BaseMapper<BizArticleTag> {
}
