package com.zimeiti.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import com.zimeiti.common.Result;
import com.zimeiti.entity.AuditPlatform;
import com.zimeiti.service.PlatformService;
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
 * 目标平台接口。
 * <p>读取对登录用户开放（阶段 6 的适配页要用平台清单）；修改需要 platform:manage。
 */
@RestController
@RequestMapping("/api/platform")
@RequiredArgsConstructor
public class PlatformController {

    private final PlatformService platformService;

    @GetMapping("/list")
    public Result<List<AuditPlatform>> list() {
        return Result.ok(platformService.list());
    }

    @PostMapping
    @SaCheckPermission("platform:manage")
    public Result<Void> save(@Valid @RequestBody AuditPlatform platform) {
        platformService.save(platform);
        return Result.ok();
    }

    @PutMapping
    @SaCheckPermission("platform:manage")
    public Result<Void> update(@Valid @RequestBody AuditPlatform platform) {
        platformService.update(platform);
        return Result.ok();
    }

    @DeleteMapping("/{id}")
    @SaCheckPermission("platform:manage")
    public Result<Void> delete(@PathVariable Long id) {
        platformService.delete(id);
        return Result.ok();
    }
}
