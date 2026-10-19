package com.zimeiti.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import cn.dev33.satoken.annotation.SaMode;
import com.zimeiti.common.Result;
import com.zimeiti.dto.AdaptRequestDTO;
import com.zimeiti.service.AdaptService;
import com.zimeiti.vo.AdaptationVO;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

/**
 * 跨平台适配接口（阶段 6）。
 * <p>权限：创作者用自己的 creator:adapt；管理员靠 article:list（管理员拥有全部菜单）。
 * 数据权限在服务层判断 —— 创作者只能适配自己的稿件。
 */
@RestController
@RequestMapping("/api/article")
@RequiredArgsConstructor
public class AdaptController {

    private final AdaptService adaptService;

    /** 生成适配版本（一次可多个平台），结果同时落库 */
    @PostMapping("/{id}/adapt")
    @SaCheckPermission(value = {"creator:adapt", "article:list"}, mode = SaMode.OR)
    public Result<Map<String, Object>> adapt(@PathVariable Long id,
                                             @Valid @RequestBody AdaptRequestDTO dto) {
        return Result.ok(adaptService.adapt(id, dto.getPlatformKeys()));
    }

    /** 某篇稿件的适配历史（按时间倒序） */
    @GetMapping("/{id}/adaptations")
    @SaCheckPermission(value = {"creator:adapt", "article:list"}, mode = SaMode.OR)
    public Result<List<AdaptationVO>> adaptations(@PathVariable Long id) {
        return Result.ok(adaptService.listByArticle(id));
    }
}
