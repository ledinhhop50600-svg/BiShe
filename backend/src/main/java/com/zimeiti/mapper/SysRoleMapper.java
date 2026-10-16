package com.zimeiti.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.zimeiti.entity.SysRole;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * 角色数据访问接口。
 */
@Mapper
public interface SysRoleMapper extends BaseMapper<SysRole> {

    /**
     * 查询某个用户拥有的角色标识列表（如 [reviewer]）。
     * <p>这里手写 SQL 而不是用 BaseMapper：因为需要跨三张表关联（用户-角色-角色），
     * 这正是"单表用框架、多表手写 SQL"的分界线。
     */
    @Select("""
            SELECT r.role_key
            FROM sys_role r
            JOIN sys_user_role ur ON ur.role_id = r.id
            WHERE ur.user_id = #{userId} AND r.status = 1 AND r.deleted = 0
            """)
    List<String> selectRoleKeysByUserId(@Param("userId") Long userId);

    /**
     * 查询某个用户的角色名称列表（如 [审核员]），用于界面上显示身份标签。
     */
    @Select("""
            SELECT r.role_name
            FROM sys_role r
            JOIN sys_user_role ur ON ur.role_id = r.id
            WHERE ur.user_id = #{userId} AND r.status = 1 AND r.deleted = 0
            """)
    List<String> selectRoleNamesByUserId(@Param("userId") Long userId);
}
