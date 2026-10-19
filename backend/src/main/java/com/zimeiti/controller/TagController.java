package com.zimeiti.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import com.zimeiti.common.Result;
import com.zimeiti.entity.BizTag;
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
 * 稿件标签接口（与分类同属内容分类体系，共用 CategoryService）。
 */
@RestController
@RequestMapping("/api/tag")
@RequiredArgsConstructor
public class TagController {

    private final CategoryService categoryService;

    @GetMapping("/list")
    public Result<List<BizTag>> list() {
        return Result.ok(categoryService.listTags());
    }

    @PostMapping
    @SaCheckPermission("category:manage")
    public Result<Void> save(@Valid @RequestBody BizTag tag) {
        categoryService.saveTag(tag);
        return Result.ok();
    }

    @PutMapping
    @SaCheckPermission("category:manage")
    public Result<Void> update(@Valid @RequestBody BizTag tag) {
        categoryService.updateTag(tag);
        return Result.ok();
    }

    @DeleteMapping("/{id}")
    @SaCheckPermission("category:manage")
    public Result<Void> delete(@PathVariable Long id) {
        categoryService.deleteTag(id);
        return Result.ok();
    }
}
