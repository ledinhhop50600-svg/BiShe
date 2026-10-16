package com.zimeiti.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import com.zimeiti.common.PageResult;
import com.zimeiti.common.Result;
import com.zimeiti.dto.UserSaveDTO;
import com.zimeiti.service.UserService;
import com.zimeiti.vo.UserVO;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 用户管理接口。
 * <p>每个接口都用 {@code @SaCheckPermission("system:user")} 声明所需权限：
 * 只有拥有该权限标识的角色才能调用 —— 这是"后端鉴权"，与前端隐藏按钮是两道独立的防线，
 * 即使有人绕过前端直接调接口，也会被这里拦下（返回 403）。
 */
@RestController
@RequestMapping("/api/user")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    @GetMapping("/page")
    @SaCheckPermission("system:user")
    public Result<PageResult<UserVO>> page(@RequestParam(defaultValue = "1") long pageNum,
                                           @RequestParam(defaultValue = "10") long pageSize,
                                           @RequestParam(required = false) String username,
                                           @RequestParam(required = false) Integer status) {
        return Result.ok(userService.page(pageNum, pageSize, username, status));
    }

    @GetMapping("/{id}")
    @SaCheckPermission("system:user")
    public Result<UserVO> detail(@PathVariable Long id) {
        return Result.ok(userService.detail(id));
    }

    @PostMapping
    @SaCheckPermission("system:user")
    public Result<Void> save(@Valid @RequestBody UserSaveDTO dto) {
        userService.save(dto);
        return Result.ok();
    }

    @PutMapping
    @SaCheckPermission("system:user")
    public Result<Void> update(@Valid @RequestBody UserSaveDTO dto) {
        userService.update(dto);
        return Result.ok();
    }

    @PutMapping("/{id}/status")
    @SaCheckPermission("system:user")
    public Result<Void> updateStatus(@PathVariable Long id, @RequestParam Integer status) {
        userService.updateStatus(id, status);
        return Result.ok();
    }

    @PutMapping("/{id}/password")
    @SaCheckPermission("system:user")
    public Result<Void> resetPassword(@PathVariable Long id, @RequestParam String password) {
        userService.resetPassword(id, password);
        return Result.ok();
    }

    @DeleteMapping("/{id}")
    @SaCheckPermission("system:user")
    public Result<Void> delete(@PathVariable Long id) {
        userService.delete(id);
        return Result.ok();
    }
}
