package com.zimeiti.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 菜单新增/修改的请求参数。
 * <p>按钮权限（menuType = F）不需要 path 与 component，只需填 menuName 和 perms。
 */
@Data
public class MenuSaveDTO {

    private Long id;

    /** 上级菜单 id，0 表示顶级 */
    @NotNull(message = "请选择上级菜单")
    private Long parentId;

    @NotBlank(message = "菜单名称不能为空")
    @Size(max = 50, message = "菜单名称最长 50 个字符")
    private String menuName;

    /** M 目录 / C 菜单页面 / F 按钮权限 */
    @NotBlank(message = "请选择菜单类型")
    private String menuType;

    /** 前端路由地址（目录与菜单页面需要） */
    @Size(max = 200, message = "路由地址最长 200 个字符")
    private String path;

    /** 前端组件路径（菜单页面需要） */
    @Size(max = 200, message = "组件路径最长 200 个字符")
    private String component;

    /** 权限标识，如 article:list */
    @Size(max = 100, message = "权限标识最长 100 个字符")
    private String perms;

    @Size(max = 50, message = "图标最长 50 个字符")
    private String icon;

    @NotNull(message = "请填写排序号")
    private Integer sort;

    @NotNull(message = "请选择是否显示")
    private Integer visible;

    @NotNull(message = "请选择状态")
    private Integer status;
}
