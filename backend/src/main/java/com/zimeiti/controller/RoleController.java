package com.zimeiti.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import cn.dev33.satoken.annotation.SaMode;
import com.zimeiti.common.PageResult;
import com.zimeiti.common.Result;
import com.zimeiti.dto.RoleSaveDTO;
import com.zimeiti.entity.SysRole;
import com.zimeiti.service.RoleService;
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

import java.util.List;

/**
 * 角色管理接口。
 * <p>注意 {@code /api/role/list} 上的注解用了 OR 模式：它同时被"用户管理"用来填角色下拉框，
 * 因此拥有 system:role 或 system:user 任一权限即可访问，不必为了复用而重复写接口。
 */
@RestController
@RequestMapping("/api/role")
@RequiredArgsConstructor
public class RoleController {

    private final RoleService roleService;

    @GetMapping("/page")
    @SaCheckPermission("system:role")
    public Result<PageResult<SysRole>> page(@RequestParam(defaultValue = "1") long pageNum,
                                            @RequestParam(defaultValue = "10") long pageSize,
                                            @RequestParam(required = false) String roleName) {
        return Result.ok(roleService.page(pageNum, pageSize, roleName));
    }

    @GetMapping("/list")
    @SaCheckPermission(value = {"system:role", "system:user"}, mode = SaMode.OR)
    public Result<List<SysRole>> list() {
        return Result.ok(roleService.listAll());
    }

    @GetMapping("/{id}/menuIds")
    @SaCheckPermission("system:role")
    public Result<List<Long>> menuIds(@PathVariable Long id) {
        return Result.ok(roleService.menuIds(id));
    }

    @PostMapping
    @SaCheckPermission("system:role")
    public Result<Void> save(@Valid @RequestBody RoleSaveDTO dto) {
        roleService.save(dto);
        return Result.ok();
    }

    @PutMapping
    @SaCheckPermission("system:role")
    public Result<Void> update(@Valid @RequestBody RoleSaveDTO dto) {
        roleService.update(dto);
        return Result.ok();
    }

    @DeleteMapping("/{id}")
    @SaCheckPermission("system:role")
    public Result<Void> delete(@PathVariable Long id) {
        roleService.delete(id);
        return Result.ok();
    }
}
