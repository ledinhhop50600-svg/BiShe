package com.zimeiti.service;

import com.zimeiti.common.PageResult;
import com.zimeiti.dto.RoleSaveDTO;
import com.zimeiti.entity.SysRole;

import java.util.List;

/**
 * 角色管理服务。
 */
public interface RoleService {

    /** 分页查询角色 */
    PageResult<SysRole> page(long current, long size, String roleName);

    /** 查询全部启用角色（给"用户管理"里分配角色用） */
    List<SysRole> listAll();

    /** 查询某角色已勾选的菜单 id（含按钮权限） */
    List<Long> menuIds(Long roleId);

    void save(RoleSaveDTO dto);

    void update(RoleSaveDTO dto);

    void delete(Long id);
}
