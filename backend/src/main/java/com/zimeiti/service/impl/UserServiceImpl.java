package com.zimeiti.service.impl;

import cn.dev33.satoken.stp.StpUtil;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zimeiti.common.BizException;
import com.zimeiti.common.PageResult;
import com.zimeiti.dto.UserSaveDTO;
import com.zimeiti.entity.SysUser;
import com.zimeiti.entity.SysUserRole;
import com.zimeiti.mapper.SysRoleMapper;
import com.zimeiti.mapper.SysUserMapper;
import com.zimeiti.mapper.SysUserRoleMapper;
import com.zimeiti.service.UserService;
import com.zimeiti.vo.UserVO;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;

/**
 * 用户管理实现。
 */
@Service
@RequiredArgsConstructor
public class UserServiceImpl implements UserService {

    private final SysUserMapper userMapper;
    private final SysRoleMapper roleMapper;
    private final SysUserRoleMapper userRoleMapper;
    private final PasswordEncoder passwordEncoder;

    @Override
    public PageResult<UserVO> page(long current, long size, String username, Integer status) {
        Page<SysUser> page = userMapper.selectPage(new Page<>(current, size),
                Wrappers.<SysUser>lambdaQuery()
                        .like(StringUtils.hasText(username), SysUser::getUsername, username)
                        .eq(status != null, SysUser::getStatus, status)
                        .orderByAsc(SysUser::getId));

        // 说明：这里为每个用户单独查了一次角色（N+1 查询）。在本项目的数据规模下（几十个用户）
        // 完全够用，且代码最直观。若用户量很大，应改为一次批量查询后按用户分组。
        List<UserVO> records = new ArrayList<>();
        for (SysUser user : page.getRecords()) {
            records.add(toVO(user));
        }
        return PageResult.of(records, page.getTotal(), page.getCurrent(), page.getSize());
    }

    @Override
    public UserVO detail(Long id) {
        SysUser user = userMapper.selectById(id);
        if (user == null) {
            throw new BizException("用户不存在");
        }
        return toVO(user);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void save(UserSaveDTO dto) {
        if (usernameExists(dto.getUsername(), null)) {
            throw new BizException("账号已存在：" + dto.getUsername());
        }
        if (!StringUtils.hasText(dto.getPassword())) {
            throw new BizException("新增用户时必须设置初始密码");
        }
        SysUser user = new SysUser();
        copy(dto, user);
        // 密码加密存储：数据库里只有哈希，看不到明文
        user.setPassword(passwordEncoder.encode(dto.getPassword()));
        userMapper.insert(user);
        saveUserRoles(user.getId(), dto.getRoleIds());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void update(UserSaveDTO dto) {
        if (dto.getId() == null) {
            throw new BizException("缺少用户 id");
        }
        SysUser exist = userMapper.selectById(dto.getId());
        if (exist == null) {
            throw new BizException("用户不存在");
        }
        if (usernameExists(dto.getUsername(), dto.getId())) {
            throw new BizException("账号已被其他用户使用：" + dto.getUsername());
        }
        SysUser user = new SysUser();
        user.setId(dto.getId());
        copy(dto, user);
        // 密码留空表示不修改密码（编辑用户时不必每次都重设）
        if (StringUtils.hasText(dto.getPassword())) {
            user.setPassword(passwordEncoder.encode(dto.getPassword()));
        }
        userMapper.updateById(user);

        // 角色关系整体覆盖
        userRoleMapper.delete(Wrappers.<SysUserRole>lambdaQuery().eq(SysUserRole::getUserId, dto.getId()));
        saveUserRoles(dto.getId(), dto.getRoleIds());
    }

    @Override
    public void updateStatus(Long id, Integer status) {
        if (StpUtil.getLoginIdAsLong() == id) {
            throw new BizException("不能禁用当前登录的账号");
        }
        SysUser user = userMapper.selectById(id);
        if (user == null) {
            throw new BizException("用户不存在");
        }
        SysUser update = new SysUser();
        update.setId(id);
        update.setStatus(status);
        userMapper.updateById(update);
    }

    @Override
    public void resetPassword(Long id, String newPassword) {
        if (!StringUtils.hasText(newPassword) || newPassword.length() < 6) {
            throw new BizException("新密码长度不能少于 6 位");
        }
        SysUser user = userMapper.selectById(id);
        if (user == null) {
            throw new BizException("用户不存在");
        }
        SysUser update = new SysUser();
        update.setId(id);
        update.setPassword(passwordEncoder.encode(newPassword));
        userMapper.updateById(update);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void delete(Long id) {
        if (StpUtil.getLoginIdAsLong() == id) {
            throw new BizException("不能删除当前登录的账号");
        }
        SysUser user = userMapper.selectById(id);
        if (user == null) {
            throw new BizException("用户不存在");
        }
        // 逻辑删除：数据仍在库里，只是查询时被过滤掉（平台数据需要可追溯）
        userMapper.deleteById(id);
        userRoleMapper.delete(Wrappers.<SysUserRole>lambdaQuery().eq(SysUserRole::getUserId, id));
    }

    private boolean usernameExists(String username, Long excludeId) {
        return userMapper.selectCount(Wrappers.<SysUser>lambdaQuery()
                .eq(SysUser::getUsername, username)
                .ne(excludeId != null, SysUser::getId, excludeId)) > 0;
    }

    private void copy(UserSaveDTO dto, SysUser user) {
        user.setUsername(dto.getUsername());
        user.setNickname(dto.getNickname());
        user.setEmail(dto.getEmail());
        user.setPhone(dto.getPhone());
        user.setStatus(dto.getStatus());
        user.setRemark(dto.getRemark());
    }

    private void saveUserRoles(Long userId, List<Long> roleIds) {
        if (roleIds == null || roleIds.isEmpty()) {
            return;
        }
        for (Long roleId : new LinkedHashSet<>(roleIds)) {
            userRoleMapper.insert(new SysUserRole(userId, roleId));
        }
    }

    private UserVO toVO(SysUser user) {
        UserVO vo = new UserVO();
        vo.setId(user.getId());
        vo.setUsername(user.getUsername());
        vo.setNickname(user.getNickname());
        vo.setEmail(user.getEmail());
        vo.setPhone(user.getPhone());
        vo.setStatus(user.getStatus());
        vo.setRemark(user.getRemark());
        vo.setCreateTime(user.getCreateTime());
        vo.setRoleIds(userRoleMapper.selectList(Wrappers.<SysUserRole>lambdaQuery()
                        .eq(SysUserRole::getUserId, user.getId()))
                .stream().map(SysUserRole::getRoleId).toList());
        vo.setRoleNames(roleMapper.selectRoleNamesByUserId(user.getId()));
        return vo;
    }
}
