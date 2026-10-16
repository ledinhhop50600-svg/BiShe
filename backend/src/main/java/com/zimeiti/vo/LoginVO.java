package com.zimeiti.vo;

import lombok.Data;

/**
 * 登录成功后的返回内容。
 * <p>tokenName 是令牌在请求头里的名字（本项目为 satoken），tokenValue 是令牌值。
 * 前端拿到后需要保存 tokenValue，之后每次请求都放进请求头里 —— 这就是"登录状态"的载体。
 */
@Data
public class LoginVO {

    /** 令牌名称，默认 satoken */
    private String tokenName;

    /** 令牌值 */
    private String tokenValue;

    /** 登录用户信息（含角色、权限、菜单） */
    private UserInfoVO userInfo;
}
