package com.zimeiti.controller;

import com.zimeiti.common.Result;
import com.zimeiti.dto.LoginDTO;
import com.zimeiti.service.AuthService;
import com.zimeiti.vo.LoginVO;
import com.zimeiti.vo.UserInfoVO;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 认证接口。
 * <p>接口一览：
 * POST /api/auth/login   登录（白名单，未登录可访问）
 * POST /api/auth/logout  登出
 * GET  /api/auth/me      获取当前登录用户信息
 */
@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @PostMapping("/login")
    public Result<LoginVO> login(@Valid @RequestBody LoginDTO dto) {
        return Result.ok(authService.login(dto));
    }

    @PostMapping("/logout")
    public Result<Void> logout() {
        authService.logout();
        return Result.ok();
    }

    @GetMapping("/me")
    public Result<UserInfoVO> me() {
        return Result.ok(authService.currentUser());
    }
}
