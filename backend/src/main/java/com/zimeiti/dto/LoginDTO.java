package com.zimeiti.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * 登录请求参数。
 * <p>使用 @NotBlank 做基础校验：前端传空值时，Spring 会直接拦下并返回友好提示，
 * 不用在业务代码里写 if (StringUtils.isEmpty(...))。
 */
@Data
public class LoginDTO {

    @NotBlank(message = "请输入账号")
    private String username;

    @NotBlank(message = "请输入密码")
    private String password;
}
