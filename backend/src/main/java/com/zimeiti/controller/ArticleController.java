package com.zimeiti.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import cn.dev33.satoken.annotation.SaMode;
import com.zimeiti.common.PageResult;
import com.zimeiti.common.Result;
import com.zimeiti.dto.ArticleReviewDTO;
import com.zimeiti.dto.ArticleSaveDTO;
import com.zimeiti.service.ArticleService;
import com.zimeiti.vo.ArticleVO;
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
 * 稿件接口。
 * <p>状态流转全部通过"动作接口"完成（submit / withdraw / review / offline），
 * 前端没有任何接口可以直接设置稿件状态 —— 这是状态机的基本约束。
 */
@RestController
@RequestMapping("/api/article")
@RequiredArgsConstructor
public class ArticleController {

    private final ArticleService articleService;

    /**
     * 后台稿件列表。
     * <p>注意这里用的是 OR 权限：这个接口被两个页面复用 ——
     * 「稿件管理」（管理员，article:list）与「审核工作台」（审核员，audit:workbench）。
     * 早前只写了 article:list，导致审核员打开工作台时被 403 拦下（待审队列永远是空的）。
     * 凡是共用接口，权限要覆盖**所有调用方**，不能只按其中一个页面来设计。
     */
    @GetMapping("/page")
    @SaCheckPermission(value = {"article:list", "audit:workbench"}, mode = SaMode.OR)
    public Result<PageResult<ArticleVO>> page(@RequestParam(defaultValue = "1") long pageNum,
                                              @RequestParam(defaultValue = "10") long pageSize,
                                              @RequestParam(required = false) String title,
                                              @RequestParam(required = false) Integer status,
                                              @RequestParam(required = false) Long categoryId) {
        return Result.ok(articleService.page(pageNum, pageSize, title, status, categoryId));
    }

    /** 我的稿件（创作者） */
    @GetMapping("/my")
    @SaCheckPermission("creator:article")
    public Result<PageResult<ArticleVO>> my(@RequestParam(defaultValue = "1") long pageNum,
                                            @RequestParam(defaultValue = "10") long pageSize,
                                            @RequestParam(required = false) Integer status) {
        return Result.ok(articleService.myPage(pageNum, pageSize, status));
    }

    /** 内容广场：浏览平台已发布的稿件（含自己的），支持标题 / 分类 / 标签筛选 */
    @GetMapping("/plaza")
    @SaCheckPermission("creator:plaza")
    public Result<PageResult<ArticleVO>> plaza(@RequestParam(defaultValue = "1") long pageNum,
                                               @RequestParam(defaultValue = "10") long pageSize,
                                               @RequestParam(required = false) String title,
                                               @RequestParam(required = false) Long categoryId,
                                               @RequestParam(required = false) Long tagId) {
        return Result.ok(articleService.plaza(pageNum, pageSize, title, categoryId, tagId));
    }

    /** 稿件详情：三类角色都可能看，服务层再判断创作者只能看自己的 */
    @GetMapping("/{id}")
    @SaCheckPermission(value = {"article:list", "audit:workbench", "creator:article"}, mode = SaMode.OR)
    public Result<ArticleVO> detail(@PathVariable Long id) {
        return Result.ok(articleService.detail(id));
    }

    /** 新建稿件（保存为草稿） */
    @PostMapping
    @SaCheckPermission(value = {"creator:submit", "article:list"}, mode = SaMode.OR)
    public Result<Long> save(@Valid @RequestBody ArticleSaveDTO dto) {
        return Result.ok(articleService.save(dto));
    }

    /** 修改稿件（仅自己的草稿或已驳回稿件） */
    @PutMapping
    @SaCheckPermission(value = {"creator:submit", "article:list"}, mode = SaMode.OR)
    public Result<Void> update(@Valid @RequestBody ArticleSaveDTO dto) {
        articleService.update(dto);
        return Result.ok();
    }

    /** 删除稿件 */
    @DeleteMapping("/{id}")
    @SaCheckPermission(value = {"creator:submit", "article:delete"}, mode = SaMode.OR)
    public Result<Void> delete(@PathVariable Long id) {
        articleService.delete(id);
        return Result.ok();
    }

    /** 提交发布申请：草稿/已驳回 -> 待审核 */
    @PostMapping("/{id}/submit")
    @SaCheckPermission("creator:submit")
    public Result<Void> submit(@PathVariable Long id) {
        articleService.submit(id);
        return Result.ok();
    }

    /** 撤回申请：待审核 -> 草稿 */
    @PostMapping("/{id}/withdraw")
    @SaCheckPermission("creator:submit")
    public Result<Void> withdraw(@PathVariable Long id) {
        articleService.withdraw(id);
        return Result.ok();
    }

    /** 审核（通过 / 驳回 / 阻断） */
    @PutMapping("/{id}/review")
    @SaCheckPermission("audit:workbench")
    public Result<Void> review(@PathVariable Long id, @Valid @RequestBody ArticleReviewDTO dto) {
        articleService.review(id, dto);
        return Result.ok();
    }

    /** 下架已发布稿件 */
    @PutMapping("/{id}/offline")
    @SaCheckPermission("article:edit")
    public Result<Void> offline(@PathVariable Long id) {
        articleService.offline(id);
        return Result.ok();
    }
}
