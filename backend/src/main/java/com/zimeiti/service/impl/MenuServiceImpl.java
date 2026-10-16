package com.zimeiti.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.zimeiti.common.BizException;
import com.zimeiti.dto.MenuSaveDTO;
import com.zimeiti.entity.SysMenu;
import com.zimeiti.entity.SysRoleMenu;
import com.zimeiti.mapper.SysMenuMapper;
import com.zimeiti.mapper.SysRoleMenuMapper;
import com.zimeiti.service.MenuService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 菜单管理实现。
 */
@Service
@RequiredArgsConstructor
public class MenuServiceImpl implements MenuService {

    private final SysMenuMapper menuMapper;
    private final SysRoleMenuMapper roleMenuMapper;

    @Override
    public List<SysMenu> treeAll() {
        List<SysMenu> all = menuMapper.selectList(Wrappers.<SysMenu>lambdaQuery()
                .orderByAsc(SysMenu::getParentId)
                .orderByAsc(SysMenu::getSort)
                .orderByAsc(SysMenu::getId));
        return buildTree(all);
    }

    @Override
    public void save(MenuSaveDTO dto) {
        validate(dto);
        SysMenu menu = new SysMenu();
        copy(dto, menu);
        menuMapper.insert(menu);
    }

    @Override
    public void update(MenuSaveDTO dto) {
        SysMenu exist = menuMapper.selectById(dto.getId());
        if (exist == null) {
            throw new BizException("菜单不存在");
        }
        validate(dto);
        // 不能把菜单挂到自己或自己的子孙下面，否则菜单树会出现环，前端渲染会死循环
        if (dto.getId().equals(dto.getParentId())) {
            throw new BizException("上级菜单不能是自己");
        }
        if (isDescendant(dto.getId(), dto.getParentId())) {
            throw new BizException("上级菜单不能是自己的下级菜单");
        }
        SysMenu menu = new SysMenu();
        menu.setId(dto.getId());
        copy(dto, menu);
        menuMapper.updateById(menu);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void delete(Long id) {
        SysMenu menu = menuMapper.selectById(id);
        if (menu == null) {
            throw new BizException("菜单不存在");
        }
        Long childCount = menuMapper.selectCount(
                Wrappers.<SysMenu>lambdaQuery().eq(SysMenu::getParentId, id));
        if (childCount != null && childCount > 0) {
            throw new BizException("请先删除下级菜单");
        }
        Long roleCount = roleMenuMapper.selectCount(
                Wrappers.<SysRoleMenu>lambdaQuery().eq(SysRoleMenu::getMenuId, id));
        if (roleCount != null && roleCount > 0) {
            throw new BizException("该菜单已分配给 " + roleCount + " 个角色，请先取消授权");
        }
        menuMapper.deleteById(id);
    }

    /** 基础校验：菜单页面必须有路由地址；按钮权限必须有权限标识 */
    private void validate(MenuSaveDTO dto) {
        if ("C".equals(dto.getMenuType()) && !StringUtils.hasText(dto.getPath())) {
            throw new BizException("菜单页面必须填写路由地址");
        }
        if ("F".equals(dto.getMenuType()) && !StringUtils.hasText(dto.getPerms())) {
            throw new BizException("按钮权限必须填写权限标识");
        }
    }

    /**
     * 判断 candidateParentId 是否是 menuId 的子孙菜单。
     * <p>做法：从候选上级往上找父级，一路找到根；如果中途遇到 menuId，说明候选上级在它下方。
     * 菜单树很浅（三层以内），这种逐级上溯的写法最直观。
     */
    private boolean isDescendant(Long menuId, Long candidateParentId) {
        Long cursor = candidateParentId;
        int guard = 0;
        while (cursor != null && cursor != 0L && guard++ < 20) {
            if (cursor.equals(menuId)) {
                return true;
            }
            SysMenu parent = menuMapper.selectById(cursor);
            cursor = parent == null ? null : parent.getParentId();
        }
        return false;
    }

    private void copy(MenuSaveDTO dto, SysMenu menu) {
        menu.setParentId(dto.getParentId());
        menu.setMenuName(dto.getMenuName());
        menu.setMenuType(dto.getMenuType());
        menu.setPath(dto.getPath());
        menu.setComponent(dto.getComponent());
        menu.setPerms(dto.getPerms());
        menu.setIcon(dto.getIcon());
        menu.setSort(dto.getSort());
        menu.setVisible(dto.getVisible());
        menu.setStatus(dto.getStatus());
    }

    /** 把扁平列表组装成树（与登录时组装用户菜单树的逻辑一致） */
    private List<SysMenu> buildTree(List<SysMenu> all) {
        Map<Long, SysMenu> byId = new LinkedHashMap<>();
        for (SysMenu m : all) {
            byId.put(m.getId(), m);
        }
        List<SysMenu> roots = new ArrayList<>();
        for (SysMenu m : byId.values()) {
            Long parentId = m.getParentId();
            if (parentId == null || parentId == 0L) {
                roots.add(m);
                continue;
            }
            SysMenu parent = byId.get(parentId);
            if (parent != null) {
                parent.getChildren().add(m);
            } else {
                roots.add(m);
            }
        }
        return roots;
    }
}
