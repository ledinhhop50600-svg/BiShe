package com.zimeiti.service;

import com.zimeiti.dto.PasswordChangeDTO;
import com.zimeiti.dto.ProfileUpdateDTO;
import com.zimeiti.vo.ProfileVO;

/**
 * 个人中心：查看/修改自己的资料、修改密码。
 */
public interface ProfileService {

    ProfileVO get();

    void update(ProfileUpdateDTO dto);

    /** 修改密码：验证原密码，成功后注销当前会话，要求重新登录 */
    void changePassword(PasswordChangeDTO dto);
}
