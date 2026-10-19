package com.zimeiti.controller;

import com.zimeiti.common.Result;
import com.zimeiti.dto.PasswordChangeDTO;
import com.zimeiti.dto.ProfileUpdateDTO;
import com.zimeiti.service.ProfileService;
import com.zimeiti.vo.ProfileVO;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 个人中心接口。
 * <p>只操作"当前登录用户自己的数据"，因此不需要功能权限注解 ——
 * 登录拦截器已经保证只有登录用户能访问，userId 从令牌里取，不接受前端传入。
 */
@RestController
@RequestMapping("/api/profile")
@RequiredArgsConstructor
public class ProfileController {

    private final ProfileService profileService;

    @GetMapping
    public Result<ProfileVO> get() {
        return Result.ok(profileService.get());
    }

    @PutMapping
    public Result<Void> update(@Valid @RequestBody ProfileUpdateDTO dto) {
        profileService.update(dto);
        return Result.ok();
    }

    @PutMapping("/password")
    public Result<Void> changePassword(@Valid @RequestBody PasswordChangeDTO dto) {
        profileService.changePassword(dto);
        return Result.ok();
    }
}
