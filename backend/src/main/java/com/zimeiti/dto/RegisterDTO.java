package com.zimeiti.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 自主注册请求。
 * <p>角色不由用户选择：注册一律分配「创作者」，管理员/审核员只能由管理员创建。
 */
@Data
public class RegisterDTO {

    @NotBlank(message = "请输入账号")
    @Pattern(regexp = "^[a-zA-Z0-9_]{3,20}$", message = "账号为 3-20 位字母、数字或下划线")
    private String username;

    @NotBlank(message = "请输入密码")
    @Pattern(regexp = "^(?=.*[A-Za-z])(?=.*\\d).{6,64}$",
            message = "密码至少 6 位，且同时包含字母和数字")
    private String password;

    @NotBlank(message = "请再次输入密码")
    private String confirmPassword;

    @NotBlank(message = "请输入昵称")
    @Size(max = 50, message = "昵称最长 50 个字符")
    private String nickname;

    @NotBlank(message = "请获取验证码")
    private String captchaId;

    @NotBlank(message = "请输入验证码")
    private String captchaAnswer;
}
