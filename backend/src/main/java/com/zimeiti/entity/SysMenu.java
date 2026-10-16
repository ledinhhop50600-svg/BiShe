package com.zimeiti.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * 菜单实体，对应 sys_menu 表。
 * <p>这张表同时承担两件事：
 * 一是"界面菜单"（menuType 为 M 目录或 C 菜单页面），决定不同角色登录后能看到哪些菜单；
 * 二是"按钮权限"（menuType 为 F），决定页面上的按钮能不能点。
 * 两者用同一个 perms 字段（权限标识）串起来，后端接口靠它做校验。
 */
@Data
@TableName("sys_menu")
public class SysMenu {

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 上级菜单 id，0 表示顶级 */
    private Long parentId;

    /** 菜单名称（界面上显示的文字） */
    private String menuName;

    /** 类型：M 目录，C 菜单页面，F 按钮权限 */
    private String menuType;

    /** 前端路由地址 */
    private String path;

    /** 前端组件路径 */
    private String component;

    /** 权限标识，如 article:add */
    private String perms;

    private String icon;

    private Integer sort;

    /** 是否显示：1 显示，0 隐藏 */
    private Integer visible;

    /** 状态：1 启用，0 禁用 */
    private Integer status;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;

    /**
     * 子菜单。数据库里没有这一列，靠 @TableField(exist = false) 告诉 MyBatis-Plus 不要映射它，
     * 它只在组装菜单树时由 Java 代码填充。
     */
    @TableField(exist = false)
    private List<SysMenu> children = new ArrayList<>();
}
