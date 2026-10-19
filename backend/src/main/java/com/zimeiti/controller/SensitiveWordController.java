package com.zimeiti.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import com.zimeiti.common.PageResult;
import com.zimeiti.common.Result;
import com.zimeiti.entity.AuditSensitiveWord;
import com.zimeiti.service.SensitiveWordService;
import com.zimeiti.vo.SensitiveCheckVO;
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

import java.util.Map;

/**
 * 敏感词接口。
 * <p>{@code POST /api/sensitive/check} 对所有登录用户开放：投稿页和审核页都会用它做一次初筛。
 * 其余管理接口需要 audit:sensitive 权限。
 */
@RestController
@RequestMapping("/api/sensitive")
@RequiredArgsConstructor
public class SensitiveWordController {

    private final SensitiveWordService wordService;

    @GetMapping("/page")
    @SaCheckPermission("audit:sensitive")
    public Result<PageResult<AuditSensitiveWord>> page(@RequestParam(defaultValue = "1") long pageNum,
                                                       @RequestParam(defaultValue = "10") long pageSize,
                                                       @RequestParam(required = false) String word,
                                                       @RequestParam(required = false) String category) {
        return Result.ok(wordService.page(pageNum, pageSize, word, category));
    }

    @PostMapping
    @SaCheckPermission("audit:sensitive")
    public Result<Void> save(@Valid @RequestBody AuditSensitiveWord word) {
        wordService.save(word);
        return Result.ok();
    }

    @PutMapping
    @SaCheckPermission("audit:sensitive")
    public Result<Void> update(@Valid @RequestBody AuditSensitiveWord word) {
        wordService.update(word);
        return Result.ok();
    }

    @DeleteMapping("/{id}")
    @SaCheckPermission("audit:sensitive")
    public Result<Void> delete(@PathVariable Long id) {
        wordService.delete(id);
        return Result.ok();
    }

    /** 文本检测：请求体为 {"text": "待检测内容"} */
    @PostMapping("/check")
    public Result<SensitiveCheckVO> check(@RequestBody Map<String, String> body) {
        return Result.ok(wordService.check(body.get("text")));
    }
}
