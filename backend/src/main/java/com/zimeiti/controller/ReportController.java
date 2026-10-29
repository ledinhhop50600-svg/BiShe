package com.zimeiti.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import com.zimeiti.common.PageResult;
import com.zimeiti.common.Result;
import com.zimeiti.dto.ReportHandleDTO;
import com.zimeiti.service.ReportService;
import com.zimeiti.vo.ReportVO;

import java.util.Map;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 举报接口。
 * <p>创作者可举报他人已发布的稿件；审核员处理举报，成立则稿件自动下架。
 */
@RestController
@RequestMapping("/api/report")
@RequiredArgsConstructor
public class ReportController {

    private final ReportService reportService;

    @GetMapping("/page")
    @SaCheckPermission("report:handle")
    public Result<PageResult<ReportVO>> page(@RequestParam(defaultValue = "1") long pageNum,
                                             @RequestParam(defaultValue = "10") long pageSize,
                                             @RequestParam(required = false) Integer status) {
        return Result.ok(reportService.page(pageNum, pageSize, status));
    }

    @PostMapping
    @SaCheckPermission("creator:article")
    public Result<Void> create(@RequestParam Long articleId, @RequestParam String reason) {
        reportService.create(articleId, reason);
        return Result.ok();
    }

    @PutMapping("/{id}/handle")
    @SaCheckPermission("report:handle")
    public Result<Void> handle(@PathVariable Long id, @Valid @RequestBody ReportHandleDTO dto) {
        reportService.handle(id, dto);
        return Result.ok();
    }

    /** 举报复审：调用智能体并落 audit_record，供审核员参考；不自动改稿件状态 */
    @PostMapping("/{id}/agent-review")
    @SaCheckPermission("report:handle")
    public Result<Map<String, Object>> agentReview(@PathVariable Long id) {
        return Result.ok(reportService.agentReview(id));
    }
}
