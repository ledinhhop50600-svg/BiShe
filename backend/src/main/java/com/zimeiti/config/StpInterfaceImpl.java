package com.zimeiti.config;

import cn.dev33.satoken.stp.StpInterface;
import com.zimeiti.mapper.SysMenuMapper;
import com.zimeiti.mapper.SysRoleMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * Sa-Token 的权限数据来源。
 * <p>Sa-Token 自己不知道"这个用户有哪些角色和权限"，它会回调这个接口来问。
 * 我们在这里从数据库里查出来交给它，之后就可以在接口上写
 * {@code @SaCheckPermission("article:list")} 或 {@code @SaCheckRole("admin")} 做校验。
 * <p>这样设计的关键好处：权限数据全在数据库里（用户-角色-菜单三张关联表），
 * 改权限只需要改数据，不用改代码、不用重新部署。
 */
@Component
@RequiredArgsConstructor
public class StpInterfaceImpl implements StpInterface {

    private final SysMenuMapper menuMapper;
    private final SysRoleMapper roleMapper;

    /** 返回该用户的权限标识列表，如 ["article:list", "audit:workbench"] */
    @Override
    public List<String> getPermissionList(Object loginId, String loginType) {
        return menuMapper.selectPermsByUserId(toUserId(loginId));
    }

    /** 返回该用户的角色标识列表，如 ["reviewer"] */
    @Override
    public List<String> getRoleList(Object loginId, String loginType) {
        return roleMapper.selectRoleKeysByUserId(toUserId(loginId));
    }

    /** Sa-Token 传入的 loginId 是 Object 类型（本项目存的是用户 id），统一转成 Long 用 */
    private Long toUserId(Object loginId) {
        return Long.valueOf(String.valueOf(loginId));
    }
}
