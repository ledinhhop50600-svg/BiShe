package com.zimeiti.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 角色实体，对应 sys_role 表。
 * <p>本项目有三种角色：超级管理员（admin）、审核员（reviewer）、创作者（creator）。
 * <p>roleKey 是程序里判断身份用的标识（纯英文，不会因为改名而失效）；
 * roleName 是界面上显示的中文名称。
 */
@Data
@TableName("sys_role")
public class SysRole {

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 角色名称，如"审核员" */
    private String roleName;

    /** 角色标识，如 reviewer */
    private String roleKey;

    private String description;

    private Integer sort;

    /** 状态：1 启用，0 禁用 */
    private Integer status;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;
}
