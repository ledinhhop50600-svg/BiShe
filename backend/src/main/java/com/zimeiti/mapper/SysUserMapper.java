package com.zimeiti.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.zimeiti.entity.SysUser;
import org.apache.ibatis.annotations.Mapper;

/**
 * 用户数据访问接口。
 * <p>继承 BaseMapper 后，用户表的单表增删改查都无需手写 SQL（selectById / selectList / insert / updateById ...）。
 * <p>注意：由于实体上有 @TableLogic，所有查询都会自动带上 deleted = 0 条件，已逻辑删除的用户查不出来。
 */
@Mapper
public interface SysUserMapper extends BaseMapper<SysUser> {
}
