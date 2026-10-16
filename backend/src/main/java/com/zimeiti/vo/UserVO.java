package com.zimeiti.vo;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 用户列表与详情返回对象。
 * <p>比 SysUser 实体多带了 roleIds / roleNames：因为界面上要显示"这个用户是什么角色"，
 * 而角色信息存在关联表里，需要额外查询后拼进来。
 */
@Data
public class UserVO {

    private Long id;

    private String username;

    private String nickname;

    private String email;

    private String phone;

    private Integer status;

    private String remark;

    private LocalDateTime createTime;

    /** 拥有的角色 id 列表（编辑用户时回填下拉框） */
    private List<Long> roleIds;

    /** 拥有的角色名称列表（列表页显示用） */
    private List<String> roleNames;
}
