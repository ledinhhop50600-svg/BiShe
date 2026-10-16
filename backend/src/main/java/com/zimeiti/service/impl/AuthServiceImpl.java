package com.zimeiti.service.impl;

import cn.dev33.satoken.stp.StpUtil;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.zimeiti.common.BizException;
import com.zimeiti.dto.LoginDTO;
import com.zimeiti.entity.SysMenu;
import com.zimeiti.entity.SysUser;
import com.zimeiti.mapper.SysMenuMapper;
import com.zimeiti.mapper.SysRoleMapper;
import com.zimeiti.mapper.SysUserMapper;
import com.zimeiti.service.AuthService;
import com.zimeiti.vo.LoginVO;
import com.zimeiti.vo.UserInfoVO;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 认证服务实现。
 * <p>登录流程：按账号查用户 -> 校验密码 -> 检查账号状态 -> 签发令牌 -> 返回令牌与用户信息。
 */
@Service
@RequiredArgsConstructor
public class AuthServiceImpl implements AuthService {

    private final SysUserMapper userMapper;
    private final SysRoleMapper roleMapper;
    private final SysMenuMapper menuMapper;
    private final PasswordEncoder passwordEncoder;

    @Override
    public LoginVO login(LoginDTO dto) {
        SysUser user = userMapper.selectOne(
                Wrappers.<SysUser>lambdaQuery().eq(SysUser::getUsername, dto.getUsername().trim()));

        // 账号不存在与密码错误返回同一句提示：避免被用来试探系统里有哪些账号
        if (user == null || !passwordEncoder.matches(dto.getPassword(), user.getPassword())) {
            throw new BizException("账号或密码错误");
        }
        if (Integer.valueOf(0).equals(user.getStatus())) {
            throw new BizException("账号已被禁用，请联系管理员");
        }

        // 登录成功：Sa-Token 生成令牌并记录登录状态（loginId 用用户 id）
        StpUtil.login(user.getId());

        LoginVO vo = new LoginVO();
        vo.setTokenName(StpUtil.getTokenName());
        vo.setTokenValue(StpUtil.getTokenValue());
        vo.setUserInfo(buildUserInfo(user));
        return vo;
    }

    @Override
    public UserInfoVO currentUser() {
        // 从当前请求携带的令牌解析出登录用户 id；未登录会抛异常，由全局异常处理器返回 401
        long userId = StpUtil.getLoginIdAsLong();
        SysUser user = userMapper.selectById(userId);
        if (user == null) {
            throw new BizException(401, "账号不存在或已被删除，请重新登录");
        }
        return buildUserInfo(user);
    }

    @Override
    public void logout() {
        StpUtil.logout();
    }

    /**
     * 组装用户信息：角色名称（界面显示用）、角色标识（程序判断用）、权限标识、菜单树。
     */
    private UserInfoVO buildUserInfo(SysUser user) {
        UserInfoVO vo = new UserInfoVO();
        vo.setId(user.getId());
        vo.setUsername(user.getUsername());
        vo.setNickname(user.getNickname());
        vo.setAvatar(user.getAvatar());
        vo.setRoles(roleMapper.selectRoleNamesByUserId(user.getId()));
        vo.setRoleKeys(roleMapper.selectRoleKeysByUserId(user.getId()));
        vo.setPermissions(menuMapper.selectPermsByUserId(user.getId()));
        vo.setMenus(buildMenuTree(menuMapper.selectMenusByUserId(user.getId())));
        return vo;
    }

    /**
     * 把扁平的菜单列表组装成树。
     * <p>数据库里菜单层级靠 parent_id 表达，而前端渲染导航需要嵌套结构，所以在后端一次性组装好，
     * 前端拿到直接能用，不用再写一遍递归逻辑。
     * <p>按钮权限（menuType = F）不进入菜单树 —— 它们只参与权限校验，不是能点开的页面。
     */
    private List<SysMenu> buildMenuTree(List<SysMenu> all) {
        Map<Long, SysMenu> byId = new LinkedHashMap<>();
        for (SysMenu m : all) {
            if (!"F".equals(m.getMenuType())) {
                byId.put(m.getId(), m);
            }
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
                // 兜底：父菜单没有权限时，把它当顶级显示，避免菜单凭空消失
                roots.add(m);
            }
        }
        return roots;
    }
}
