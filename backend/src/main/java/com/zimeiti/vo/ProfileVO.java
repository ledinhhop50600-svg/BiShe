package com.zimeiti.vo;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 个人中心展示信息（只含当前用户自己的数据）。
 */
@Data
public class ProfileVO {

    private Long id;

    /** 账号名，注册后不可修改 */
    private String username;

    private String nickname;

    private String email;

    private String phone;

    private String avatar;

    private List<String> roles;

    private LocalDateTime createTime;
}
