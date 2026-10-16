package com.zimeiti.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import cn.dev33.satoken.annotation.SaMode;
import com.zimeiti.common.Result;
import com.zimeiti.dto.MenuSaveDTO;
import com.zimeiti.entity.SysMenu;
import com.zimeiti.service.MenuService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 菜单管理接口。
 * <p>{@code /api/menu/tree} 供两个地方使用：菜单管理页面（展示整棵树），
 * 以及角色管理的"分配权限"弹窗（勾选树）。所以它允许 system:menu 或 system:role 任一权限访问。
 */
@RestController
@RequestMapping("/api/menu")
@RequiredArgsConstructor
public class MenuController {

    private final MenuService menuService;

    @GetMapping("/tree")
    @SaCheckPermission(value = {"system:menu", "system:role"}, mode = SaMode.OR)
    public Result<List<SysMenu>> tree() {
        return Result.ok(menuService.treeAll());
    }

    @PostMapping
    @SaCheckPermission("system:menu")
    public Result<Void> save(@Valid @RequestBody MenuSaveDTO dto) {
        menuService.save(dto);
        return Result.ok();
    }

    @PutMapping
    @SaCheckPermission("system:menu")
    public Result<Void> update(@Valid @RequestBody MenuSaveDTO dto) {
        menuService.update(dto);
        return Result.ok();
    }

    @DeleteMapping("/{id}")
    @SaCheckPermission("system:menu")
    public Result<Void> delete(@PathVariable Long id) {
        menuService.delete(id);
        return Result.ok();
    }
}
