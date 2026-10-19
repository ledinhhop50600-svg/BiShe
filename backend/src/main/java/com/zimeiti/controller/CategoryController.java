package com.zimeiti.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import com.zimeiti.common.Result;
import com.zimeiti.entity.BizCategory;
import com.zimeiti.service.CategoryService;
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
 * 稿件分类接口。
 * <p>读取对登录用户开放（投稿时要选分类，所以创作者也需要读）；修改需要 category:manage。
 */
@RestController
@RequestMapping("/api/category")
@RequiredArgsConstructor
public class CategoryController {

    private final CategoryService categoryService;

    @GetMapping("/list")
    public Result<List<BizCategory>> list() {
        return Result.ok(categoryService.listCategories());
    }

    @PostMapping
    @SaCheckPermission("category:manage")
    public Result<Void> save(@Valid @RequestBody BizCategory category) {
        categoryService.saveCategory(category);
        return Result.ok();
    }

    @PutMapping
    @SaCheckPermission("category:manage")
    public Result<Void> update(@Valid @RequestBody BizCategory category) {
        categoryService.updateCategory(category);
        return Result.ok();
    }

    @DeleteMapping("/{id}")
    @SaCheckPermission("category:manage")
    public Result<Void> delete(@PathVariable Long id) {
        categoryService.deleteCategory(id);
        return Result.ok();
    }
}
