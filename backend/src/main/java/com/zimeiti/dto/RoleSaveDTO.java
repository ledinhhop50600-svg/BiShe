package com.zimeiti.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.util.List;

/**
 * 角色新增/修改的请求参数。
 * <p>menuIds 是"这个角色被勾选了哪些菜单与按钮权限"，保存时会整体覆盖 sys_role_menu 里该角色的记录。
 */
@Data
public class RoleSaveDTO {

    private Long id;

    @NotBlank(message = "角色名称不能为空")
    @Size(max = 20, message = "角色名称最长 20 个字符")
    private String roleName;

    @NotBlank(message = "角色标识不能为空")
    @Pattern(regexp = "^[a-zA-Z0-9_]+$", message = "角色标识只能包含字母、数字和下划线")
    @Size(max = 50, message = "角色标识最长 50 个字符")
    private String roleKey;

    @Size(max = 255, message = "角色说明最长 255 个字符")
    private String description;

    @NotNull(message = "请填写排序号")
    private Integer sort;

    @NotNull(message = "请选择状态")
    private Integer status;

    /** 该角色拥有的菜单 id 列表（含按钮权限） */
    private List<Long> menuIds;
}
