package com.zimeiti.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import com.fasterxml.jackson.annotation.JsonIgnore;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 用户实体，对应 sys_user 表。
 * <p>三种角色（超级管理员 / 审核员 / 创作者）共用这一张表，具体身份由「用户-角色」关联决定。
 */
@Data
@TableName("sys_user")
public class SysUser {

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 登录账号 */
    private String username;

    /**
     * 密码（BCrypt 哈希）。
     * <p>@JsonIgnore 确保这个字段永远不会出现在返回给前端的 JSON 里 —— 即使某天有人不小心
     * 把整个 SysUser 对象返回出去，密码也不会泄漏。
     */
    @JsonIgnore
    private String password;

    /** 昵称（界面上显示的名字） */
    private String nickname;

    private String avatar;

    private String email;

    private String phone;

    /** 状态：1 启用，0 禁用 */
    private Integer status;

    private String remark;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;

    /** 逻辑删除标记：@TableLogic 让 MyBatis-Plus 在查询时自动追加 deleted = 0 条件 */
    @TableLogic
    private Integer deleted;
}
