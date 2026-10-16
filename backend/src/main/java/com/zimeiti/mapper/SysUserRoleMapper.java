package com.zimeiti.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.zimeiti.entity.SysUserRole;
import org.apache.ibatis.annotations.Mapper;

/**
 * 用户-角色关联数据访问接口。
 * <p>只有关联关系，单表增删改查用 BaseMapper 提供的方法即可，无需手写 SQL。
 */
@Mapper
public interface SysUserRoleMapper extends BaseMapper<SysUserRole> {
}
