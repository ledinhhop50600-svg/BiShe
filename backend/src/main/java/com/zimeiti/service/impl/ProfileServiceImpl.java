package com.zimeiti.service.impl;

import cn.dev33.satoken.stp.StpUtil;
import com.zimeiti.common.BizException;
import com.zimeiti.dto.PasswordChangeDTO;
import com.zimeiti.dto.ProfileUpdateDTO;
import com.zimeiti.entity.SysUser;
import com.zimeiti.mapper.SysRoleMapper;
import com.zimeiti.mapper.SysUserMapper;
import com.zimeiti.service.ProfileService;
import com.zimeiti.vo.ProfileVO;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 个人中心实现。
 * <p>账号名不可修改：它是登录凭据，也是日志/审核记录里的身份标识，
 * 允许改会破坏历史可追溯性（主流平台同样不允许改）。
 */
@Service
@RequiredArgsConstructor
public class ProfileServiceImpl implements ProfileService {

    private final SysUserMapper userMapper;
    private final SysRoleMapper roleMapper;
    private final PasswordEncoder passwordEncoder;

    @Override
    public ProfileVO get() {
        SysUser user = currentUser();
        ProfileVO vo = new ProfileVO();
        vo.setId(user.getId());
        vo.setUsername(user.getUsername());
        vo.setNickname(user.getNickname());
        vo.setEmail(user.getEmail());
        vo.setPhone(user.getPhone());
        vo.setAvatar(user.getAvatar());
        vo.setRoles(roleMapper.selectRoleNamesByUserId(user.getId()));
        vo.setCreateTime(user.getCreateTime());
        return vo;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void update(ProfileUpdateDTO dto) {
        SysUser user = currentUser();
        SysUser update = new SysUser();
        update.setId(user.getId());
        update.setNickname(dto.getNickname().trim());
        // 空字符串而不是 null：MyBatis-Plus 默认忽略 null 字段，传 null 无法清空邮箱/手机号
        update.setEmail(trimToEmpty(dto.getEmail()));
        update.setPhone(trimToEmpty(dto.getPhone()));
        userMapper.updateById(update);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void changePassword(PasswordChangeDTO dto) {
        SysUser user = currentUser();
        if (!passwordEncoder.matches(dto.getOldPassword(), user.getPassword())) {
            throw new BizException(400, "原密码不正确");
        }
        if (!dto.getNewPassword().equals(dto.getConfirmPassword())) {
            throw new BizException(400, "两次输入的新密码不一致");
        }
        if (passwordEncoder.matches(dto.getNewPassword(), user.getPassword())) {
            throw new BizException(400, "新密码不能与原密码相同");
        }

        SysUser update = new SysUser();
        update.setId(user.getId());
        update.setPassword(passwordEncoder.encode(dto.getNewPassword()));
        userMapper.updateById(update);

        // 密码已变更：让当前令牌立即失效，前端回到登录页重新登录。
        // 这样即使会话被别人占用，改密后对方也会被踢下线。
        StpUtil.logout();
    }

    private SysUser currentUser() {
        long userId = StpUtil.getLoginIdAsLong();
        SysUser user = userMapper.selectById(userId);
        if (user == null) {
            throw new BizException(401, "账号不存在或已被删除，请重新登录");
        }
        return user;
    }

    private String trimToEmpty(String s) {
        return s == null ? "" : s.trim();
    }
}
