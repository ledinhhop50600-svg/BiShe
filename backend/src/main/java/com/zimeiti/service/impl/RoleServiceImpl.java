package com.zimeiti.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zimeiti.common.BizException;
import com.zimeiti.common.PageResult;
import com.zimeiti.dto.RoleSaveDTO;
import com.zimeiti.entity.SysRole;
import com.zimeiti.entity.SysRoleMenu;
import com.zimeiti.entity.SysUserRole;
import com.zimeiti.mapper.SysRoleMapper;
import com.zimeiti.mapper.SysRoleMenuMapper;
import com.zimeiti.mapper.SysUserRoleMapper;
import com.zimeiti.service.RoleService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;

/**
 * 角色管理实现。
 * <p>给角色分配菜单权限的做法是"整体覆盖"：先把该角色的关联记录全部删掉，再按前端提交的
 * menuIds 重新插入。这比逐条比对增删更简单，也不容易出错（代价是每次保存都重写关联记录，
 * 对权限这种低频操作完全可以接受）。
 */
@Service
@RequiredArgsConstructor
public class RoleServiceImpl implements RoleService {

    private final SysRoleMapper roleMapper;
    private final SysRoleMenuMapper roleMenuMapper;
    private final SysUserRoleMapper userRoleMapper;

    @Override
    public PageResult<SysRole> page(long current, long size, String roleName) {
        Page<SysRole> page = roleMapper.selectPage(new Page<>(current, size),
                Wrappers.<SysRole>lambdaQuery()
                        .like(StringUtils.hasText(roleName), SysRole::getRoleName, roleName)
                        .orderByAsc(SysRole::getSort));
        return PageResult.of(page.getRecords(), page.getTotal(), page.getCurrent(), page.getSize());
    }

    @Override
    public List<SysRole> listAll() {
        return roleMapper.selectList(Wrappers.<SysRole>lambdaQuery()
                .eq(SysRole::getStatus, 1)
                .orderByAsc(SysRole::getSort));
    }

    @Override
    public List<Long> menuIds(Long roleId) {
        return roleMenuMapper.selectList(Wrappers.<SysRoleMenu>lambdaQuery()
                        .eq(SysRoleMenu::getRoleId, roleId))
                .stream()
                .map(SysRoleMenu::getMenuId)
                .toList();
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void save(RoleSaveDTO dto) {
        if (roleKeyExists(dto.getRoleKey(), null)) {
            throw new BizException("角色标识已存在：" + dto.getRoleKey());
        }
        SysRole role = new SysRole();
        copy(dto, role);
        roleMapper.insert(role);
        saveRoleMenus(role.getId(), dto.getMenuIds());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void update(RoleSaveDTO dto) {
        if (dto.getId() == null) {
            throw new BizException("缺少角色 id");
        }
        SysRole exist = roleMapper.selectById(dto.getId());
        if (exist == null) {
            throw new BizException("角色不存在");
        }
        if (roleKeyExists(dto.getRoleKey(), dto.getId())) {
            throw new BizException("角色标识已被其他角色使用：" + dto.getRoleKey());
        }
        SysRole role = new SysRole();
        role.setId(dto.getId());
        copy(dto, role);
        roleMapper.updateById(role);

        // 权限整体覆盖
        roleMenuMapper.delete(Wrappers.<SysRoleMenu>lambdaQuery().eq(SysRoleMenu::getRoleId, dto.getId()));
        saveRoleMenus(dto.getId(), dto.getMenuIds());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void delete(Long id) {
        SysRole role = roleMapper.selectById(id);
        if (role == null) {
            throw new BizException("角色不存在");
        }
        // 角色下还有用户时不允许删除：否则这些用户会失去全部权限，属于危险操作
        Long userCount = userRoleMapper.selectCount(
                Wrappers.<SysUserRole>lambdaQuery().eq(SysUserRole::getRoleId, id));
        if (userCount != null && userCount > 0) {
            throw new BizException("该角色下还有 " + userCount + " 个用户，请先调整这些用户的角色");
        }
        roleMapper.deleteById(id);
        roleMenuMapper.delete(Wrappers.<SysRoleMenu>lambdaQuery().eq(SysRoleMenu::getRoleId, id));
    }

    private boolean roleKeyExists(String roleKey, Long excludeId) {
        return roleMapper.selectCount(Wrappers.<SysRole>lambdaQuery()
                .eq(SysRole::getRoleKey, roleKey)
                .ne(excludeId != null, SysRole::getId, excludeId)) > 0;
    }

    private void copy(RoleSaveDTO dto, SysRole role) {
        role.setRoleName(dto.getRoleName());
        role.setRoleKey(dto.getRoleKey());
        role.setDescription(dto.getDescription());
        role.setSort(dto.getSort());
        role.setStatus(dto.getStatus());
    }

    /** 去重后批量插入角色-菜单关联（前端树组件可能提交重复 id） */
    private void saveRoleMenus(Long roleId, List<Long> menuIds) {
        if (menuIds == null || menuIds.isEmpty()) {
            return;
        }
        List<SysRoleMenu> links = new ArrayList<>();
        for (Long menuId : new LinkedHashSet<>(menuIds)) {
            links.add(new SysRoleMenu(roleId, menuId));
        }
        for (SysRoleMenu link : links) {
            roleMenuMapper.insert(link);
        }
    }
}
