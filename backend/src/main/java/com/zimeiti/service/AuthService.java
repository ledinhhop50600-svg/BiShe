package com.zimeiti.service;

import com.zimeiti.dto.LoginDTO;
import com.zimeiti.dto.RegisterDTO;
import com.zimeiti.vo.LoginVO;
import com.zimeiti.vo.UserInfoVO;

/**
 * 认证服务：注册、登录、登出、获取当前登录用户。
 */
public interface AuthService {

    /** 注册：校验验证码与账号规则，固定分配「创作者」角色，注册成功后直接登录 */
    LoginVO register(RegisterDTO dto);

    /** 登录：校验账号密码，成功后签发令牌 */
    LoginVO login(LoginDTO dto);

    /** 获取当前登录用户信息（含角色、权限、菜单） */
    UserInfoVO currentUser();

    /** 登出：注销当前令牌对应的登录状态 */
    void logout();
}
