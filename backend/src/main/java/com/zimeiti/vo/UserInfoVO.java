package com.zimeiti.vo;

import com.zimeiti.entity.SysMenu;
import lombok.Data;

import java.util.List;

/**
 * 当前登录用户的信息，用于登录成功后返回、以及前端刷新页面时拉取。
 * <p>为什么要把菜单和权限一起返回？因为前端要用它来渲染菜单和判断按钮是否可见。
 * 这样前端不需要写死任何菜单，全部由后端根据角色下发。
 */
@Data
public class UserInfoVO {

    private Long id;

    private String username;

    private String nickname;

    private String avatar;

    /** 角色名称，用于界面显示，如 ["审核员"] */
    private List<String> roles;

    /** 角色标识，用于程序判断，如 ["reviewer"] */
    private List<String> roleKeys;

    /** 权限标识列表，如 ["article:list", "audit:rejudge"]，用于按钮级权限控制 */
    private List<String> permissions;

    /** 菜单树（目录 + 菜单页面），前端据此渲染导航 */
    private List<SysMenu> menus;
}
