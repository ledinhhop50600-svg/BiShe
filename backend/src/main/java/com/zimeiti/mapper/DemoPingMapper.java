package com.zimeiti.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.zimeiti.entity.DemoPing;
import org.apache.ibatis.annotations.Mapper;

/**
 * 数据访问接口。
 * <p>继承 MyBatis-Plus 的 BaseMapper 后，单表增删改查无需手写任何 SQL：
 * selectList / selectById / insert / updateById / deleteById 等方法已由框架提供。
 * <p>本接口没有任何方法体，也不需要在 XML 里写 SQL —— 这是 MyBatis-Plus 与手写 MyBatis 的主要差别。
 */
@Mapper
public interface DemoPingMapper extends BaseMapper<DemoPing> {
}
