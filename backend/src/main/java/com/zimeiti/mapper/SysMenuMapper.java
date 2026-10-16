package com.zimeiti.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.zimeiti.entity.SysMenu;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * 菜单数据访问接口。
 */
@Mapper
public interface SysMenuMapper extends BaseMapper<SysMenu> {

    /**
     * 查询某个用户可见的全部菜单（含目录、菜单页面、按钮权限），按层级与排序返回。
     * <p>关联路径：用户 -> 用户角色 -> 角色菜单 -> 菜单。
     * <p>这条查询是"动态菜单"的数据来源：不同角色能看到什么菜单，完全由数据库里的关联决定，
     * 前端不写死任何菜单。
     */
    @Select("""
            SELECT DISTINCT m.*
            FROM sys_menu m
            JOIN sys_role_menu rm ON rm.menu_id = m.id
            JOIN sys_user_role ur ON ur.role_id = rm.role_id
            JOIN sys_role r ON r.id = ur.role_id
            WHERE ur.user_id = #{userId}
              AND m.status = 1
              AND r.status = 1
              AND r.deleted = 0
            ORDER BY m.parent_id, m.sort, m.id
            """)
    List<SysMenu> selectMenusByUserId(@Param("userId") Long userId);

    /**
     * 查询某个用户拥有的权限标识列表（如 [article:list, audit:workbench]）。
     * <p>Sa-Token 做接口鉴权时会调用它，判断"这个用户能不能访问这个接口"。
     * <p>只取有 perms 值的记录（目录类菜单没有权限标识）。
     */
    @Select("""
            SELECT DISTINCT m.perms
            FROM sys_menu m
            JOIN sys_role_menu rm ON rm.menu_id = m.id
            JOIN sys_user_role ur ON ur.role_id = rm.role_id
            JOIN sys_role r ON r.id = ur.role_id
            WHERE ur.user_id = #{userId}
              AND m.status = 1
              AND r.status = 1
              AND r.deleted = 0
              AND m.perms IS NOT NULL
              AND m.perms <> ''
            """)
    List<String> selectPermsByUserId(@Param("userId") Long userId);
}
