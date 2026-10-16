package com.zimeiti.service;

import com.zimeiti.common.PageResult;
import com.zimeiti.dto.UserSaveDTO;
import com.zimeiti.vo.UserVO;

/**
 * 用户管理服务。
 */
public interface UserService {

    /** 分页查询用户（支持按账号模糊搜索、按状态筛选） */
    PageResult<UserVO> page(long current, long size, String username, Integer status);

    /** 查询单个用户详情（含角色 id，供编辑表单回填） */
    UserVO detail(Long id);

    void save(UserSaveDTO dto);

    void update(UserSaveDTO dto);

    /** 启用 / 禁用账号 */
    void updateStatus(Long id, Integer status);

    /** 重置密码 */
    void resetPassword(Long id, String newPassword);

    void delete(Long id);
}
