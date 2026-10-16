package com.zimeiti.service;

import com.zimeiti.dto.MenuSaveDTO;
import com.zimeiti.entity.SysMenu;

import java.util.List;

/**
 * 菜单管理服务。
 */
public interface MenuService {

    /** 查询完整菜单树（菜单管理页、角色分配权限的树都用它） */
    List<SysMenu> treeAll();

    void save(MenuSaveDTO dto);

    void update(MenuSaveDTO dto);

    void delete(Long id);
}
