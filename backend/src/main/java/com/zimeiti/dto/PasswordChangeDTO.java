package com.zimeiti.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import lombok.Data;

/**
 * 修改密码：必须验证原密码（会话被盗时不能直接改密）。
 */
@Data
public class PasswordChangeDTO {

    @NotBlank(message = "请输入原密码")
    private String oldPassword;

    @NotBlank(message = "请输入新密码")
    @Pattern(regexp = "^(?=.*[A-Za-z])(?=.*\\d).{6,64}$",
            message = "新密码至少 6 位，且同时包含字母和数字")
    private String newPassword;

    @NotBlank(message = "请再次输入新密码")
    private String confirmPassword;
}
