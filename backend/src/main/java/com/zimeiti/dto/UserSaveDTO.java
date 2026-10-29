package com.zimeiti.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.util.List;

/**
 * 用户新增/修改的请求参数。
 * <p>为什么不直接用 SysUser 实体接收参数？两个原因：
 *  1. 接口参数与数据库字段不一定一一对应（例如这里的 roleIds 在数据库里是另一张表）；
 *  2. 可以精确控制"哪些字段允许被前端传入"，避免越权改到不该改的字段。
 */
@Data
public class UserSaveDTO {

    /** 主键：新增时为空，修改时必填 */
    private Long id;

    @NotBlank(message = "账号不能为空")
    @Size(min = 3, max = 20, message = "账号长度需在 3-20 之间")
    @Pattern(regexp = "^[a-zA-Z0-9_]+$", message = "账号只能包含字母、数字和下划线")
    private String username;

    /** 密码：新增时必填；修改时留空表示不改密码 */
    @Size(max = 64, message = "密码最长 64 个字符")
    private String password;

    @NotBlank(message = "昵称不能为空")
    @Size(max = 20, message = "昵称最长 20 个字符")
    private String nickname;

    @Email(message = "邮箱格式不正确")
    @Size(max = 100, message = "邮箱最长 100 个字符")
    private String email;

    @Pattern(regexp = "^$|^1[3-9][0-9]{9}$", message = "手机号格式不正确")
    @Size(max = 20, message = "手机号最长 20 个字符")
    private String phone;

    @NotNull(message = "请选择状态")
    private Integer status;

    @Size(max = 255, message = "备注最长 255 个字符")
    private String remark;

    /** 该用户拥有的角色 id 列表 */
    private List<Long> roleIds;
}
